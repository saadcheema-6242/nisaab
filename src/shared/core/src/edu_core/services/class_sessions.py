"""Weekly class sessions: scheduling them, and showing them to the right people.

The rules about links, join windows and who a subject is for live in
edu_core.weekly_session, where they can be checked without a database. This
file is the part that needs one: reading the timetable, and deciding which
of the three views a caller gets.

The link is the thing to be careful with. A student is given it only while
the session is open; a teacher always, because they have to start the class;
an administrator always, because they have to check it is right. That is
enforced here rather than in the page, because a page is a suggestion and a
service is not.
"""

import logging
from contextlib import contextmanager
from datetime import datetime, timezone

from edu_db.models import ClassSession, StudentProfile, Subject, User
from edu_db.session import get_session_factory
from sqlalchemy.orm import joinedload

from edu_core.exceptions import NotFoundError
from edu_core.group_change import GROUP_SUBJECTS
from edu_core.roles import is_approved_teacher
from edu_core.schemas.sessions import (
    AdminSessionDto,
    AdminSessionListDto,
    SessionListDto,
    StudentSessionDto,
    TeacherDashboardDto,
    TeacherDto,
    TeacherOptionDto,
    TeacherSessionDto,
)
from edu_core.weekly_session import (
    SessionError,
    check_duration,
    check_link,
    check_title,
    groups_for,
    is_joinable,
    state,
    upcoming,
    when_in_words,
)

logger = logging.getLogger(__name__)

# How far back a finished session stays visible to an administrator. Students
# and teachers only ever see what has not ended.
HISTORY_LIMIT = 50


