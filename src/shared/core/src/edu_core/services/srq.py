"""Short-response questions (SRQs): generate per SLO and mark written answers.

Both run inside the API request (about 5-15 seconds) rather than through the
worker queue, so the student gets the question and the marks straight away.
"""

from contextlib import contextmanager
from uuid import uuid4

from edu_ai.agents.slo_context import load_slo
from edu_ai.agents.srq_agent import generate_srq, mark_srq
from edu_ai.llm import GENERATION, MARKING, create_chat_model
from edu_db.models import PracticeRecord, Project, SrqAttempt, SrqQuestion
from edu_db.session import get_session_factory

from edu_core.exceptions import NotFoundError
from edu_core.services.content import usable_items
from edu_core.schemas.srq import (
    SrqAttemptDto,
    SrqDetailDto,
    SrqPointResultDto,
    SrqQuestionDto,
)


class SrqService:
    """Service for short-response questions and AI marking."""

    async def generate(
        self,
        project_id: str,
        user_id: str,
        slo_code: str,
        long: bool = False,
        marks: int | None = None,
        parts: bool = True,
        level: str | None = None,
    ) -> SrqQuestionDto:
        """Generate a new SRQ for an SLO (or, with long=True, a 6-mark ERQ).

        marks asks for an exact total; bank questions are reused only when they match it.

        level asks for a cognitive level (K, U or A). A paper decides its levels
        before anything is written, so a reused bank question at the wrong level
        is no use to it and is skipped.

        Raises:
            NotFoundError: If the project or SLO does not exist
        """
        with self._get_db_session() as db:
            project = self._get_project(db, project_id, user_id)
            slo = load_slo(db, slo_code, project)
            if slo is None:
                raise NotFoundError(f"SLO {slo_code} not found")
            language_code = project.language_code

            # A reviewed question from the shared bank that this student has not had yet
            if project.grade_subject_id and not long:
                used = {
                    source
                    for (source,) in db.query(SrqQuestion.source).filter(
                        SrqQuestion.project_id == project_id
                    )
                }
                for item in usable_items(db, project.grade_subject_id, slo.code, "srq"):
                    if f"bank:{item.id}" in used:
                        continue
                    if marks is not None and item.payload.get("marks") != marks:
                        continue
                    if level and item.payload.get("cognitive_level") != level:
                        continue
                    question = SrqQuestion(
                        id=str(uuid4()),
                        project_id=project_id,
                        slo_code=slo.code,
                        question=item.payload["question"],
                        marks=item.payload["marks"],
                        model_answer=item.payload["model_answer"],
                        rubric=item.payload["rubric"],
                        cognitive_level=item.payload.get("cognitive_level"),
                        source=f"bank:{item.id}",
                    )
                    db.add(question)
                    db.commit()
                    db.refresh(question)
                    return self._question_to_dto(question)

        llm = create_chat_model(task=GENERATION, temperature=0.7)
        generated = await generate_srq(
            llm, slo, language_code, long=long, marks=marks, parts=parts, level=level
        )

        with self._get_db_session() as db:
            question = SrqQuestion(
                id=str(uuid4()),
                project_id=project_id,
                slo_code=slo.code,
                question=generated.question,
                marks=generated.marks,
                model_answer=generated.model_answer,
                rubric=[p.model_dump() for p in generated.rubric],
                cognitive_level=(generated.cognitive_level or "").strip().upper()[:1] or None,
            )
            db.add(question)
            db.commit()
            db.refresh(question)
            return self._question_to_dto(question)

    def list_questions(
        self, project_id: str, user_id: str, slo_code: str | None = None
    ) -> list[SrqQuestionDto]:
        """List the SRQs of a project, newest first."""
        with self._get_db_session() as db:
            self._get_project(db, project_id, user_id)
            query = db.query(SrqQuestion).filter(SrqQuestion.project_id == project_id)
            if slo_code:
                query = query.filter(SrqQuestion.slo_code == slo_code)
            return [
                self._question_to_dto(q)
                for q in query.order_by(SrqQuestion.created_at.desc()).all()
            ]

    def get_question(self, project_id: str, question_id: str, user_id: str) -> SrqDetailDto:
        """Get an SRQ with the user's marked attempts.

        Raises:
            NotFoundError: If the project or question does not exist
        """
        with self._get_db_session() as db:
            question = self._get_question(db, project_id, question_id, user_id)
            attempts = (
                db.query(SrqAttempt)
                .filter(SrqAttempt.question_id == question_id, SrqAttempt.user_id == user_id)
                .order_by(SrqAttempt.created_at.desc())
                .all()
            )
            return SrqDetailDto(
                question=self._question_to_dto(question),
                attempts=[self._attempt_to_dto(a, question) for a in attempts],
            )

    async def mark(
        self, project_id: str, question_id: str, user_id: str, answer: str
    ) -> SrqAttemptDto:
        """Mark a written answer against the rubric and record it for mastery.

        Raises:
            NotFoundError: If the project or question does not exist
        """
        with self._get_db_session() as db:
            question = self._get_question(db, project_id, question_id, user_id)
            project = db.get(Project, project_id)
            slo = load_slo(db, question.slo_code, project) if question.slo_code else None
            fields = {
                "question": question.question,
                "marks": question.marks,
                "rubric": list(question.rubric or []),
                "model_answer": question.model_answer,
            }
            language_code = project.language_code

        llm = create_chat_model(task=MARKING, temperature=0)
        awarded, result = await mark_srq(
            llm, **fields, answer=answer, slo=slo, language_code=language_code
        )

        with self._get_db_session() as db:
            question = db.get(SrqQuestion, question_id)
            attempt = SrqAttempt(
                id=str(uuid4()),
                question_id=question_id,
                user_id=user_id,
                answer=answer,
                awarded_marks=awarded,
                max_marks=question.marks,
                result=result,
            )
            db.add(attempt)
            score = awarded / question.marks if question.marks else 0.0
            db.add(
                PracticeRecord(
                    id=str(uuid4()),
                    user_id=user_id,
                    project_id=project_id,
                    item_type="srq",
                    item_id=question_id,
                    topic=question.question[:100],
                    user_answer=answer[:2000],
                    correct_answer=question.model_answer,
                    was_correct=score >= 0.5,
                    score=score,
                    slo_code=question.slo_code,
                )
            )
            db.commit()
            db.refresh(attempt)
            return self._attempt_to_dto(attempt, question)

    @staticmethod
    def _get_project(db, project_id: str, user_id: str) -> Project:
        project = (
            db.query(Project)
            .filter(Project.id == project_id, Project.owner_id == user_id)
            .first()
        )
        if project is None:
            raise NotFoundError(f"Project {project_id} not found")
        return project

    def _get_question(self, db, project_id: str, question_id: str, user_id: str) -> SrqQuestion:
        self._get_project(db, project_id, user_id)
        question = (
            db.query(SrqQuestion)
            .filter(SrqQuestion.id == question_id, SrqQuestion.project_id == project_id)
            .first()
        )
        if question is None:
            raise NotFoundError(f"Question {question_id} not found")
        return question

    @staticmethod
    def _question_to_dto(question: SrqQuestion) -> SrqQuestionDto:
        return SrqQuestionDto(
            id=question.id,
            project_id=question.project_id,
            slo_code=question.slo_code,
            question=question.question,
            marks=question.marks,
            cognitive_level=question.cognitive_level,
            created_at=question.created_at,
        )

    @staticmethod
    def _attempt_to_dto(attempt: SrqAttempt, question: SrqQuestion) -> SrqAttemptDto:
        result = attempt.result or {}
        return SrqAttemptDto(
            id=attempt.id,
            question_id=attempt.question_id,
            answer=attempt.answer,
            awarded_marks=attempt.awarded_marks,
            max_marks=attempt.max_marks,
            points=[SrqPointResultDto(**p) for p in result.get("points", [])],
            feedback=result.get("feedback", ""),
            missing=result.get("missing", []),
            model_answer=question.model_answer,
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
