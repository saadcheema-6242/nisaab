"""Finished practice attempts: scored on the server and recorded for SLO mastery."""

from contextlib import contextmanager
from uuid import uuid4

from edu_db.models import (
    Flashcard,
    FlashcardGroup,
    MindMap,
    Note,
    PracticeAttempt,
    PracticePaper,
    PracticeRecord,
    Project,
    Quiz,
    QuizQuestion,
    StudyPlan,
)
from edu_db.session import get_session_factory

from edu_core.exceptions import NotFoundError
from edu_core.schemas.attempts import (
    AttemptSummaryDto,
    FlashcardAttemptDto,
    FlashcardResultDto,
    PracticeHistoryItemDto,
    QuizAnswerResultDto,
    QuizAttemptDto,
)


class AttemptService:
    """Service for scoring and storing practice attempts."""

    def submit_quiz(
        self, user_id: str, project_id: str, quiz_id: str, answers: dict[str, str | None]
    ) -> QuizAttemptDto:
        """Score the answers ({question_id: option}), record them and return the result.

        Raises:
            NotFoundError: If the project or quiz does not exist
        """
        with self._get_db_session() as db:
            self._check_quiz(db, user_id, project_id, quiz_id)
            questions = (
                db.query(QuizQuestion)
                .filter(QuizQuestion.quiz_id == quiz_id)
                .order_by(QuizQuestion.position)
                .all()
            )
            results = []
            for question in questions:
                chosen = (answers.get(question.id) or "").strip().lower()[:1] or None
                correct = question.correct_option.strip().lower()[:1]
                is_correct = chosen == correct
                results.append(
                    QuizAnswerResultDto(
                        question_id=question.id,
                        chosen=chosen,
                        correct_option=correct,
                        is_correct=is_correct,
                    )
                )
                if chosen is not None:
                    db.add(
                        PracticeRecord(
                            id=str(uuid4()),
                            user_id=user_id,
                            project_id=project_id,
                            item_type="quiz",
                            item_id=question.id,
                            topic=question.question_text[:100],
                            user_answer=chosen,
                            correct_answer=correct,
                            was_correct=is_correct,
                            slo_code=question.slo_code,
                        )
                    )
            attempt = PracticeAttempt(
                id=str(uuid4()),
                user_id=user_id,
                project_id=project_id,
                kind="quiz",
                ref_id=quiz_id,
                answers=[r.model_dump() for r in results],
                score=float(sum(r.is_correct for r in results)),
                max_score=float(len(results)),
            )
            db.add(attempt)
            db.commit()
            db.refresh(attempt)
            return self._to_dto(attempt, len(self._attempts(db, user_id, "quiz", quiz_id)))

    def latest_quiz_attempt(
        self, user_id: str, project_id: str, quiz_id: str
    ) -> tuple[QuizAttemptDto | None, list[AttemptSummaryDto]]:
        """The user's most recent attempt at the quiz (if any) and all their attempts."""
        with self._get_db_session() as db:
            self._check_quiz(db, user_id, project_id, quiz_id)
            attempts = self._attempts(db, user_id, "quiz", quiz_id)
            history = [
                AttemptSummaryDto(
                    id=a.id,
                    number=number,
                    score=a.score,
                    max_score=a.max_score,
                    created_at=a.created_at,
                )
                for number, a in enumerate(attempts, start=1)
            ]
            latest = self._to_dto(attempts[-1], len(attempts)) if attempts else None
            return latest, history

    def history(
        self, user_id: str, project_id: str, limit: int = 100
    ) -> list[PracticeHistoryItemDto]:
        """Everything in the workspace, newest first.

        Two kinds of row, in one list:

        - a finished attempt at a quiz, flashcard set or paper, numbered per item
          ("Attempt 2") and carrying its score;
        - anything the tutor made that was never attempted - a mind map, a note,
          a study plan, or a quiz still waiting to be sat. These have no score,
          so a student can find everything they have been given, not only the
          things they have already done.

        Attempts at deleted items are left out.

        Raises:
            NotFoundError: If the project does not exist
        """
        with self._get_db_session() as db:
            project = (
                db.query(Project)
                .filter(Project.id == project_id, Project.owner_id == user_id)
                .first()
            )
            if project is None:
                raise NotFoundError(f"Project {project_id} not found")
            attempts = (
                db.query(PracticeAttempt)
                .filter(
                    PracticeAttempt.user_id == user_id,
                    PracticeAttempt.project_id == project_id,
                )
                .order_by(PracticeAttempt.created_at)
                .all()
            )

            def names(model, column, kind: str) -> dict[str, str]:
                ids = {a.ref_id for a in attempts if a.kind == kind}
                if not ids:
                    return {}
                rows = db.query(model.id, column).filter(model.id.in_(ids)).all()
                return {row[0]: row[1] for row in rows}

            titles = {
                "quiz": names(Quiz, Quiz.name, "quiz"),
                "flashcards": names(FlashcardGroup, FlashcardGroup.name, "flashcards"),
                "paper": names(PracticePaper, PracticePaper.title, "paper"),
            }
            counts: dict[tuple[str, str], int] = {}
            items = []
            attempted: set[tuple[str, str]] = set()
            for attempt in attempts:
                key = (attempt.kind, attempt.ref_id)
                counts[key] = counts.get(key, 0) + 1
                title = titles.get(attempt.kind, {}).get(attempt.ref_id)
                if title is None:
                    continue
                attempted.add(key)
                items.append(
                    PracticeHistoryItemDto(
                        id=attempt.id,
                        kind=attempt.kind,
                        ref_id=attempt.ref_id,
                        title=title,
                        number=counts[key],
                        score=attempt.score,
                        max_score=attempt.max_score,
                        created_at=attempt.created_at,
                    )
                )

            # Everything the tutor made, so nothing is hidden just because the
            # student has not sat it yet. A mind map records generated_at rather
            # than created_at, and a study plan has no title of its own.
            made = [
                ("quiz", Quiz, Quiz.name, Quiz.created_at),
                ("flashcards", FlashcardGroup, FlashcardGroup.name, FlashcardGroup.created_at),
                ("paper", PracticePaper, PracticePaper.title, PracticePaper.created_at),
                ("mind_map", MindMap, MindMap.title, MindMap.generated_at),
                ("note", Note, Note.title, Note.created_at),
            ]
            for kind, model, name, made_at in made:
                rows = (
                    db.query(model.id, name, made_at)
                    .filter(model.project_id == project_id)
                    .all()
                )
                for ref_id, title, created_at in rows:
                    if (kind, ref_id) in attempted:
                        continue
                    items.append(
                        PracticeHistoryItemDto(
                            id=f"{kind}:{ref_id}",
                            kind=kind,
                            ref_id=ref_id,
                            title=title or "Untitled",
                            number=None,
                            score=None,
                            max_score=None,
                            created_at=created_at,
                        )
                    )

            # A study plan has no title column, so it is named here rather than
            # selected.
            plans = (
                db.query(StudyPlan.id, StudyPlan.created_at)
                .filter(StudyPlan.project_id == project_id)
                .all()
            )
            for plan_id, created_at in plans:
                items.append(
                    PracticeHistoryItemDto(
                        id=f"study_plan:{plan_id}",
                        kind="study_plan",
                        ref_id=plan_id,
                        title="Study plan",
                        number=None,
                        score=None,
                        max_score=None,
                        created_at=created_at,
                    )
                )

            items.sort(key=lambda item: item.created_at, reverse=True)
            return items[:limit]

    @staticmethod
    def _attempts(db, user_id: str, kind: str, ref_id: str) -> list[PracticeAttempt]:
        """The user's attempts at one quiz, flashcard set or paper, first to last."""
        return (
            db.query(PracticeAttempt)
            .filter(
                PracticeAttempt.user_id == user_id,
                PracticeAttempt.kind == kind,
                PracticeAttempt.ref_id == ref_id,
            )
            .order_by(PracticeAttempt.created_at)
            .all()
        )

    def submit_flashcards(
        self, user_id: str, project_id: str, group_id: str, knew: dict[str, bool]
    ) -> FlashcardAttemptDto:
        """Record which cards the student knew ({flashcard_id: knew}) for mastery.

        Raises:
            NotFoundError: If the project or flashcard set does not exist
        """
        with self._get_db_session() as db:
            self._check_group(db, user_id, project_id, group_id)
            cards = (
                db.query(Flashcard)
                .filter(Flashcard.group_id == group_id)
                .order_by(Flashcard.position)
                .all()
            )
            results = []
            for card in cards:
                if card.id not in knew:
                    continue
                results.append(FlashcardResultDto(flashcard_id=card.id, knew=knew[card.id]))
                db.add(
                    PracticeRecord(
                        id=str(uuid4()),
                        user_id=user_id,
                        project_id=project_id,
                        item_type="flashcard",
                        item_id=card.id,
                        topic=card.question[:100],
                        user_answer=None,
                        correct_answer=card.answer,
                        was_correct=knew[card.id],
                        slo_code=card.slo_code,
                    )
                )
            attempt = PracticeAttempt(
                id=str(uuid4()),
                user_id=user_id,
                project_id=project_id,
                kind="flashcards",
                ref_id=group_id,
                answers=[r.model_dump() for r in results],
                score=float(sum(r.knew for r in results)),
                max_score=float(len(results)),
            )
            db.add(attempt)
            db.commit()
            db.refresh(attempt)
            return self._flashcards_to_dto(
                attempt, len(self._attempts(db, user_id, "flashcards", group_id))
            )

    def latest_flashcards_attempt(
        self, user_id: str, project_id: str, group_id: str
    ) -> FlashcardAttemptDto | None:
        """The user's most recent run through the flashcard set, if any."""
        with self._get_db_session() as db:
            self._check_group(db, user_id, project_id, group_id)
            attempts = self._attempts(db, user_id, "flashcards", group_id)
            return self._flashcards_to_dto(attempts[-1], len(attempts)) if attempts else None

    @staticmethod
    def _check_group(db, user_id: str, project_id: str, group_id: str) -> None:
        project = (
            db.query(Project)
            .filter(Project.id == project_id, Project.owner_id == user_id)
            .first()
        )
        group = (
            db.query(FlashcardGroup)
            .filter(FlashcardGroup.id == group_id, FlashcardGroup.project_id == project_id)
            .first()
        )
        if project is None or group is None:
            raise NotFoundError(f"Flashcard set {group_id} not found")

    @staticmethod
    def _flashcards_to_dto(attempt: PracticeAttempt, number: int) -> FlashcardAttemptDto:
        return FlashcardAttemptDto(
            id=attempt.id,
            group_id=attempt.ref_id,
            number=number,
            known=attempt.score,
            total=attempt.max_score,
            results=[FlashcardResultDto(**r) for r in attempt.answers or []],
            created_at=attempt.created_at,
        )

    @staticmethod
    def _check_quiz(db, user_id: str, project_id: str, quiz_id: str) -> None:
        project = (
            db.query(Project)
            .filter(Project.id == project_id, Project.owner_id == user_id)
            .first()
        )
        quiz = db.query(Quiz).filter(Quiz.id == quiz_id, Quiz.project_id == project_id).first()
        if project is None or quiz is None:
            raise NotFoundError(f"Quiz {quiz_id} not found")

    @staticmethod
    def _to_dto(attempt: PracticeAttempt, number: int) -> QuizAttemptDto:
        return QuizAttemptDto(
            id=attempt.id,
            quiz_id=attempt.ref_id,
            number=number,
            score=attempt.score,
            max_score=attempt.max_score,
            answers=[QuizAnswerResultDto(**a) for a in attempt.answers or []],
            created_at=attempt.created_at,
        )

    @contextmanager
    def _get_db_session(self):
        """Context manager for database sessions."""
        SessionLocal = get_session_factory()
        db = SessionLocal()
        try:
            yield db
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
