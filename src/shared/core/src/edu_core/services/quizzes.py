"""CRUD service for managing quizzes."""

import asyncio
from contextlib import contextmanager
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from edu_db.models import Project, Quiz, QuizQuestion
from edu_db.session import get_session_factory

from edu_core import practice_options as options
from edu_core.exceptions import NotFoundError
from edu_core.services.content import usable_items
from edu_core.schemas.quizzes import QuizDto, QuizQuestionDto

if TYPE_CHECKING:
    from edu_queue.service import QueueService


class QuizService:
    """Service for managing quizzes."""

    def __init__(self, queue_service: "QueueService") -> None:
        """Initialize the quiz service.

        Args:
            queue_service: QueueService instance for async generation tasks
        """
        self.queue_service = queue_service

    def create_quiz(
        self,
        project_id: str,
        name: str,
        description: str | None = None,
    ) -> QuizDto:
        """Create a new quiz.

        Args:
            project_id: The project ID
            name: The quiz name
            description: Optional quiz description

        Returns:
            Created QuizDto
        """
        with self._get_db_session() as db:
            try:
                quiz = Quiz(
                    id=str(uuid4()),
                    project_id=project_id,
                    name=name,
                    description=description,
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                )
                db.add(quiz)
                db.commit()
                db.refresh(quiz)

                return self._model_to_dto(quiz)
            except Exception:
                db.rollback()
                raise

    def get_quiz(self, quiz_id: str, project_id: str) -> QuizDto:
        """Get a quiz by ID.

        Args:
            quiz_id: The quiz ID
            project_id: The project ID

        Returns:
            QuizDto

        Raises:
            NotFoundError: If quiz not found
        """
        with self._get_db_session() as db:
            try:
                quiz = (
                    db.query(Quiz)
                    .filter(Quiz.id == quiz_id, Quiz.project_id == project_id)
                    .first()
                )
                if not quiz:
                    raise NotFoundError(f"Quiz {quiz_id} not found")

                return self._model_to_dto(quiz)
            except NotFoundError:
                raise
            except Exception:
                raise

    def list_quizzes(self, project_id: str) -> list[QuizDto]:
        """List all quizzes for a project.

        Args:
            project_id: The project ID

        Returns:
            List of QuizDto instances
        """
        with self._get_db_session() as db:
            try:
                quizzes = (
                    db.query(Quiz)
                    .filter(Quiz.project_id == project_id)
                    .order_by(Quiz.created_at.desc())
                    .all()
                )
                return [self._model_to_dto(quiz) for quiz in quizzes]
            except Exception:
                raise

    def update_quiz(
        self,
        quiz_id: str,
        project_id: str,
        name: str | None = None,
        description: str | None = None,
    ) -> QuizDto:
        """Update a quiz.

        Args:
            quiz_id: The quiz ID
            project_id: The project ID
            name: Optional new name
            description: Optional new description

        Returns:
            Updated QuizDto

        Raises:
            NotFoundError: If quiz not found
        """
        with self._get_db_session() as db:
            try:
                quiz = (
                    db.query(Quiz)
                    .filter(Quiz.id == quiz_id, Quiz.project_id == project_id)
                    .first()
                )
                if not quiz:
                    raise NotFoundError(f"Quiz {quiz_id} not found")

                if name is not None:
                    quiz.name = name
                if description is not None:
                    quiz.description = description
                quiz.updated_at = datetime.now()

                db.commit()
                db.refresh(quiz)

                return self._model_to_dto(quiz)
            except NotFoundError:
                raise
            except Exception:
                db.rollback()
                raise

    def delete_quiz(self, quiz_id: str, project_id: str) -> None:
        """Delete a quiz.

        Args:
            quiz_id: The quiz ID
            project_id: The project ID

        Raises:
            NotFoundError: If quiz not found
        """
        with self._get_db_session() as db:
            try:
                quiz = (
                    db.query(Quiz)
                    .filter(Quiz.id == quiz_id, Quiz.project_id == project_id)
                    .first()
                )
                if not quiz:
                    raise NotFoundError(f"Quiz {quiz_id} not found")

                db.delete(quiz)
                db.commit()
            except NotFoundError:
                raise
            except Exception:
                db.rollback()
                raise

    def _model_to_dto(self, quiz: Quiz) -> QuizDto:
        """Convert Quiz model to QuizDto."""
        return QuizDto(
            id=quiz.id,
            project_id=quiz.project_id,
            name=quiz.name,
            description=quiz.description,
            slo_code=quiz.slo_code,
            created_at=quiz.created_at,
            updated_at=quiz.updated_at,
        )

    def create_quiz_question(
        self,
        quiz_id: str,
        project_id: str,
        question_text: str,
        option_a: str,
        option_b: str,
        option_c: str,
        option_d: str,
        correct_option: str,
        explanation: str | None = None,
        difficulty_level: str = "medium",
        position: int | None = None,
    ) -> QuizQuestionDto:
        """Create a new quiz question.

        Args:
            quiz_id: The quiz ID
            project_id: The project ID
            question_text: The question text
            option_a: Option A
            option_b: Option B
            option_c: Option C
            option_d: Option D
            correct_option: Correct option (a, b, c, or d)
            explanation: Optional explanation
            difficulty_level: Difficulty level (easy, medium, hard)
            position: Optional position for ordering (auto-assigned if None)

        Returns:
            Created QuizQuestionDto

        Raises:
            NotFoundError: If quiz not found
        """
        with self._get_db_session() as db:
            try:
                # Verify quiz exists
                quiz = (
                    db.query(Quiz)
                    .filter(Quiz.id == quiz_id, Quiz.project_id == project_id)
                    .first()
                )
                if not quiz:
                    raise NotFoundError(f"Quiz {quiz_id} not found")

                # Auto-assign position if not provided
                if position is None:
                    max_position = (
                        db.query(QuizQuestion.position)
                        .filter(QuizQuestion.quiz_id == quiz_id)
                        .order_by(QuizQuestion.position.desc())
                        .limit(1)
                        .scalar()
                    )
                    position = (max_position + 1) if max_position is not None else 0

                question = QuizQuestion(
                    id=str(uuid4()),
                    quiz_id=quiz_id,
                    project_id=project_id,
                    question_text=question_text,
                    option_a=option_a,
                    option_b=option_b,
                    option_c=option_c,
                    option_d=option_d,
                    correct_option=correct_option,
                    explanation=explanation,
                    difficulty_level=difficulty_level,
                    position=position,
                    created_at=datetime.now(),
                )
                db.add(question)
                db.commit()
                db.refresh(question)

                return self._question_model_to_dto(question)
            except NotFoundError:
                raise
            except Exception:
                db.rollback()
                raise

    def get_quiz_question(
        self, question_id: str, quiz_id: str, project_id: str
    ) -> QuizQuestionDto:
        """Get a quiz question by ID.

        Args:
            question_id: The question ID
            quiz_id: The quiz ID
            project_id: The project ID

        Returns:
            QuizQuestionDto

        Raises:
            NotFoundError: If question not found
        """
        with self._get_db_session() as db:
            try:
                question = (
                    db.query(QuizQuestion)
                    .filter(
                        QuizQuestion.id == question_id,
                        QuizQuestion.quiz_id == quiz_id,
                        QuizQuestion.project_id == project_id,
                    )
                    .first()
                )
                if not question:
                    raise NotFoundError(f"Quiz question {question_id} not found")

                return self._question_model_to_dto(question)
            except NotFoundError:
                raise
            except Exception:
                raise

    def list_quiz_questions(
        self, quiz_id: str, project_id: str
    ) -> list[QuizQuestionDto]:
        """List all questions in a quiz.

        Args:
            quiz_id: The quiz ID
            project_id: The project ID

        Returns:
            List of QuizQuestionDto instances
        """
        with self._get_db_session() as db:
            try:
                questions = (
                    db.query(QuizQuestion)
                    .filter(
                        QuizQuestion.quiz_id == quiz_id,
                        QuizQuestion.project_id == project_id,
                    )
                    .order_by(QuizQuestion.position.asc())
                    .all()
                )
                return [self._question_model_to_dto(q) for q in questions]
            except Exception:
                raise

    def update_quiz_question(
        self,
        question_id: str,
        quiz_id: str,
        project_id: str,
        question_text: str | None = None,
        option_a: str | None = None,
        option_b: str | None = None,
        option_c: str | None = None,
        option_d: str | None = None,
        correct_option: str | None = None,
        explanation: str | None = None,
        difficulty_level: str | None = None,
        position: int | None = None,
    ) -> QuizQuestionDto:
        """Update a quiz question.

        Args:
            question_id: The question ID
            quiz_id: The quiz ID
            project_id: The project ID
            question_text: Optional new question text
            option_a: Optional new option A
            option_b: Optional new option B
            option_c: Optional new option C
            option_d: Optional new option D
            correct_option: Optional new correct option
            explanation: Optional new explanation
            difficulty_level: Optional new difficulty level
            position: Optional new position

        Returns:
            Updated QuizQuestionDto

        Raises:
            NotFoundError: If question not found
        """
        with self._get_db_session() as db:
            try:
                question = (
                    db.query(QuizQuestion)
                    .filter(
                        QuizQuestion.id == question_id,
                        QuizQuestion.quiz_id == quiz_id,
                        QuizQuestion.project_id == project_id,
                    )
                    .first()
                )
                if not question:
                    raise NotFoundError(f"Quiz question {question_id} not found")

                if question_text is not None:
                    question.question_text = question_text
                if option_a is not None:
                    question.option_a = option_a
                if option_b is not None:
                    question.option_b = option_b
                if option_c is not None:
                    question.option_c = option_c
                if option_d is not None:
                    question.option_d = option_d
                if correct_option is not None:
                    question.correct_option = correct_option
                if explanation is not None:
                    question.explanation = explanation
                if difficulty_level is not None:
                    question.difficulty_level = difficulty_level
                if position is not None:
                    question.position = position

                db.commit()
                db.refresh(question)

                return self._question_model_to_dto(question)
            except NotFoundError:
                raise
            except Exception:
                db.rollback()
                raise

    def delete_quiz_question(
        self, question_id: str, quiz_id: str, project_id: str
    ) -> None:
        """Delete a quiz question.

        Args:
            question_id: The question ID
            quiz_id: The quiz ID
            project_id: The project ID

        Raises:
            NotFoundError: If question not found
        """
        with self._get_db_session() as db:
            try:
                question = (
                    db.query(QuizQuestion)
                    .filter(
                        QuizQuestion.id == question_id,
                        QuizQuestion.quiz_id == quiz_id,
                        QuizQuestion.project_id == project_id,
                    )
                    .first()
                )
                if not question:
                    raise NotFoundError(f"Quiz question {question_id} not found")

                db.delete(question)
                db.commit()
            except NotFoundError:
                raise
            except Exception:
                db.rollback()
                raise

    def reorder_quiz_questions(
        self, quiz_id: str, project_id: str, question_ids: list[str]
    ) -> list[QuizQuestionDto]:
        """Reorder quiz questions.

        Args:
            quiz_id: The quiz ID
            project_id: The project ID
            question_ids: List of question IDs in the desired order

        Returns:
            List of updated QuizQuestionDto instances

        Raises:
            NotFoundError: If quiz or any question not found
        """
        with self._get_db_session() as db:
            try:
                # Verify quiz exists
                quiz = (
                    db.query(Quiz)
                    .filter(Quiz.id == quiz_id, Quiz.project_id == project_id)
                    .first()
                )
                if not quiz:
                    raise NotFoundError(f"Quiz {quiz_id} not found")

                # Update positions
                questions = []
                for position, question_id in enumerate(question_ids):
                    question = (
                        db.query(QuizQuestion)
                        .filter(
                            QuizQuestion.id == question_id,
                            QuizQuestion.quiz_id == quiz_id,
                            QuizQuestion.project_id == project_id,
                        )
                        .first()
                    )
                    if not question:
                        raise NotFoundError(f"Quiz question {question_id} not found")
                    question.position = position
                    questions.append(question)

                db.commit()
                for q in questions:
                    db.refresh(q)

                return [self._question_model_to_dto(q) for q in questions]
            except NotFoundError:
                raise
            except Exception:
                db.rollback()
                raise

    def _question_model_to_dto(self, question: QuizQuestion) -> QuizQuestionDto:
        """Convert QuizQuestion model to QuizQuestionDto."""
        return QuizQuestionDto(
            id=question.id,
            quiz_id=question.quiz_id,
            project_id=question.project_id,
            question_text=question.question_text,
            option_a=question.option_a,
            option_b=question.option_b,
            option_c=question.option_c,
            option_d=question.option_d,
            correct_option=question.correct_option,
            explanation=question.explanation,
            difficulty_level=question.difficulty_level,
            position=question.position,
            slo_code=question.slo_code,
            cognitive_level=question.cognitive_level,
            created_at=question.created_at,
        )

    def queue_generation(
        self,
        quiz_id: str,
        project_id: str,
        topic: str | None = None,
        custom_instructions: str | None = None,
        count: int | None = None,
        user_id: str | None = None,
        slo_code: str | None = None,
    ) -> QuizDto:
        """Queue a quiz generation request to be processed by a worker.

        Args:
            quiz_id: The quiz ID to populate
            project_id: The project ID
            queue_service: QueueService instance to send the message
            topic: Optional topic for generation
            custom_instructions: Optional custom instructions
            count: Optional count of questions to generate
            user_id: Optional user ID for queue message
            slo_code: Optional FBISE SLO the questions must assess

        Returns:
            Existing QuizDto (generation will happen asynchronously)

        Raises:
            NotFoundError: If quiz not found
        """
        from edu_queue.schemas import QueueTaskMessage, QuizGenerationData, TaskType

        # Verify quiz exists
        quiz = self.get_quiz(quiz_id=quiz_id, project_id=project_id)

        # Prepare task data
        task_data: QuizGenerationData = {
            "project_id": project_id,
            "quiz_id": quiz_id,
        }
        if topic:
            task_data["topic"] = topic
        if custom_instructions:
            task_data["custom_instructions"] = custom_instructions
        if user_id:
            task_data["user_id"] = user_id
        if count is not None:
            task_data["count"] = count
        if slo_code:
            task_data["slo_code"] = slo_code
            quiz = self._set_slo_code(quiz_id, slo_code)
            # Reviewed questions from the shared bank are ready instantly
            if self._fill_from_bank(quiz_id, project_id, slo_code, count or 10):
                return self.get_quiz(quiz_id=quiz_id, project_id=project_id)

        # Send message to queue
        task_message: QueueTaskMessage = {
            "type": TaskType.QUIZ_GENERATION,
            "data": task_data,
        }
        self.queue_service.send_message(task_message)

        return quiz

    def _fill_from_bank(
        self, quiz_id: str, project_id: str, slo_code: str, count: int, minimum: int = 3
    ) -> bool:
        """Fill the quiz with bank MCQs for the SLO; False if the bank has fewer than minimum."""
        with self._get_db_session() as db:
            project = db.get(Project, project_id)
            if project is None or not project.grade_subject_id:
                return False
            items = usable_items(db, project.grade_subject_id, slo_code, "mcq")[:count]
            if len(items) < minimum:
                return False
            quiz = db.query(Quiz).filter(Quiz.id == quiz_id).one()
            reviewed = all(item.review_status == "approved" for item in items)
            quiz.name = f"SLO {slo_code}: practice"
            quiz.description = (
                "Questions checked by a subject teacher"
                if reviewed
                else "Practice questions for this SLO"
            )
            db.query(QuizQuestion).filter(QuizQuestion.quiz_id == quiz_id).delete()
            fields = (
                "question_text", "option_a", "option_b", "option_c", "option_d",
                "correct_option", "explanation",
            )
            for position, item in enumerate(items):
                db.add(
                    QuizQuestion(
                        id=str(uuid4()),
                        quiz_id=quiz_id,
                        project_id=project_id,
                        **{field: item.payload.get(field) for field in fields},
                        difficulty_level=item.payload.get("difficulty_level") or "medium",
                        cognitive_level=item.payload.get("cognitive_level"),
                        slo_code=slo_code,
                        position=position,
                        created_at=datetime.now(),
                    )
                )
            db.commit()
            return True

    async def create_practice_quiz(
        self,
        project_id: str,
        topic: str,
        count: int = 5,
        slo_code: str | None = None,
        search_service=None,
        slo_codes: list[str] | None = None,
        style: str = "mixed",
        level: str = "board",
        notes: str | None = None,
    ) -> tuple[QuizDto, int, str]:
        """Make a quiz to attempt right away (e.g. inside the chat).

        Uses the SLOs the student chose (or the best match for the topic), spreading
        the questions over them. Teacher-bank questions that suit the chosen question
        type (theory, numerical, derivation, mixed) and level (easy, board,
        challenging) come first; the AI writes the rest now, in parallel.
        Returns (quiz, number of questions, "bank", "ai" or "mixed").
        """
        from edu_ai.agents.bank_agent import generate_mcqs
        from edu_ai.agents.quiz_agent import QuizAgent
        from edu_ai.agents.slo_context import load_slo
        from edu_ai.llm import GENERATION, create_chat_model
        from edu_ai.tools.syllabus import resolve_slos

        count = max(3, min(count, 20))
        style, level = options.normalize_style(style), options.normalize_level(level)
        extra = options.instructions(style, notes)
        with self._get_db_session() as db:
            project = db.get(Project, project_id)
            if project is None:
                raise NotFoundError(f"Project {project_id} not found")
            grade_subject_id = project.grade_subject_id
            language_code = project.language_code
        wanted = [*(slo_codes or []), *([slo_code] if slo_code else [])]
        codes = resolve_slos(grade_subject_id, topic, wanted) if grade_subject_id else []

        if not codes:
            # Not a syllabus topic: a general AI quiz on the topic
            quiz = self.create_quiz(project_id=project_id, name=f"{topic[:60]} practice")
            agent = QuizAgent(
                search_service=search_service,
                llm=create_chat_model(task=GENERATION, temperature=0.5),
            )
            await agent.generate_and_save(
                project_id=project_id, topic=topic, quiz_id=quiz.id, count=count,
                custom_instructions=extra,
            )
            with self._get_db_session() as db:
                total = db.query(QuizQuestion).filter(QuizQuestion.quiz_id == quiz.id).count()
            return self.get_quiz(quiz_id=quiz.id, project_id=project_id), total, "ai"

        # Per SLO: suitable bank questions first, then how many the AI must write
        plan = []
        with self._get_db_session() as db:
            for code, share in zip(codes, options.split(count, len(codes))):
                if share == 0:
                    continue
                bank = [
                    item
                    for item in usable_items(db, grade_subject_id, code, "mcq")
                    if options.bank_fits(item.payload, style, level)
                ][:share]
                plan.append(
                    (
                        code,
                        [dict(item.payload) for item in bank],
                        all(item.review_status == "approved" for item in bank),
                        share - len(bank),
                        load_slo(db, code, grade_subject_id=grade_subject_id),
                    )
                )

        llm = create_chat_model(task=GENERATION, temperature=0.5)

        async def written(slo, missing: int) -> list[dict]:
            # Small batches in parallel: one call for many worked numericals is slow
            if missing <= 0 or slo is None:
                return []
            batches = options.split(missing, -(-missing // options.BATCH))
            results = await asyncio.gather(
                *(
                    generate_mcqs(
                        llm, slo, size,
                        difficulty=options.difficulty(level),
                        language_code=language_code,
                        instructions=extra + options.batch_note(number, len(batches)),
                    )
                    for number, size in enumerate(batches, start=1)
                ),
                return_exceptions=True,
            )
            questions = [q for batch in results if isinstance(batch, list) for q in batch]
            if not questions and results and isinstance(results[0], Exception):
                raise results[0]
            return questions

        generated = await asyncio.gather(
            *(written(slo, missing) for _, _, _, missing, slo in plan), return_exceptions=True
        )
        questions: list[tuple[str, dict]] = []
        for (code, bank, _, _, _), ai in zip(plan, generated):
            questions += [(code, q) for q in bank]
            questions += [(code, q) for q in ai] if isinstance(ai, list) else []
        if not questions:
            failure = next((g for g in generated if isinstance(g, Exception)), None)
            raise ValueError(f"No questions could be made for {topic}") from failure

        from_bank = sum(len(bank) for _, bank, _, _, _ in plan)
        source = "bank" if from_bank == len(questions) else "ai" if from_bank == 0 else "mixed"
        label = options.STYLE_NAMES[style]
        name = (
            f"SLO {codes[0]}: {label}"
            if len(codes) == 1
            else f"{topic[:1].upper()}{topic[1:50]}: {label}"
        )
        reviewed = source == "bank" and all(ok for _, _, ok, _, _ in plan)
        quiz = self.create_quiz(project_id=project_id, name=name)
        fields = (
            "question_text", "option_a", "option_b", "option_c", "option_d",
            "correct_option", "explanation",
        )
        with self._get_db_session() as db:
            row = db.query(Quiz).filter(Quiz.id == quiz.id).one()
            row.slo_code = codes[0]
            row.description = (
                "Questions checked by a subject teacher"
                if reviewed
                else f"Practice for SLO {', '.join(codes)}"
            )
            for position, (code, question) in enumerate(questions):
                db.add(
                    QuizQuestion(
                        id=str(uuid4()),
                        quiz_id=quiz.id,
                        project_id=project_id,
                        **{field: question.get(field) for field in fields},
                        difficulty_level=question.get("difficulty_level") or "medium",
                        cognitive_level=question.get("cognitive_level"),
                        slo_code=code,
                        position=position,
                        created_at=datetime.now(),
                    )
                )
            db.commit()
        return self.get_quiz(quiz_id=quiz.id, project_id=project_id), len(questions), source

    def _set_slo_code(self, quiz_id: str, slo_code: str) -> QuizDto:
        """Tag the quiz with its SLO as soon as generation is queued."""
        with self._get_db_session() as db:
            quiz = db.query(Quiz).filter(Quiz.id == quiz_id).one()
            quiz.slo_code = slo_code
            db.commit()
            db.refresh(quiz)
            return self._model_to_dto(quiz)

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
