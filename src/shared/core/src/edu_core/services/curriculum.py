"""Read service for the FBISE curriculum (grade subjects, domains, SLOs)."""

from contextlib import contextmanager

from edu_db.models import CurriculumDomain, GradeSubject, Slo, Subject
from edu_db.session import get_session_factory
from sqlalchemy import func
from sqlalchemy.orm import joinedload, selectinload

from edu_core.exceptions import NotFoundError
from edu_core.mastery import slo_mastery
from edu_core.schemas.curriculum import (
    CurriculumTreeDto,
    DomainDto,
    GradeSubjectDto,
    SloDto,
)


class CurriculumService:
    """Service for reading the FBISE curriculum."""

    def list_grade_subjects(self, grade: int | None = None) -> list[GradeSubjectDto]:
        """List grade subjects, optionally for one grade."""
        with self._get_db_session() as db:
            query = db.query(GradeSubject).join(Subject).options(
                joinedload(GradeSubject.subject)
            )
            if grade is not None:
                query = query.filter(GradeSubject.grade == grade)
            grade_subjects = query.order_by(GradeSubject.grade, Subject.sort_order).all()
            counts = dict(
                db.query(Slo.grade_subject_id, func.count(Slo.id))
                .group_by(Slo.grade_subject_id)
                .all()
            )
            return [
                self._grade_subject_to_dto(gs, counts.get(gs.id, 0))
                for gs in grade_subjects
            ]

    def get_tree(self, grade_subject_id: str, user_id: str) -> CurriculumTreeDto:
        """Get domains and SLOs of a grade subject with the user's mastery.

        Raises:
            NotFoundError: If the grade subject does not exist
        """
        with self._get_db_session() as db:
            grade_subject = (
                db.query(GradeSubject)
                .options(
                    joinedload(GradeSubject.subject),
                    selectinload(GradeSubject.domains).selectinload(CurriculumDomain.slos),
                )
                .filter(GradeSubject.id == grade_subject_id)
                .first()
            )
            if not grade_subject:
                raise NotFoundError(f"Grade subject {grade_subject_id} not found")

            all_slos = [slo for domain in grade_subject.domains for slo in domain.slos]
            progress = slo_mastery(db, user_id, (slo.code for slo in all_slos))

            domains = []
            for domain in grade_subject.domains:
                slos = [
                    self._slo_to_dto(slo, domain, progress.get(slo.code))
                    for slo in domain.slos
                ]
                practised = [s.mastery for s in slos if s.mastery is not None]
                domains.append(
                    DomainDto(
                        code=domain.code,
                        name=domain.name,
                        slo_count=len(slos),
                        examined_count=sum(
                            1 for s in slos if s.assessment_form == "summative"
                        ),
                        mastery=round(sum(practised) / len(practised), 3)
                        if practised
                        else None,
                        slos=slos,
                    )
                )

            return CurriculumTreeDto(
                grade_subject=self._grade_subject_to_dto(grade_subject, len(all_slos)),
                domains=domains,
            )

    def get_slo(
        self, code: str, user_id: str, grade_subject_id: str | None = None
    ) -> SloDto:
        """Get one SLO by its FBISE code.

        Raises:
            NotFoundError: If no SLO has this code
        """
        with self._get_db_session() as db:
            query = (
                db.query(Slo)
                .options(joinedload(Slo.domain))
                .filter(func.upper(Slo.code) == code.strip().upper())
            )
            if grade_subject_id:
                query = query.filter(Slo.grade_subject_id == grade_subject_id)
            slo = query.first()
            if not slo:
                raise NotFoundError(f"SLO {code} not found")
            progress = slo_mastery(db, user_id, [slo.code])
            return self._slo_to_dto(slo, slo.domain, progress.get(slo.code))

    @staticmethod
    def _grade_subject_to_dto(grade_subject: GradeSubject, slo_count: int) -> GradeSubjectDto:
        return GradeSubjectDto(
            id=grade_subject.id,
            subject_code=grade_subject.subject.code,
            subject_name=grade_subject.subject.name,
            grade=grade_subject.grade,
            scheme=grade_subject.scheme,
            curriculum=grade_subject.curriculum,
            source_url=grade_subject.source_url,
            status=grade_subject.status,
            slo_count=slo_count,
        )

    @staticmethod
    def _slo_to_dto(
        slo: Slo,
        domain: CurriculumDomain,
        progress: tuple[int, float | None] | None,
    ) -> SloDto:
        attempts, mastery = progress or (0, None)
        return SloDto(
            id=slo.id,
            code=slo.code,
            grade_subject_id=slo.grade_subject_id,
            domain_code=domain.code,
            domain_name=domain.name,
            content_area=slo.content_area,
            description=slo.description,
            assessment_form=slo.assessment_form,
            cognitive_levels=slo.cognitive_levels or [],
            periods=slo.periods,
            attempts=attempts,
            mastery=mastery,
        )

    @contextmanager
    def _get_db_session(self):
        """Context manager for database sessions."""
        SessionLocal = get_session_factory()
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()