class ClassSessionService:
    @contextmanager
    def _session(self):
        factory = get_session_factory()
        db = factory()
        try:
            yield db
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    # ---- shared -----------------------------------------------------------

    @staticmethod
    def _subject_names(db) -> dict[str, str]:
        return {s.code: s.name for s in db.query(Subject).all()}

    @staticmethod
    def _teacher_of(row: ClassSession) -> TeacherDto | None:
        """The teacher as shown on a card.

        Falls back to the name stored on the session, so a class scheduled
        before the teacher signed up still says who is taking it, and a class
        whose teacher's account was deleted does not turn anonymous.
        """
        if row.teacher is not None:
            return TeacherDto(
                id=row.teacher.id,
                name=row.teacher.name or row.teacher_name or "A teacher",
                headline=row.teacher.headline,
            )
        if row.teacher_name:
            return TeacherDto(id=None, name=row.teacher_name, headline=None)
        return None

    def _common(self, row: ClassSession, names: dict, now: datetime) -> dict:
        return {
            "id": row.id,
            "title": row.title,
            "description": row.description,
            "subject_code": row.subject_code,
            "subject_name": names.get(row.subject_code, row.subject_code),
            "grade": row.grade,
            "starts_at": row.starts_at,
            "duration_minutes": row.duration_minutes,
            "when": when_in_words(row.starts_at, now),
            "state": state(row.starts_at, row.duration_minutes, now),
        }

    @staticmethod
    def _rows(db):
        return db.query(ClassSession).options(joinedload(ClassSession.teacher))

    # ---- the student's timetable -----------------------------------------

    def for_student(
        self, user_id: str, limit: int = 20, is_admin: bool = False
    ) -> SessionListDto:
        """Sessions this student may attend, soonest first.

        Filtered by grade and by whether their group studies the subject, so
        an ICS student is shown Physics and Maths and never Biology. A
        student with no profile yet has no timetable rather than everyone's.

        An administrator is not a member of a cohort, so filtering them into
        one would be answering a question nobody asked: they see every class
        in the school. The join window still applies to them, because the
        link opening early is about the link, not about who is reading it.
        """
        now = datetime.now(timezone.utc)
        with self._session() as db:
            query = self._rows(db).filter(ClassSession.cancelled_at.is_(None))

            if not is_admin:
                profile = (
                    db.query(StudentProfile)
                    .filter(StudentProfile.user_id == user_id)
                    .one_or_none()
                )
                if profile is None:
                    return SessionListDto(sessions=[])

                studies = GROUP_SUBJECTS.get((profile.group_code or "").upper(), [])
                if not studies:
                    return SessionListDto(sessions=[])

                query = query.filter(
                    ClassSession.grade == profile.grade,
                    ClassSession.subject_code.in_(studies),
                )

            rows = query.order_by(ClassSession.starts_at).all()
            names = self._subject_names(db)

            out = []
            for row in self._still_running(rows, now, limit):
                body = self._common(row, names, now)
                # The whole point of the window: the link exists on the row
                # the entire time and is handed over only while the class is
                # open. Sending it earlier and hiding it in the page would
                # put it in the network tab for anyone who looked.
                body["join_url"] = (
                    row.join_url
                    if is_joinable(row.starts_at, row.duration_minutes, now)
                    else None
                )
                out.append(
                    StudentSessionDto(**body, teacher=self._teacher_of(row))
                )
            return SessionListDto(sessions=out)

    @staticmethod
    def _still_running(rows, now, limit):
        as_dicts = [
            {
                "row": r,
                "starts_at": r.starts_at,
                "duration_minutes": r.duration_minutes,
            }
            for r in rows
        ]
        return [item["row"] for item in upcoming(as_dicts, now, limit)]

    # ---- the teacher's dashboard -----------------------------------------

    def for_teacher(self, user_id: str) -> TeacherDashboardDto:
        now = datetime.now(timezone.utc)
        with self._session() as db:
            teacher = db.query(User).filter(User.id == user_id).one_or_none()
            if teacher is None:
                raise NotFoundError("No such account")

            rows = (
                self._rows(db)
                .filter(
                    ClassSession.teacher_id == user_id,
                    ClassSession.cancelled_at.is_(None),
                )
                .order_by(ClassSession.starts_at)
                .all()
            )
            names = self._subject_names(db)
            mine = [
                TeacherSessionDto(
                    **self._common(row, names, now),
                    join_url=row.join_url,
                    groups=groups_for(row.subject_code),
                )
                for row in self._still_running(rows, now, HISTORY_LIMIT)
            ]
            return TeacherDashboardDto(
                teacher=TeacherDto(
                    id=teacher.id,
                    name=teacher.name or "Teacher",
                    headline=teacher.headline,
                ),
                # A class already running is still the next one: a teacher
                # opening this mid-lesson wants the lesson they are in.
                next_session=mine[0] if mine else None,
                sessions=mine,
            )

    # ---- the administrator's view ----------------------------------------

    def for_admin(self) -> AdminSessionListDto:
        now = datetime.now(timezone.utc)
        with self._session() as db:
            rows = (
                self._rows(db)
                .order_by(ClassSession.starts_at.desc())
                .limit(HISTORY_LIMIT)
                .all()
            )
            names = self._subject_names(db)
            sessions = [
                AdminSessionDto(
                    **self._common(row, names, now),
                    teacher=self._teacher_of(row),
                    join_url=row.join_url,
                    meeting_source=row.meeting_source,
                    groups=groups_for(row.subject_code),
                    cancelled_at=row.cancelled_at,
                )
                for row in rows
            ]
            sessions.sort(key=lambda s: s.starts_at)
            return AdminSessionListDto(
                sessions=sessions, teachers=self._teachers(db)
            )

    @staticmethod
    def _teachers(db) -> list[TeacherOptionDto]:
        """Who may actually be put in front of a class.

        Approved teachers only. Filtering on the role alone would list every
        account that ticked "teacher" at signup, unreviewed, as assignable to
        real students - which is the whole reason approval exists.
        """
        rows = (
            db.query(User)
            .filter(User.role == "teacher", User.teacher_approved_at.isnot(None))
            .order_by(User.name)
            .all()
        )
        return [
            TeacherOptionDto(
                id=u.id, name=u.name or u.email or "Teacher",
                email=u.email, headline=u.headline,
            )
            for u in rows
        ]

    # ---- scheduling -------------------------------------------------------

    def create(
        self,
        *,
        created_by: str,
        title: str,
        subject_code: str,
        grade: int,
        starts_at: datetime,
        duration_minutes: int,
        join_url: str,
        teacher_id: str | None = None,
        teacher_name: str | None = None,
        description: str | None = None,
    ) -> AdminSessionDto:
        """Schedule a class. Everything is validated before anything is stored."""
        title = check_title(title)
        duration_minutes = check_duration(duration_minutes)
        join_url = check_link(join_url)

        subject_code = (subject_code or "").upper()
        if not groups_for(subject_code):
            raise SessionError(
                f"No group studies {subject_code}, so nobody could attend."
            )
        if grade not in (11, 12):
            raise SessionError("A class is for grade 11 or 12.")
        if starts_at.tzinfo is None:
            starts_at = starts_at.replace(tzinfo=timezone.utc)

        with self._session() as db:
            name = (teacher_name or "").strip() or None
            if teacher_id:
                teacher = db.query(User).filter(User.id == teacher_id).one_or_none()
                if teacher is None:
                    raise NotFoundError("No such teacher")
                if not is_approved_teacher(teacher.role, teacher.teacher_approved_at):
                    raise SessionError(
                        "That account is not an approved teacher. Approve it "
                        "from the Teachers tab first."
                    )
                name = name or teacher.name
            if not teacher_id and not name:
                raise SessionError("Say who is taking the class.")

            row = ClassSession(
                title=title,
                description=(description or "").strip() or None,
                subject_code=subject_code,
                grade=grade,
                teacher_id=teacher_id,
                teacher_name=name,
                starts_at=starts_at,
                duration_minutes=duration_minutes,
                join_url=join_url,
                meeting_source="manual",
                created_by=created_by,
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            logger.info("Scheduled %s for %s XI/%s", row.title, subject_code, grade)
            names = self._subject_names(db)
            now = datetime.now(timezone.utc)
            return AdminSessionDto(
                **self._common(row, names, now),
                teacher=self._teacher_of(row),
                join_url=row.join_url,
                meeting_source=row.meeting_source,
                groups=groups_for(row.subject_code),
                cancelled_at=None,
            )

    def cancel(self, session_id: str) -> None:
        """Take a class off the timetable without losing the record of it.

        Marked rather than deleted: a class that was scheduled and called off
        is a thing that happened, and an administrator looking at a gap in
        next week wants to know whether it was cancelled or never set.
        """
        with self._session() as db:
            row = (
                db.query(ClassSession)
                .filter(ClassSession.id == session_id)
                .one_or_none()
            )
            if row is None:
                raise NotFoundError("No such session")
            row.cancelled_at = datetime.now(timezone.utc)
            db.commit()

    def set_role(self, user_id: str, role: str, headline: str | None = None) -> None:
        """Make an account a teacher, or put it back to being a student."""
        if role not in ("student", "teacher"):
            raise SessionError("A role is either student or teacher.")
        with self._session() as db:
            user = db.query(User).filter(User.id == user_id).one_or_none()
            if user is None:
                raise NotFoundError("No such account")
            user.role = role
            if headline is not None:
                user.headline = headline.strip() or None
            if role == "teacher":
                # An administrator naming someone a teacher is the approval.
                # Leaving the date unset here would mark them a teacher who
                # can never be scheduled, which reads as a bug rather than a
                # decision. An existing approval is left as it was.
                if user.teacher_approved_at is None:
                    user.teacher_approved_at = datetime.now(timezone.utc)
            else:
                # A former teacher keeps their classes in the record, but
                # stops being offered for new ones.
                user.headline = None
                user.teacher_approved_at = None
                user.teacher_approved_by = None
            db.commit()
