import logging
from contextlib import contextmanager
from datetime import datetime
from uuid import uuid4

from edu_ai.agents.utils import generate
from edu_ai.llm import create_chat_model, is_llm_configured
from edu_db.models import CurriculumDomain, PracticeRecord, Project, Slo, StudyPlan
from edu_db.session import get_session_factory
from pydantic import BaseModel, Field

from edu_core import study_plan_blueprint as blueprint
from edu_core.exceptions import NotFoundError
from edu_core.schemas.study_plan_generation import StudyPlanContent, StudyPlanItem
from edu_core.schemas.study_plans import StudyPlanDto

logger = logging.getLogger(__name__)


class PlanWords(BaseModel):
    """What the model is asked for: wording, never the schedule itself."""

    analysis: str = Field(
        description=(
            "Two or three sentences on where the student stands, from the "
            "numbers given. Do not invent figures."
        )
    )
    titles: list[str] = Field(
        description=(
            "One line per planned step, in the same order as the steps given, "
            "saying what to do. Same number of lines as steps."
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
    ) -> StudyPlanDto:
        """Build a study plan and save it.

        Args:
            user_id: The student.
            project_id: Their subject workspace.
            topic: What to plan around - a domain ("Dynamics"), a topic
                ("projectile motion") or an outcome code. Without one the plan
                covers everything the student is weak at, across the syllabus.
            days: How long the plan runs for.
            hours_per_day: How long they can study each day.

        The arithmetic - which outcomes, how long each, which day - is decided
        in edu_core.study_plan_blueprint from the student's practice records.
        The model is asked only to phrase it, because a model left to choose
        its own allocation writes a plan that reads well and does not add up.

        Raises:
            NotFoundError: If the project is not an FBISE subject workspace.
        """
        with self._get_db_session() as db:
            project = db.query(Project).filter(Project.id == project_id).first()
            if project is None:
                raise NotFoundError(f"Project {project_id} not found")
            language_code = project.language_code or "en"

            syllabus, scope = self._syllabus(db, project, topic)
            records = [
                {"slo_code": record.slo_code, "was_correct": record.was_correct}
                for record in db.query(PracticeRecord).filter(
                    PracticeRecord.user_id == user_id,
                    PracticeRecord.project_id == project_id,
                )
            ]

        plan = blueprint.build(
            syllabus=syllabus,
            records=records,
            days=days,
            hours_per_day=hours_per_day,
            # A plan over the whole syllabus is about weaknesses. A plan on one
            # topic covers that topic whether or not they are weak at it, which
            # is what the student asked for by naming it.
            weak_only=topic is None,
            scope=scope,
        )

        described = {slo["code"]: slo.get("description", "") for slo in syllabus}
        content = await self._phrase(plan, described, language_code, project_id)

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
        otherwise to whatever the syllabus search ranks against it. A topic
        that matches nothing falls back to the whole syllabus rather than
        producing an empty plan - a student who mistypes a chapter name is
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
            {"code": slo.code, "description": slo.description, "domain": domain.name}
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
        matched = [slo for slo in everything if slo["code"] in codes]
        if matched:
            return matched, wanted
        return everything, "whole syllabus"

    async def _phrase(
        self,
        plan: blueprint.Plan,
        described: dict[str, str],
        language_code: str,
        project_id: str,
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
            )
            for item in plan.items
        ]
        focus = list(dict.fromkeys(item.slo_code for item in plan.items))
        plain = StudyPlanContent(
            analysis=blueprint.summarise(plan),
            focus_areas=focus,
            items=items,
            encouragement="",
        )
        if not self.llm or not items:
            return plain

        lines = []
        for item in plan.items:
            target = f" - {item.target}" if item.target else ""
            said = described.get(item.slo_code, "")[:110]
            lines.append(
                f"Day {item.day}: {item.slo_code} - {item.action} "
                f"({item.minutes} min){target} [{said}]"
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
            )
        except Exception:  # noqa: BLE001 - the schedule is the valuable part
            logger.warning("Could not phrase the study plan; using plain wording")
            return plain

        # Titles come back in order; anything missing keeps its plain wording.
        for item, title in zip(items, written.titles or []):
            if title and title.strip():
                item.title = title.strip()
        return StudyPlanContent(
            analysis=written.analysis or plain.analysis,
            focus_areas=focus,
            items=items,
            encouragement=written.encouragement or "",
        )

    @staticmethod
    def _plain_title(item, description: str) -> str:
        """A readable line for one step, without asking a model for it."""
        said = (description or item.slo_code).strip()
        if len(said) > 90:
            said = said[:87].rstrip() + "..."
        verbs = {
            "read": f"Read through {said}",
            "flashcards": f"Run the flashcards on {said}",
            "quiz": f"Attempt a quiz on {said}",
            "srq": f"Answer a short question on {said}",
            "paper": f"Sit a practice paper covering {said}",
        }
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
