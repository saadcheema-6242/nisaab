import logging
from contextlib import contextmanager
from datetime import datetime
from uuid import uuid4

from edu_ai.agents.utils import generate
from edu_ai.llm import create_chat_model, is_llm_configured
from edu_db.models import (
    CurriculumDomain,
    PracticeRecord,
    Project,
    Slo,
    StudentProfile,
    StudyPlan,
)
from edu_db.session import get_session_factory
from pydantic import BaseModel, Field

from edu_core import study_plan_blueprint as blueprint
from edu_core.exceptions import NotFoundError
from edu_core.schemas.study_plan_generation import StudyPlanContent, StudyPlanItem
from edu_core.schemas.study_plans import StudyPlanDto

logger = logging.getLogger(__name__)


class PlannedStep(BaseModel):
    """How one sitting is described to the student."""

    title: str = Field(
        description=(
            "One line naming the real content, not the outcome code: "
            '"Work through projectile questions where the angle is given", '
            'not "Practise P-11-B-07". Under about 90 characters.'
        )
    )
    tasks: list[str] = Field(
        description=(
            "Two to four concrete things to do in this sitting, each naming "
            "real content and a quantity where one makes sense: 'Attempt 8 "
            "MCQs on inclined planes', 'Write out the derivation of range "
            "twice from memory'. Never 'practise questions' or 'revise the "
            "topic' - a student cannot act on those."
        )
    )


class PlanWords(BaseModel):
    """What the model is asked for: wording, never the schedule itself."""

    analysis: str = Field(
        description=(
            "Two or three sentences on where the student stands, from the "
            "numbers given. Do not invent figures."
        )
    )
    day_themes: list[str] = Field(
        description=(
            "What each day is about, in order from day one: a short name like "
            "'Resolving forces on a slope'. One per day, same number as days."
        )
    )
    steps: list[PlannedStep] = Field(
        description=(
            "One entry per planned step, in the same order as the steps given, "
            "and the same number of them."
        )
    )
    encouragement: str = Field(description="One or two encouraging sentences.")


