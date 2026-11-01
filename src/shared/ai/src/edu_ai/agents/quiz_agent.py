from datetime import datetime
from typing import Any
from uuid import uuid4

from edu_core.openly_licensed import fetch, search
from edu_core.paper_blueprint import distinct_by_text
from edu_core.services.quizzes import clamp_count
from edu_core.exceptions import NotFoundError
from edu_db.models import Project, Quiz, QuizQuestion
from langchain_openai import AzureChatOpenAI
from pydantic import BaseModel, Field

from edu_ai.agents.slo_context import language_name, load_slo
from edu_ai.agents.topic_graph_agent import TopicGraphAgent
from edu_ai.agents.utils import generate, get_db_session


class QuizQuestionGenerationResult(BaseModel):
    """Pydantic model for quiz question data structure."""

    question_text: str = Field(..., description="The quiz question text")
    option_a: str = Field(..., description="Option A")
    option_b: str = Field(..., description="Option B")
    option_c: str = Field(..., description="Option C")
    option_d: str = Field(..., description="Option D")
    correct_option: str = Field(..., description="Correct option: a, b, c, or d")
    explanation: str = Field(..., description="Explanation for the correct answer")
    difficulty_level: str = Field(
        ..., description="Difficulty level: easy, medium, or hard"
    )
    cognitive_level: str | None = Field(
        None, description="Cognitive level: K (knowledge), U (understanding) or A (application)"
    )
    option_diagrams: dict | None = Field(
        None,
        description=(
            "Only when the options themselves are pictures to choose between. "
            "An object keyed by option letter, each value a search for a real "
            'diagram: {"a":{"query":"benzene structural formula"},'
            '"b":{"query":"cyclopentane structural formula"}}. If the picture '
            "belongs to the question rather than the choice, put it in diagram "
            "instead - that is the usual case. Never search the same thing for "
            "every option."
        ),
    )
    # Deliberately a plain dict, not a model. It is validated on its own
    # further down, so a search the model gets wrong costs that one picture
    # instead of failing the whole structured output and losing the quiz.
    diagram: dict | None = Field(
        None,
        description=(
            "A diagram for the question, only when it cannot be asked in words "
            'alone: {"query":"animal cell diagram labelled"}. The query is what '
            "the diagram would be titled in an encyclopedia - the thing itself, "
            "in plain English, with no mention of FSc or of the student's "
            "language. "
            "A real, published diagram is searched for, so unlike a generated "
            "picture it does carry correct labels and values and you may refer "
            "to them. If nothing freely licensed is found the question keeps "
            "its text and loses only the picture, so the question must still "
            "make sense on its own: never write 'in the figure' or 'shown "
            "above' unless the question would be unanswerable without it."
        ),
    )


class QuizGenerationResult(BaseModel):
    """Model for quiz generation result."""

    name: str = Field(..., description="The name of the quiz")
    description: str = Field(..., description="The description of the quiz")
    questions: list[QuizQuestionGenerationResult] = Field(
        ..., description="The questions of the quiz"
    )


