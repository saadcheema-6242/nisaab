"""Looking after the accounts: who is on the system, and what to do about them.

Three powers, in increasing order of how sorry you will be if you get it wrong:

- look, which is counting rather than reading. An administrator needs to know
  how much a student has before deciding anything; reading their chats is a
  different decision and this is not the screen for it.
- suspend, which is reversible. Temporary by default, because almost every
  real reason to stop an account is a cooling-off and not an ending.
- delete, which is not reversible at all, and so reports exactly what it
  removed rather than saying "done".

Everything here assumes the caller has already been checked. Deciding who is
an administrator is the router's job, done once, rather than a flag passed
around and eventually forgotten on one method.
"""

import logging
from contextlib import contextmanager
from datetime import datetime, timezone

from edu_db.models import (
    Chat,
    ChatMessage,
    CommunityPost,
    Document,
    Flashcard,
    FlashcardGroup,
    MindMap,
    Note,
    PracticePaper,
    PracticeRecord,
    Project,
    Quiz,
    SrqAttempt,
    StudentProfile,
    StudyPlan,
    User,
    UserUsage,
)
from edu_db.session import get_session_factory
from sqlalchemy import func, or_

from edu_core.exceptions import NotFoundError
from edu_core.moderation import ACTIVE, ban_state, until_from_days
from edu_core.schemas.admin import (
    AdminOverviewDto,
    AdminUsageDto,
    AdminUserDetailDto,
    AdminUserDto,
    AdminUserListDto,
    DeletionReportDto,
)

logger = logging.getLogger(__name__)

# How many accounts one page of the list holds
PAGE_SIZE = 50
# The longest a reason may be. It is read by the student, so it has to be a
# sentence, not an essay.
MAX_REASON = 500