class StudyPlanService:
    """Service for managing personalized study plans."""

    def __init__(
        self,
        azure_openai_chat_deployment: str | None = None,
        azure_openai_endpoint: str | None = None,
        azure_openai_api_version: str | None = None,
        azure_ad_token_provider=None,
    ) -> None:
        """Initialize the study plan service.

        Args:
            azure_openai_chat_deployment: Azure OpenAI chat deployment name
            azure_openai_endpoint: Azure OpenAI endpoint URL
            azure_openai_api_version: Azure OpenAI API version
            azure_ad_token_provider: Token provider for Azure AD auth
        """
        self.llm = None
        if is_llm_configured(azure_endpoint=azure_openai_endpoint):
            self.llm = create_chat_model(
                temperature=0.7,
                azure_deployment=azure_openai_chat_deployment,
                azure_endpoint=azure_openai_endpoint,
                azure_api_version=azure_openai_api_version,
            )

    def get_latest_study_plan(self, user_id: str, project_id: str) -> StudyPlanDto | None:
        """Get the latest study plan for a user in a project.

        Args:
            user_id: The user ID
            project_id: The project ID

        Returns:
            Latest StudyPlanDto or None if no plan exists
        """
        with self._get_db_session() as db:
            plan = (
                db.query(StudyPlan)
                .filter(StudyPlan.user_id == user_id, StudyPlan.project_id == project_id)
                .order_by(StudyPlan.created_at.desc())
                .first()
            )
            
            if not plan:
                return None
            
            return self._model_to_dto(plan)
            
    def list_study_plans(self, user_id: str, project_id: str) -> list[StudyPlanDto]:
        """List all study plans for a user in a project.

        Args:
            user_id: The user ID
            project_id: The project ID

        Returns:
            List of StudyPlanDto
        """
        with self._get_db_session() as db:
            plans = (
                db.query(StudyPlan)
                .filter(StudyPlan.user_id == user_id, StudyPlan.project_id == project_id)
                .order_by(StudyPlan.created_at.desc())
                .all()
            )
            return [self._model_to_dto(p) for p in plans]

    async def generate_study_plan(
        self,
        user_id: str,
        project_id: str,
        topic: str | None = None,
        days: int | None = None,
        hours_per_day: float | None = None,
        specifications: str | None = None,
        mode: str | None = None,
    ) -> StudyPlanDto:
        """Build a study plan and save it.

        Args:
            user_id: The student.
            project_id: Their subject workspace.
            topic: What to plan around - a domain ("Dynamics"), a topic
                ("projectile motion") or an outcome code.
            days: How long the plan runs for.
            hours_per_day: How long they can study each day.
            specifications: Anything else the student said about how they
                study - "only at weekends", "school until 2pm", "exams in
                three weeks". Shapes the wording, never the arithmetic.
            mode: "topic" to teach the named topic, "weak" to cover everything
                their practice says they are weak at. Defaults to whichever
                the arguments imply.

        The two modes are kept apart deliberately. A topic plan never reads the
        student's practice records, so it cannot open with "there are no
        practice records on file" - a true statement, and not an answer to a
        student who asked for a plan on data science.

        The arithmetic - which outcomes, how long each, which day - is decided
        in edu_core.study_plan_blueprint. The model is asked only to phrase it,
        because a model left to choose its own allocation writes a plan that
        reads well and does not add up.

        Raises:
            NotFoundError: If the project is not an FBISE subject workspace.
        """
        asked = (mode or "").strip().lower()
        if asked.startswith("weak"):
            plan_mode = blueprint.WEAK
        elif asked.startswith("topic"):
            plan_mode = blueprint.TOPIC if (topic or "").strip() else blueprint.WEAK
        else:
            # Nothing said: a named topic means they want that topic.
            plan_mode = blueprint.TOPIC if (topic or "").strip() else blueprint.WEAK

        with self._get_db_session() as db:
            project = db.query(Project).filter(Project.id == project_id).first()
            if project is None:
                raise NotFoundError(f"Project {project_id} not found")
            language_code = project.language_code or "en"
            exam_year = self._exam_year(db, user_id)

            syllabus, scope = self._syllabus(
                db, project, topic if plan_mode == blueprint.TOPIC else None
            )
            # A topic plan is not asked about the student's record and is not
            # told it. A weak-topics plan is nothing but their record.
            records = (
                []
                if plan_mode == blueprint.TOPIC
                else [
                    {"slo_code": record.slo_code, "was_correct": record.was_correct}
                    for record in db.query(PracticeRecord).filter(
                        PracticeRecord.user_id == user_id,
                        PracticeRecord.project_id == project_id,
                    )
                ]
            )

        plan = blueprint.build(
            syllabus=syllabus,
            records=records,
            days=days,
            hours_per_day=hours_per_day,
            mode=plan_mode,
            scope=scope,
        )

        described = {slo["code"]: slo.get("description", "") for slo in syllabus}
        content = await self._phrase(
            plan, described, language_code, project_id, specifications, exam_year
        )

        with self._get_db_session() as db:
            study_plan = StudyPlan(
                id=str(uuid4()),
                user_id=user_id,
                project_id=project_id,
                content=content.model_dump(),
                weak_topics=plan.weak_codes,
                created_at=datetime.now(),
            )
            db.add(study_plan)
            db.commit()
            db.refresh(study_plan)
            return self._model_to_dto(study_plan)

    @staticmethod
    def _syllabus(db, project, topic: str | None) -> tuple[list[dict], str]:
        """The outcomes a plan may draw on, and what to call that scope.

        A named topic narrows the plan to a domain where the name matches one,
        otherwise to whatever the syllabus search ranks against it, widened to
        the whole content area each match sits in. The widening matters: the
        search demands a match on most of the query, so "data science" found
        one outcome out of the syllabus and the plan that came back was three
        steps long whatever period the student asked for. A topic is a chapter
        of work, not a single line of it, so the plan covers the chapter.

        A topic that matches nothing falls back to the whole syllabus rather
        than producing an empty plan - a student who mistypes a chapter name is
        better served by a general plan than by nothing at all.
        """
        if not project.grade_subject_id:
            raise NotFoundError(
                "Study plans are available in FBISE subject workspaces"
            )
        rows = (
            db.query(Slo, CurriculumDomain)
            .join(CurriculumDomain, Slo.domain_id == CurriculumDomain.id)
            .filter(
                Slo.grade_subject_id == project.grade_subject_id,
                Slo.assessment_form == "summative",
            )
            .order_by(CurriculumDomain.sort_order, Slo.sort_order)
            .all()
        )
        if not rows:
            raise NotFoundError("This subject's syllabus map is not available yet")

        everything = [
            {
                "code": slo.code,
                "description": slo.description,
                "domain": domain.name,
                "area": slo.content_area or "",
            }
            for slo, domain in rows
        ]
        wanted = (topic or "").strip()
        if not wanted or wanted.lower() in ("whole syllabus", "all", "everything"):
            return everything, "whole syllabus"

        lowered = wanted.lower()
        named = [
            slo
            for slo in everything
            if slo["domain"].lower() in lowered or lowered in slo["domain"].lower()
        ]
        if named:
            return named, named[0]["domain"]

        from edu_ai.tools.syllabus import search_slos

        codes = {
            match["code"]
            for match in search_slos(project.grade_subject_id, wanted, limit=12)
        }
        # Everything the search found, plus the rest of the content areas those
        # outcomes belong to. The search is built to pinpoint one outcome for a
        # citation; a plan needs the chapter around it.
        areas = {
            slo["area"] for slo in everything if slo["code"] in codes and slo["area"]
        }
        matched = [
            slo
            for slo in everything
            if slo["code"] in codes or (slo["area"] and slo["area"] in areas)
        ]
        if matched:
            return matched, wanted
        return everything, "whole syllabus"

    async def _phrase(
        self,
        plan: blueprint.Plan,
        described: dict[str, str],
        language_code: str,
        project_id: str,
        specifications: str | None = None,
        exam_year: int | None = None,
    ) -> StudyPlanContent:
        """Put the plan into words the student will read.

        The schedule is already decided. If the model is unavailable or its
        answer does not line up, the plan is still returned with every step
        described plainly - a plan without a pep talk is worth far more than
        no plan.
        """
        items = [
            StudyPlanItem(
                day=item.day,
                slo_code=item.slo_code,
                action=item.action,
                title=self._plain_title(item, described.get(item.slo_code, "")),
                minutes=item.minutes,
                target=item.target,
                domain=item.domain,
                standing=item.standing,
                pass_index=item.pass_index,
            )
            for item in plan.items
        ]
        day_count = max((item.day for item in plan.items), default=0)
        focus = list(dict.fromkeys(item.slo_code for item in plan.items))
        plain = StudyPlanContent(
            analysis=blueprint.summarise(plan),
            focus_areas=focus,
            items=items,
            day_themes=[],
            encouragement="",
        )
        if not self.llm or not items:
            return plain

        lines = []
        for item in plan.items:
            target = f" - {item.target}" if item.target else ""
            said = described.get(item.slo_code, "")[:110]
            # Which sweep this is, so the wording can tell learning it the
            # first time apart from coming back to it a fortnight later.
            sweep = "first time" if item.pass_index == 0 else f"revisit {item.pass_index}"
            lines.append(
                f"Day {item.day}: {item.slo_code} - {item.action} "
                f"({item.minutes} min, {sweep}){target} [{said}]"
            )

        try:
            written = await generate(
                llm=self.llm,
                search_service=None,
                output_model=PlanWords,
                prompt_template="study_plan",
                project_id=project_id,
                topic=plan.scope,
                language_code=language_code,
                document_content=blueprint.summarise(plan),
                plan_lines="\n".join(lines),
                day_count=day_count,
                specifications=(specifications or "").strip(),
                exam_note=self._exam_note(exam_year),
                mode=plan.mode,
            )
        except Exception:  # noqa: BLE001 - the schedule is the valuable part
            logger.warning("Could not phrase the study plan; using plain wording")
            return plain

        # Wording comes back in order; anything missing keeps its plain form.
        for item, step in zip(items, written.steps or []):
            if step.title and step.title.strip():
                item.title = step.title.strip()
            item.tasks = [t.strip() for t in (step.tasks or []) if t and t.strip()]
        return StudyPlanContent(
            analysis=written.analysis or plain.analysis,
            focus_areas=focus,
            items=items,
            day_themes=[t.strip() for t in (written.day_themes or []) if t.strip()],
            encouragement=written.encouragement or "",
        )

    @staticmethod
    def _exam_year(db, user_id: str) -> int | None:
        """The year the student sits the board exam, if they said."""
        profile = (
            db.query(StudentProfile)
            .filter(StudentProfile.user_id == user_id)
            .first()
        )
        return getattr(profile, "exam_year", None) if profile else None

    @staticmethod
    def _exam_note(exam_year: int | None) -> str:
        """How close the board exam is, as a fact for the model to plan around.

        A plan written three weeks before the paper should look nothing like
        one written in August. The model cannot know which it is, so it is
        told rather than left to guess from the date.
        """
        if not exam_year:
            return ""
        # FBISE sits the annual HSSC papers in the second quarter
        exam_month = datetime(int(exam_year), 5, 1)
        months = (exam_month.year - datetime.now().year) * 12 + (
            exam_month.month - datetime.now().month
        )
        if months < 0:
            return ""
        if months <= 1:
            return (
                "The board exam is within about a month. This is revision: "
                "past papers, timed practice and the outcomes they still lose "
                "marks on. Do not start anything new."
            )
        if months <= 3:
            return (
                f"The board exam is about {months} months away. Mix revision "
                "with finishing the syllabus, and start timed practice."
            )
        return (
            f"The board exam is about {months} months away. There is time to "
            "build understanding properly before revision starts."
        )

    @staticmethod
    def _plain_title(item, description: str) -> str:
        """A readable line for one step, without asking a model for it."""
        said = (description or item.slo_code).strip()
        if len(said) > 90:
            said = said[:87].rstrip() + "..."
        first = {
            "read": f"Read through {said}",
            "flashcards": f"Run the flashcards on {said}",
            "quiz": f"Attempt a quiz on {said}",
            "srq": f"Answer a short question on {said}",
            "paper": f"Sit a practice paper covering {said}",
        }
        # A revisit is not the same sitting again. Even with no model to phrase
        # it, the wording has to say which of the two a student is looking at,
        # or a month-long plan reads as one week printed four times.
        again = {
            "read": f"Read {said} again, this time without notes",
            "flashcards": f"Clear the flashcards on {said} from memory",
            "quiz": f"Retest yourself on {said}",
            "srq": f"Write a full short answer on {said}, timed",
            "paper": f"Sit a timed paper covering {said}",
        }
        verbs = again if getattr(item, "pass_index", 0) else first
        return verbs.get(item.action, said)

    def _model_to_dto(self, plan: StudyPlan) -> StudyPlanDto:
        """Convert StudyPlan model to DTO."""
        # Ensure content is a dict/object for the DTO
        content = plan.content
        # If for some reason it's still a string (old records), we might want to handle it, 
        # but for now assume schema migration handles it or new records only.
        # Actually sqlalchemy JSON type returns python dicts.
        
        return StudyPlanDto(
            id=plan.id,
            user_id=plan.user_id,
            project_id=plan.project_id,
            content=content, 
            weak_topics=plan.weak_topics,
            created_at=plan.created_at,
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
