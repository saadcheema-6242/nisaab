"""Making, listing, revoking and reading a public share.

The rules about tokens and what may be shared live in edu_core.sharing,
where they are checked without a database. This is the part that needs
one.

Two audiences, and the difference between them is the point:

    The owner, signed in, who may create a share, see their own, and
    revoke any of them. Never anybody else's.

    A stranger, with a link and no account, who may read the shared
    quiz or paper and nothing else. That path writes exactly one thing -
    a counter - and reads only the row the token names.
"""

import logging
from contextlib import contextmanager
from datetime import datetime, timezone

from edu_db.models import PracticePaper, Quiz, QuizQuestion, Share, User
from edu_db.session import get_session_factory

from edu_core.exceptions import NotFoundError
from edu_core.sharing import (
    PAPER,
    QUIZ,
    ShareError,
    check_kind,
    check_title,
    is_readable,
    is_token_shaped,
    make_token,
)

logger = logging.getLogger(__name__)

# How many times a token is re-rolled before giving up. A collision at
# 160 bits will not happen; the loop exists so that if it somehow does,
# the result is a retry rather than an integrity error in a student's face.
TOKEN_TRIES = 5


class ShareService:
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

    # ---- the owner ------------------------------------------------------

    @staticmethod
    def _owned_target(db, kind: str, target_id: str, user_id: str):
        """The quiz or paper, if it belongs to this account.

        A share is made from something you own. Checking ownership here
        rather than trusting the page is what stops a student sharing
        somebody else's paper by pasting its id.
        """
        if kind == QUIZ:
            row = (
                db.query(Quiz)
                .join(Quiz.project)
                .filter(Quiz.id == target_id)
                .one_or_none()
            )
            if row is None or row.project is None or row.project.owner_id != user_id:
                return None
            return row
        row = (
            db.query(PracticePaper)
            .filter(
                PracticePaper.id == target_id,
                PracticePaper.user_id == user_id,
            )
            .one_or_none()
        )
        return row

    def create(
        self, *, user_id: str, kind: str, target_id: str, title: str | None = None
    ) -> Share:
        """Share a quiz or a paper, or return the share that already exists.

        Pressing Share twice should not mint a second link. A student who
        has already sent the first one to a group would have no way of
        knowing which of the two they must revoke.
        """
        kind = check_kind(kind)
        title = check_title(title)

        with self._session() as db:
            target = self._owned_target(db, kind, target_id, user_id)
            if target is None:
                # Deliberately the same answer as "no such quiz": a
                # student probing ids learns nothing about what exists.
                raise NotFoundError("That is not yours to share.")

            existing = (
                db.query(Share)
                .filter(
                    Share.user_id == user_id,
                    Share.kind == kind,
                    Share.target_id == target_id,
                    Share.revoked_at.is_(None),
                )
                .one_or_none()
            )
            if existing is not None:
                return existing

            row = None
            for _ in range(TOKEN_TRIES):
                token = make_token()
                if (
                    db.query(Share.id).filter(Share.token == token).one_or_none()
                    is None
                ):
                    row = Share(
                        token=token,
                        kind=kind,
                        target_id=target_id,
                        user_id=user_id,
                        title=title or getattr(target, "name", None)
                        or getattr(target, "title", None),
                    )
                    break
            if row is None:
                raise ShareError("Could not make a link just now. Try again.")

            db.add(row)
            db.commit()
            db.refresh(row)
            logger.info("Shared %s %s as %s", kind, target_id, row.token)
            return row

    def mine(self, user_id: str) -> list[Share]:
        """Every live link this account has made, newest first."""
        with self._session() as db:
            return (
                db.query(Share)
                .filter(Share.user_id == user_id, Share.revoked_at.is_(None))
                .order_by(Share.created_at.desc())
                .all()
            )

    def revoke(self, *, share_id: str, user_id: str) -> None:
        """Withdraw a link.

        Scoped to the owner in the query itself rather than fetched and
        then checked: a filter that is part of the question cannot be
        forgotten by a later edit.
        """
        with self._session() as db:
            row = (
                db.query(Share)
                .filter(Share.id == share_id, Share.user_id == user_id)
                .one_or_none()
            )
            if row is None:
                raise NotFoundError("No such share")
            if row.revoked_at is None:
                row.revoked_at = datetime.now(timezone.utc)
                db.commit()

    # ---- the stranger ---------------------------------------------------

    def read(self, token: str) -> dict:
        """What a public link shows. No account, no attempt, no marking.

        Everything this returns is content the owner chose to publish.
        It carries the owner's name, because a reader should know whose
        work they are looking at, and carries no email, no id and
        nothing about anybody else.
        """
        if not is_token_shaped(token):
            # Refused before the database is touched, so a public route
            # cannot be made to run a query per guess.
            raise NotFoundError("No such link")

        with self._session() as db:
            share = db.query(Share).filter(Share.token == token).one_or_none()
            if share is None or not is_readable(share.revoked_at):
                raise NotFoundError("No such link")

            owner = db.query(User).filter(User.id == share.user_id).one_or_none()
            body = (
                self._quiz_body(db, share.target_id)
                if share.kind == QUIZ
                else self._paper_body(db, share.target_id)
            )
            if body is None:
                # The quiz was deleted after being shared. A stale link
                # is not an error on the reader's part.
                raise NotFoundError("No such link")

            # The one write on this path. A counter, not a log: who read
            # a shared quiz is not something this product needs to know.
            share.opened_count = (share.opened_count or 0) + 1
            db.commit()

            return {
                "kind": share.kind,
                "title": share.title or body.get("title"),
                "shared_by": (owner.name if owner else None) or "A NISAAB student",
                "shared_at": share.created_at,
                **body,
            }

    @staticmethod
    def _quiz_body(db, quiz_id: str) -> dict | None:
        quiz = db.query(Quiz).filter(Quiz.id == quiz_id).one_or_none()
        if quiz is None:
            return None
        questions = (
            db.query(QuizQuestion)
            .filter(QuizQuestion.quiz_id == quiz_id)
            .order_by(QuizQuestion.position)
            .all()
        )
        return {
            "title": quiz.name,
            "description": quiz.description,
            "slo_code": quiz.slo_code,
            # The answers are included deliberately. The reader cannot
            # attempt this, so a quiz without its answers is a list of
            # questions they can do nothing with; with them it is study
            # material, which is what sharing is for.
            "questions": [
                {
                    "id": q.id,
                    "question_text": q.question_text,
                    "option_a": q.option_a,
                    "option_b": q.option_b,
                    "option_c": q.option_c,
                    "option_d": q.option_d,
                    "correct_option": q.correct_option,
                    "explanation": q.explanation,
                    "slo_code": q.slo_code,
                    "cognitive_level": q.cognitive_level,
                    # The picture travels with its credit, because the
                    # licences these come under require attribution and
                    # a shared page is where it would otherwise be lost.
                    "image_path": q.image_path,
                    "image_alt": q.image_alt,
                    "image_credit": q.image_credit,
                    "option_images": q.option_images,
                }
                for q in questions
            ],
        }

    @staticmethod
    def _paper_body(db, paper_id: str) -> dict | None:
        paper = (
            db.query(PracticePaper).filter(PracticePaper.id == paper_id).one_or_none()
        )
        if paper is None:
            return None
        return {
            "title": paper.title,
            "total_marks": paper.total_marks,
            "time_limit_minutes": paper.time_limit_minutes,
            "sections": paper.sections,
        }
