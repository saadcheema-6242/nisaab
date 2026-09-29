"""CRUD service for managing mind maps."""

from contextlib import contextmanager
from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from edu_db.models import MindMap
from edu_db.session import get_session_factory

from edu_core.exceptions import NotFoundError
from edu_core.schemas.mind_maps import MindMapDto

if TYPE_CHECKING:
    from edu_queue.service import QueueService


class MindMapService:
    """Service for managing mind maps."""

    def __init__(self, queue_service: "QueueService") -> None:
        """Initialize the mind map service.

        Args:
            queue_service: QueueService instance for async generation tasks
        """
        self.queue_service = queue_service

    def create_mind_map(
        self,
        user_id: str,
        project_id: str,
        title: str,
        description: str | None = None,
        map_data: dict[str, Any] | None = None,
    ) -> MindMapDto:
        """Create a new mind map.

        Args:
            user_id: The user ID
            project_id: The project ID
            title: The mind map title
            description: Optional description
            map_data: Optional map data (nodes, edges)

        Returns:
            Created MindMapDto
        """
        with self._get_db_session() as db:
            try:
                mind_map = MindMap(
                    id=str(uuid4()),
                    user_id=user_id,
                    project_id=project_id,
                    title=title,
                    description=description,
                    map_data=map_data or {"nodes": [], "edges": []},
                    generated_at=datetime.now(),
                    updated_at=datetime.now(),
                )
                db.add(mind_map)
                db.commit()
                db.refresh(mind_map)

                return self._model_to_dto(mind_map)
            except Exception:
                db.rollback()
                raise

    def get_mind_map(
        self, mind_map_id: str, project_id: str, user_id: str
    ) -> MindMapDto:
        """Get a mind map by ID.

        Args:
            mind_map_id: The mind map ID
            project_id: The project ID
            user_id: The user ID

        Returns:
            MindMapDto

        Raises:
            NotFoundError: If mind map not found
        """
        with self._get_db_session() as db:
            try:
                mind_map = (
                    db.query(MindMap)
                    .filter(
                        MindMap.id == mind_map_id,
                        MindMap.project_id == project_id,
                        MindMap.user_id == user_id,
                    )
                    .first()
                )
                if not mind_map:
                    raise NotFoundError(f"Mind map {mind_map_id} not found")

                return self._model_to_dto(mind_map)
            except NotFoundError:
                raise
            except Exception:
                raise

    def delete_mind_map(self, mind_map_id: str, project_id: str, user_id: str) -> None:
        """Delete a mind map.

        Raises:
            NotFoundError: If mind map not found
        """
        with self._get_db_session() as db:
            mind_map = (
                db.query(MindMap)
                .filter(
                    MindMap.id == mind_map_id,
                    MindMap.project_id == project_id,
                    MindMap.user_id == user_id,
                )
                .first()
            )
            if not mind_map:
                raise NotFoundError(f"Mind map {mind_map_id} not found")
            db.delete(mind_map)
            db.commit()

    def list_mind_maps(self, project_id: str, user_id: str) -> list[MindMapDto]:
        """List all mind maps for a project.

        Args:
            project_id: The project ID
            user_id: The user ID

        Returns:
            List of MindMapDto instances
        """
        with self._get_db_session() as db:
            try:
                mind_maps = (
                    db.query(MindMap)
                    .filter(
                        MindMap.project_id == project_id,
                        MindMap.user_id == user_id,
                    )
                    .order_by(MindMap.generated_at.desc())
                    .all()
                )
                return [self._model_to_dto(m) for m in mind_maps]
            except Exception:
                raise

    def _model_to_dto(self, mind_map: MindMap) -> MindMapDto:
        """Convert MindMap model to MindMapDto."""
        return MindMapDto(
            id=mind_map.id,
            user_id=mind_map.user_id,
            project_id=mind_map.project_id,
            title=mind_map.title,
            description=mind_map.description,
            map_data=mind_map.map_data,
            generated_at=mind_map.generated_at,
            updated_at=mind_map.updated_at,
        )

    def queue_generation(
        self,
        user_id: str,
        project_id: str,
        mind_map_id: str | None = None,
        topic: str | None = None,
        custom_instructions: str | None = None,
    ) -> MindMapDto:
        """Queue a mind map generation request to be processed by a worker.

        Args:
            user_id: The user ID
            project_id: The project ID
            queue_service: QueueService instance to send the message
            mind_map_id: Optional existing mind map ID to populate (if None, creates new)
            topic: Optional topic for generation
            custom_instructions: Optional custom instructions

        Returns:
            Existing or newly created MindMapDto (generation will happen asynchronously)

        Raises:
            NotFoundError: If mind_map_id is provided but mind map not found
        """
        from edu_queue.schemas import MindMapGenerationData, QueueTaskMessage, TaskType

        # If mind_map_id is provided, verify it exists
        if mind_map_id:
            mind_map = self.get_mind_map(
                mind_map_id=mind_map_id,
                project_id=project_id,
                user_id=user_id,
            )
        else:
            # Create a new empty mind map
            mind_map = self.create_mind_map(
                user_id=user_id,
                project_id=project_id,
                title="Generating...",
                description="Mind map is being generated",
                map_data={"nodes": [], "edges": []},
            )
            mind_map_id = mind_map.id

        # Prepare task data
        task_data: MindMapGenerationData = {
            "project_id": project_id,
            "user_id": user_id,
            "mind_map_id": mind_map_id,
        }
        if topic:
            task_data["topic"] = topic
        if custom_instructions:
            task_data["custom_instructions"] = custom_instructions

        # Send message to queue
        task_message: QueueTaskMessage = {
            "type": TaskType.MIND_MAP_GENERATION,
            "data": task_data,
        }
        self.queue_service.send_message(task_message)

        return mind_map

    async def create_practice_mind_map(
        self,
        user_id: str,
        project_id: str,
        topic: str,
        search_service=None,
        slo_codes: list[str] | None = None,
        detail: str = "standard",
        include: list[str] | None = None,
        notes: str | None = None,
    ) -> MindMapDto:
        """Make a mind map to show right away (e.g. inside the chat).

        slo_codes (the SLOs the student chose), detail ("quick", "standard" or
        "detailed") and include (e.g. formulas, derivations, exam tips) shape the
        AI-written topic maps.

        In a subject workspace the structure comes from the FBISE syllabus: a domain
        name gives domain → topics → SLOs (instant, no AI); another topic gives one
        branch per matching SLO with AI-written key points. Other topics fall back
        to a general AI mind map.
        """
        from edu_ai.agents.mind_map_agent import MindMapAgent
        from edu_ai.agents.slo_mind_map import domain_map, topic_map
        from edu_ai.llm import GENERATION, create_chat_model
        from edu_ai.tools.syllabus import resolve_slos, search_slos
        from edu_db.models import CurriculumDomain, GradeSubject, Project, Slo

        with self._get_db_session() as db:
            project = db.get(Project, project_id)
            if project is None:
                raise NotFoundError(f"Project {project_id} not found")
            language_code = project.language_code
            grade_subject = db.get(GradeSubject, project.grade_subject_id) if project.grade_subject_id else None
            subject = grade_subject.subject.name if grade_subject else ""
            grade = grade_subject.grade if grade_subject else 0
            domains = (
                db.query(CurriculumDomain)
                .filter(CurriculumDomain.grade_subject_id == grade_subject.id)
                .order_by(CurriculumDomain.sort_order)
                .all()
                if grade_subject
                else []
            )
            wanted = topic.strip().lower()
            domain = next(
                (d for d in domains if d.name.lower() in wanted or wanted in d.name.lower()), None
            )
            domain_slos = []
            if domain is not None:
                domain_slos = [
                    {
                        "code": slo.code,
                        "description": slo.description,
                        "content_area": slo.content_area,
                        "assessment_form": slo.assessment_form,
                    }
                    for slo in db.query(Slo)
                    .filter(Slo.domain_id == domain.id)
                    .order_by(Slo.sort_order)
                ]
            domain_info = {"code": domain.code, "name": domain.name} if domain else None
            all_slos = (
                [
                    {
                        "code": slo.code,
                        "description": slo.description,
                        "content_area": slo.content_area,
                        "assessment_form": slo.assessment_form,
                    }
                    for slo in db.query(Slo)
                    .filter(Slo.grade_subject_id == grade_subject.id)
                    .order_by(Slo.sort_order)
                ]
                if grade_subject and domain is None
                else []
            )

        if domain_info and domain_slos and not slo_codes:
            title, description, map_data = domain_map(subject, grade, domain_info, domain_slos)
            return self.create_mind_map(
                user_id=user_id, project_id=project_id, title=title,
                description=description, map_data=map_data,
            )

        # The SLOs the student chose, else the best matches for the topic
        picked = resolve_slos(grade_subject.id, topic, slo_codes) if grade_subject and slo_codes else []
        matches = search_slos(grade_subject.id, topic, limit=4) if grade_subject and not picked else []
        if picked:
            if not all_slos:  # the topic named a domain, so the SLO list was not loaded above
                with self._get_db_session() as db:
                    all_slos = [
                        {
                            "code": slo.code,
                            "description": slo.description,
                            "content_area": slo.content_area,
                            "assessment_form": slo.assessment_form,
                        }
                        for slo in db.query(Slo)
                        .filter(Slo.grade_subject_id == grade_subject.id)
                        .order_by(Slo.sort_order)
                    ]
            slos = [s for s in all_slos if s["code"] in picked]
            title, description, map_data = await topic_map(
                create_chat_model(task=GENERATION, temperature=0.4),
                topic, subject, grade, slos, language_code,
                detail=detail, include=include, notes=notes,
            )
            return self.create_mind_map(
                user_id=user_id, project_id=project_id, title=title,
                description=description, map_data=map_data,
            )
        if matches:
            chosen = [m["code"] for m in matches]
            # Fill thin maps with the other SLOs of the best match's topic
            area = matches[0]["content_area"]
            for slo in all_slos:
                if len(chosen) >= 4:
                    break
                if slo["content_area"] == area and slo["code"] not in chosen:
                    chosen.append(slo["code"])
            slos = [s for s in all_slos if s["code"] in chosen]
            title, description, map_data = await topic_map(
                create_chat_model(task=GENERATION, temperature=0.4),
                topic, subject, grade, slos, language_code,
                detail=detail, include=include, notes=notes,
            )
            return self.create_mind_map(
                user_id=user_id, project_id=project_id, title=title,
                description=description, map_data=map_data,
            )

        mind_map = self.create_mind_map(
            user_id=user_id, project_id=project_id, title=topic[:80], map_data={"nodes": [], "edges": []}
        )
        agent = MindMapAgent(
            search_service=search_service,
            llm=create_chat_model(task=GENERATION, temperature=0.4),
        )
        await agent.generate_and_save(
            project_id=project_id, topic=topic, mind_map_id=mind_map.id, user_id=user_id
        )
        return self.get_mind_map(mind_map_id=mind_map.id, project_id=project_id, user_id=user_id)

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