class AdminService:
    """Reading and acting on accounts. The caller is already an administrator."""

    @contextmanager
    def _session(self):
        SessionLocal = get_session_factory()
        db = SessionLocal()
        try:
            yield db
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    # ---------------------------------------------------------------- read

    def list_users(
        self, search: str = "", limit: int = PAGE_SIZE, offset: int = 0
    ) -> AdminUserListDto:
        """Every account, newest first, with enough to judge it at a glance."""
        with self._session() as db:
            rows = db.query(User).outerjoin(
                StudentProfile, StudentProfile.user_id == User.id
            )
            wanted = (search or "").strip()
            if wanted:
                like = f"%{wanted.lower()}%"
                rows = rows.filter(
                    or_(
                        func.lower(User.email).like(like),
                        func.lower(User.name).like(like),
                        User.id == wanted,
                    )
                )

            total = rows.count()
            found = (
                rows.order_by(User.created_at.desc())
                .limit(max(1, min(limit, 200)))
                .offset(max(0, offset))
                .all()
            )

            # One query each for the related rows, keyed by user, rather than
            # one query per user per kind. With a few hundred students the
            # difference is a page that loads and a page that does not.
            ids = [user.id for user in found]
            profiles = self._by_user(db, StudentProfile, ids)
            usage = self._by_user(db, UserUsage, ids)
            answers = self._counts(db, PracticeRecord, ids)

            return AdminUserListDto(
                overview=self._overview(db),
                total=total,
                users=[
                    self._as_row(
                        user, profiles.get(user.id), usage.get(user.id),
                        answers.get(user.id, 0),
                    )
                    for user in found
                ],
            )

    def get_user(self, user_id: str) -> AdminUserDetailDto:
        """One account with everything it owns, counted."""
        with self._session() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if user is None:
                raise NotFoundError(f"No account with id {user_id}")

            profile = (
                db.query(StudentProfile)
                .filter(StudentProfile.user_id == user_id)
                .first()
            )
            usage = db.query(UserUsage).filter(UserUsage.user_id == user_id).first()
            owned = self._owned(db, user_id)

            projects = (
                db.query(Project).filter(Project.owner_id == user_id).all()
            )
            row = self._as_row(user, profile, usage, owned["practice_records"])
            return AdminUserDetailDto(
                **row.model_dump(),
                projects=len(projects),
                chats=owned["chats"],
                messages=owned["messages"],
                documents=owned["documents"],
                quizzes=owned["quizzes"],
                flashcard_groups=owned["flashcard_groups"],
                notes=owned["notes"],
                mind_maps=owned["mind_maps"],
                papers=owned["papers"],
                study_plans=owned["study_plans"],
                srq_attempts=owned["srq_attempts"],
                community_posts=owned["community_posts"],
                subjects=sorted(p.name for p in projects),
            )

    # --------------------------------------------------------------- write

    def set_ban(
        self,
        user_id: str,
        days: int | None,
        reason: str,
        by: str,
    ) -> AdminUserDto:
        """Suspend an account. ``days`` of None or 0 means permanently.

        The reason is required. An account that stops working with no stated
        cause produces a confused student and a complaint, and an
        administrator six months later with no idea why they did it.
        """
        said = (reason or "").strip()
        if not said:
            raise ValueError("A suspension needs a reason")
        if len(said) > MAX_REASON:
            raise ValueError(f"A reason can be at most {MAX_REASON} characters")

        with self._session() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if user is None:
                raise NotFoundError(f"No account with id {user_id}")

            now = datetime.now(timezone.utc)
            user.banned_at = now
            user.banned_until = until_from_days(days, now)
            user.ban_reason = said
            user.banned_by = by
            db.commit()
            db.refresh(user)
            logger.warning(
                "account %s suspended by %s until %s: %s",
                user_id, by, user.banned_until or "further notice", said,
            )
            return self._as_row(user, None, None, 0)

    def lift_ban(self, user_id: str) -> AdminUserDto:
        """Let an account back in, and clear the record of why it was stopped."""
        with self._session() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if user is None:
                raise NotFoundError(f"No account with id {user_id}")
            user.banned_at = None
            user.banned_until = None
            user.ban_reason = None
            user.banned_by = None
            db.commit()
            db.refresh(user)
            logger.warning("suspension lifted on account %s", user_id)
            return self._as_row(user, None, None, 0)

    def delete_user(self, user_id: str) -> DeletionReportDto:
        """Remove an account and everything it owns. There is no undo.

        Counted before it goes, and reported after, because "deleted" on its
        own tells an administrator nothing about what they just destroyed.
        """
        with self._session() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if user is None:
                raise NotFoundError(f"No account with id {user_id}")

            email = user.email
            removed = self._owned(db, user_id)
            removed["projects"] = (
                db.query(Project).filter(Project.owner_id == user_id).count()
            )

            # The foreign keys cascade, so deleting the account takes the rest
            # with it in one transaction. Doing it by hand would mean a
            # half-deleted student whenever a new table is added and missed.
            db.delete(user)
            db.commit()
            logger.warning("account %s (%s) deleted permanently", user_id, email)

            return DeletionReportDto(
                user_id=user_id,
                email=email,
                deleted={k: v for k, v in removed.items() if v},
                note=(
                    "The sign-in account itself lives with the identity "
                    "provider, not here. Remove it there as well, or this "
                    "person can sign in again and start over with an empty "
                    "workspace."
                ),
            )

    # -------------------------------------------------------------- shared

    @staticmethod
    def _by_user(db, model, ids: list[str]) -> dict:
        if not ids:
            return {}
        return {
            row.user_id: row
            for row in db.query(model).filter(model.user_id.in_(ids)).all()
        }

    @staticmethod
    def _counts(db, model, ids: list[str]) -> dict[str, int]:
        if not ids:
            return {}
        rows = (
            db.query(model.user_id, func.count(model.id))
            .filter(model.user_id.in_(ids))
            .group_by(model.user_id)
            .all()
        )
        return {user_id: count for user_id, count in rows}

    @staticmethod
    def _owned(db, user_id: str) -> dict[str, int]:
        """How many rows of each kind this account owns."""
        def n(model, column=None):
            column = column if column is not None else model.user_id
            return db.query(func.count(model.id)).filter(column == user_id).scalar() or 0

        chat_ids = [
            row.id for row in db.query(Chat.id).filter(Chat.user_id == user_id).all()
        ]
        messages = 0
        if chat_ids:
            messages = (
                db.query(func.count(ChatMessage.id))
                .filter(ChatMessage.chat_id.in_(chat_ids))
                .scalar()
                or 0
            )
        group_ids = [
            row.id
            for row in db.query(FlashcardGroup.id)
            .filter(FlashcardGroup.user_id == user_id)
            .all()
        ]
        flashcards = 0
        if group_ids:
            flashcards = (
                db.query(func.count(Flashcard.id))
                .filter(Flashcard.group_id.in_(group_ids))
                .scalar()
                or 0
            )

        return {
            "chats": len(chat_ids),
            "messages": messages,
            "documents": n(Document, Document.owner_id),
            "quizzes": n(Quiz),
            "flashcard_groups": len(group_ids),
            "flashcards": flashcards,
            "notes": n(Note),
            "mind_maps": n(MindMap),
            "papers": n(PracticePaper),
            "study_plans": n(StudyPlan),
            "practice_records": n(PracticeRecord),
            "srq_attempts": n(SrqAttempt),
            "community_posts": n(CommunityPost),
        }

    @staticmethod
    def _overview(db) -> AdminOverviewDto:
        """The whole system in a few numbers."""
        today = datetime.now(timezone.utc).date()
        groups = dict(
            db.query(StudentProfile.group_code, func.count(StudentProfile.user_id))
            .group_by(StudentProfile.group_code)
            .all()
        )
        grades = dict(
            db.query(StudentProfile.grade, func.count(StudentProfile.user_id))
            .group_by(StudentProfile.grade)
            .all()
        )
        active = 0
        for usage in db.query(UserUsage).all():
            reset = usage.last_reset_date
            used = (
                usage.chat_messages_today
                or usage.quiz_generations_today
                or usage.flashcard_generations_today
                or usage.mindmap_generations_today
                or usage.document_uploads_today
            )
            if used and reset and reset.date() == today:
                active += 1

        banned = 0
        for user in db.query(User.banned_at, User.banned_until).filter(
            User.banned_at.isnot(None)
        ):
            if ban_state(user.banned_at, user.banned_until) != ACTIVE:
                banned += 1

        return AdminOverviewDto(
            total_users=db.query(func.count(User.id)).scalar() or 0,
            onboarded_users=db.query(func.count(StudentProfile.user_id))
            .filter(StudentProfile.onboarding_completed_at.isnot(None))
            .scalar()
            or 0,
            banned_users=banned,
            active_today=active,
            by_group={str(k): v for k, v in groups.items() if k},
            by_grade={str(k): v for k, v in grades.items() if k},
            practice_answers=db.query(func.count(PracticeRecord.id)).scalar() or 0,
        )

    @staticmethod
    def _as_row(user, profile, usage, answers: int) -> AdminUserDto:
        return AdminUserDto(
            id=user.id,
            name=user.name,
            email=user.email,
            created_at=user.created_at,
            grade=getattr(profile, "grade", None),
            group_code=getattr(profile, "group_code", None),
            language=getattr(profile, "explanation_language", None),
            onboarded=bool(getattr(profile, "onboarding_completed_at", None)),
            ban_state=ban_state(user.banned_at, user.banned_until),
            banned_until=user.banned_until,
            ban_reason=user.ban_reason,
            banned_by=user.banned_by,
            practice_answers=answers,
            usage=AdminUsageDto(
                chat_messages=getattr(usage, "chat_messages_today", 0) or 0,
                flashcard_generations=getattr(usage, "flashcard_generations_today", 0) or 0,
                quiz_generations=getattr(usage, "quiz_generations_today", 0) or 0,
                mindmap_generations=getattr(usage, "mindmap_generations_today", 0) or 0,
                document_uploads=getattr(usage, "document_uploads_today", 0) or 0,
                last_reset=getattr(usage, "last_reset_date", None),
            ),
        )