class QuizAgent:
    output_model = QuizGenerationResult
    prompt_template = "quiz_prompt"

    def __init__(
        self,
        search_service: Any,
        llm: AzureChatOpenAI,
        topic_graph_agent: TopicGraphAgent | None = None,
        storage: Any = None,
    ):
        self.search_service = search_service
        self.llm = llm
        self.topic_graph_agent = topic_graph_agent
        # Without it a question keeps its text and simply loses its diagram
        self.storage = storage

    async def generate_and_save(
        self,
        project_id: str,
        topic: str | None = None,
        custom_instructions: str | None = None,
        quiz_id: str | None = None,
        count: int | None = None,
        slo_code: str | None = None,
        **kwargs: Any,
    ) -> Quiz:
        """Generate quiz questions and save to the database.

        Args:
            project_id: The project ID
            topic: Optional topic for generation
            custom_instructions: Optional custom instructions
            quiz_id: The quiz ID to populate (required)
            count: Optional count of questions to generate
            slo_code: Optional FBISE SLO the questions must assess

        Returns:
            Updated Quiz model

        Raises:
            NotFoundError: If quiz or project not found
            ValueError: If quiz_id is not provided
        """
        if not quiz_id:
            raise ValueError("quiz_id is required for quiz generation")

        with get_db_session() as db:
            # Find existing quiz
            quiz = (
                db.query(Quiz)
                .filter(
                    Quiz.id == quiz_id,
                    Quiz.project_id == project_id,
                )
                .first()
            )
            if not quiz:
                raise NotFoundError(f"Quiz {quiz_id} not found")

            # Get project language code
            project = db.query(Project).filter(Project.id == project_id).first()
            if not project:
                raise NotFoundError(f"Project {project_id} not found")
            language_code = project.language_code

            # SLO mode: the SLO text is the topic, so no topic graph is needed
            slo = load_slo(db, slo_code, project) if slo_code else None
            prompt_template = self.prompt_template
            prompt_vars: dict[str, Any] = {}
            if slo:
                prompt_template = "quiz_slo_prompt"
                prompt_vars = {
                    **slo.prompt_vars(),
                    "language_name": language_name(language_code),
                    "difficulty": "mixed",
                }
                count = clamp_count(count)

            generation_topic = slo.description if slo else topic
            if self.topic_graph_agent and not slo:
                topic_graph = await self.topic_graph_agent.generate_topic_graph(
                    project_id=project_id,
                    topic=topic,
                    custom_instructions=custom_instructions,
                )
                if topic_graph.root_topics:
                    topics = []
                    for root_topic in topic_graph.root_topics:
                        topics.append(root_topic.topic)
                        for subtopic in root_topic.subtopics:
                            topics.append(subtopic.topic)
                    generation_topic = ", ".join(topics)

            # Generate quiz using AI
            kwargs = dict(prompt_vars)
            if count is not None:
                kwargs["count"] = count

            result = await generate(
                llm=self.llm,
                search_service=self.search_service,
                output_model=self.output_model,
                prompt_template=prompt_template,
                project_id=project_id,
                topic=generation_topic or "",
                language_code=language_code,
                custom_instructions=custom_instructions,
                **kwargs,
            )

            # Update quiz with generated name and description
            quiz.name = result.name
            quiz.description = result.description
            if slo:
                quiz.slo_code = slo.code
            quiz.updated_at = datetime.now()
            db.flush()

            # Delete existing questions and create new ones
            db.query(QuizQuestion).filter(QuizQuestion.quiz_id == quiz_id).delete()

            # A model asked for twenty questions on one SLO sometimes writes the
            # same one twice with the options shuffled. A shorter quiz is better
            # than one that asks the same thing twice.
            kept = distinct_by_text(result.questions)

            # Save quiz questions
            for position, question_item in enumerate(kept):
                question_id = str(uuid4())
                image_path, image_alt, image_credit = self._diagram(
                    project_id, question_id, question_item.diagram
                )
                option_images = self._option_diagrams(
                    project_id, question_id, question_item.option_diagrams
                )
                quiz_question = QuizQuestion(
                    id=question_id,
                    quiz_id=quiz_id,
                    project_id=project_id,
                    question_text=question_item.question_text,
                    option_a=question_item.option_a,
                    option_b=question_item.option_b,
                    option_c=question_item.option_c,
                    option_d=question_item.option_d,
                    correct_option=question_item.correct_option,
                    explanation=question_item.explanation,
                    difficulty_level=question_item.difficulty_level,
                    slo_code=slo.code if slo else None,
                    cognitive_level=_cognitive_level(question_item.cognitive_level),
                    image_path=image_path,
                    image_alt=image_alt,
                    image_credit=image_credit,
                    option_images=option_images,
                    position=position,
                    created_at=datetime.now(),
                )
                db.add(quiz_question)

            db.flush()
            return quiz


    def _option_diagrams(
        self, project_id: str, question_id: str, specs: dict | None
    ) -> dict | None:
        """Find a diagram for each option that needs one.

        Keyed by option letter, so an option without a picture is simply absent
        and the student sees its text as before.
        """
        if not specs or self.storage is None:
            return None
        drawn: dict[str, dict[str, str]] = {}
        for letter in ("a", "b", "c", "d"):
            spec = specs.get(letter)
            if not spec:
                continue
            path, alt, credit = self._diagram(
                project_id, f"{question_id}-{letter}", spec
            )
            if path:
                drawn[letter] = {
                    "path": path,
                    "alt": alt or "",
                    "credit": credit or {},
                }
        return drawn or None

    def _diagram(
        self, project_id: str, question_id: str, spec: dict | None
    ) -> tuple[str | None, str | None, dict | None]:
        """Find the question's diagram and store it, or carry on without one.

        Returns the stored path, the alt text and the credit that has to be
        shown with it. A picture is the least important part of a question: if
        the search finds nothing freely licensed, or storing fails, the
        question is still worth having, so the failure is logged and the
        question keeps its text.
        """
        if not spec or self.storage is None:
            return None, None, None
        query = (spec.get("query") or spec.get("prompt") or "").strip()
        if not query:
            return None, None, None
        try:
            results = search(query, limit=3)
            if not results:
                print(f"no freely licensed diagram for {question_id}: {query!r}")
                return None, None, None
            best = results[0]
            path = f"{project_id}/media/{question_id}.png"
            self.storage.upload(
                path, fetch(best.image_url), content_type="image/png"
            )
            return path, best.title, best.credit.as_dict()
        except Exception as error:  # noqa: BLE001 - never lose a question over a picture
            print(f"diagram for question {question_id} not found: {error}")
            return None, None, None


def _cognitive_level(value: str | None) -> str | None:
    level = (value or "").strip().upper()[:1]
    return level if level in ("K", "U", "A") else None
