"""Teacher accounts: applying to be one, and being approved.

Separate from ProfileService, which is about students and their subject
workspaces. A teacher has no year, no group and no workspaces; sharing a
service would mean every method asking which kind of account it was dealing
with before it could do anything.

The rules about what an unapproved teacher may do live in edu_core.roles and
are checked there. This is the part that needs a database.
"""

import logging
from contextlib import contextmanager
from datetime import datetime, timezone

from edu_db.models import Subject, TeacherProfile, User
from edu_db.session import get_session_factory

from edu_core.exceptions import NotFoundError
from edu_core.roles import (
    MAX_HEADLINE,
    MAX_SCHOOL,
    STUDENT,
    TEACHER,
    RoleError,
    check_grades,
    check_subjects,
    check_text,
    is_approved_teacher,
)
from edu_core.schemas.teachers import (
    TeacherAccountDto,
    TeacherProfileDto,
    TeacherQueueDto,
)

logger = logging.getLogger(__name__)


class TeacherService:
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

    @staticmethod
    def _known_subjects(db) -> list[str]:
        return [code for (code,) in db.query(Subject.code).all()]

    @staticmethod
    def _as_dto(user: User, profile: TeacherProfile | None) -> TeacherAccountDto:
        return TeacherAccountDto(
            id=user.id,
            name=user.name or user.email or "Teacher",
            email=user.email,
            headline=user.headline,
            approved=is_approved_teacher(user.role, user.teacher_approved_at),
            approved_at=user.teacher_approved_at,
            profile=(
                TeacherProfileDto(
                    subjects=list(profile.subjects or []),
                    grades=list(profile.grades or []),
                    school=profile.school,
                    about=profile.about,
                    applied_at=profile.applied_at,
                )
                if profile
                else None
            ),
        )

    # ---- applying ---------------------------------------------------------

    def apply(
        self,
        *,
        user_id: str,
        subjects: list[str],
        grades: list[int],
        school: str | None = None,
        headline: str | None = None,
        about: str | None = None,
    ) -> TeacherAccountDto:
        """Finish signing up as a teacher. Grants nothing until approved.

        Re-applying updates the application rather than creating a second
        one, so somebody who chose the wrong subject can fix it while they
        wait instead of being stuck with it.
        """
        with self._session() as db:
            user = db.get(User, user_id)
            if user is None:
                raise NotFoundError("No such account")

            chosen = check_subjects(subjects, self._known_subjects(db))
            years = check_grades(grades)
            school = check_text(school, MAX_SCHOOL, "the school name")
            headline = check_text(headline, MAX_HEADLINE, "your title")
            about = check_text(about, 600, "what you teach")

            profile = db.get(TeacherProfile, user_id)
            if profile is None:
                profile = TeacherProfile(user_id=user_id)
                db.add(profile)
            profile.subjects = chosen
            profile.grades = years
            profile.school = school
            profile.about = about

            user.role = TEACHER
            user.headline = headline
            # Re-applying never clears an approval that was already given.
            db.commit()
            db.refresh(user)
            db.refresh(profile)
            logger.info("Teacher application from %s for %s", user_id, chosen)
            return self._as_dto(user, profile)

    def get_account(self, user_id: str) -> TeacherAccountDto:
        with self._session() as db:
            user = db.get(User, user_id)
            if user is None:
                raise NotFoundError("No such account")
            return self._as_dto(user, db.get(TeacherProfile, user_id))

    def withdraw(self, user_id: str) -> None:
        """Go back to being a student.

        The way out of the waiting page. Somebody will tap "Teacher" by
        mistake, and without this their account is stranded: not approved,
        so not a teacher, and not a student either, with nothing to do but
        wait for an administrator who has no idea they are waiting.

        The application is deleted rather than kept, because a withdrawn one
        sitting in the queue is a question nobody can answer.
        """
        with self._session() as db:
            user = db.get(User, user_id)
            if user is None:
                raise NotFoundError("No such account")
            profile = db.get(TeacherProfile, user_id)
            if profile is not None:
                db.delete(profile)
            user.role = STUDENT
            user.headline = None
            user.teacher_approved_at = None
            user.teacher_approved_by = None
            db.commit()

    # ---- the administrator's queue ---------------------------------------

    def queue(self) -> TeacherQueueDto:
        """Everyone who says they are a teacher, waiting first.

        Waiting and approved in one call, because the administrator's screen
        shows both and the waiting list is meaningless without the context
        of who is already in.
        """
        with self._session() as db:
            rows = (
                db.query(User, TeacherProfile)
                .outerjoin(TeacherProfile, TeacherProfile.user_id == User.id)
                .filter(User.role == TEACHER)
                .all()
            )
            made = [self._as_dto(user, profile) for user, profile in rows]
            waiting = [t for t in made if not t.approved]
            approved = [t for t in made if t.approved]
            waiting.sort(key=lambda t: (t.profile.applied_at if t.profile else None) or datetime.max.replace(tzinfo=timezone.utc))
            approved.sort(key=lambda t: t.name.lower())
            return TeacherQueueDto(waiting=waiting, approved=approved)

    def decide(self, *, user_id: str, approve: bool, by: str) -> TeacherAccountDto:
        """Let a teacher in, or put them back to being a student.

        Refusing is not a rejection flag: the account becomes an ordinary
        student and the application goes. Somebody refused once is a student
        who can still use NISAAB, which is the right outcome, and a row
        marked "rejected" forever is not something anybody acts on.
        """
        if not approve:
            self.withdraw(user_id)
            return self.get_account(user_id)

        with self._session() as db:
            user = db.get(User, user_id)
            if user is None:
                raise NotFoundError("No such account")
            if user.role != TEACHER:
                raise RoleError("That account has not asked to be a teacher.")
            if db.get(TeacherProfile, user_id) is None:
                raise RoleError(
                    "That account has not finished its teacher application."
                )
            user.teacher_approved_at = datetime.now(timezone.utc)
            user.teacher_approved_by = by
            db.commit()
            db.refresh(user)
            logger.info("Teacher %s approved by %s", user_id, by)
            return self._as_dto(user, db.get(TeacherProfile, user_id))
