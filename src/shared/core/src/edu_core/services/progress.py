"""Student progress per subject: mastery by domain, weak SLOs and a predicted grade.

The predicted grade only uses examined (summative) SLOs the student has practised,
each weighted by its teaching periods (a proxy for its weight in the paper). It is
shown with how much of the syllabus it covers, so it reads as an estimate.
"""

from contextlib import contextmanager

from edu_db.models import CurriculumDomain, GradeSubject, Project, Slo
from edu_db.session import get_session_factory
from sqlalchemy.orm import joinedload

from edu_core.grading import grade_for
from edu_core.mastery import slo_mastery
from edu_core.schemas.progress import (
    DomainProgressDto,
    PredictedGradeDto,
    ProgressDto,
    ProgressSloDto,
    SubjectProgressDto,
)

WEAK_BELOW = 0.8


class ProgressService:
    """Service for the student's progress dashboard."""

    def get_progress(self, user_id: str) -> ProgressDto:
        with self._get_db_session() as db:
            workspaces = (
                db.query(Project)
                .options(joinedload(Project.grade_subject).joinedload(GradeSubject.subject))
                .filter(Project.owner_id == user_id, Project.kind == "subject_workspace")
                .order_by(Project.created_at)
                .all()
            )
            subjects = []
            for project in workspaces:
                grade_subject = project.grade_subject
                if grade_subject is None:
                    continue
                subjects.append(self._subject_progress(db, user_id, project, grade_subject))
            return ProgressDto(subjects=subjects)

    def _subject_progress(
        self, db, user_id: str, project: Project, grade_subject: GradeSubject
    ) -> SubjectProgressDto:
        rows = (
            db.query(Slo, CurriculumDomain)
            .join(CurriculumDomain, Slo.domain_id == CurriculumDomain.id)
            .filter(Slo.grade_subject_id == grade_subject.id)
            .order_by(CurriculumDomain.sort_order, Slo.sort_order)
            .all()
        )
        base = SubjectProgressDto(
            project_id=project.id,
            grade_subject_id=grade_subject.id,
            subject_code=grade_subject.subject.code,
            name=project.name,
            has_slos=bool(rows),
        )
        examined = [(slo, domain) for slo, domain in rows if slo.assessment_form == "summative"]
        if not examined:
            return base

        progress = slo_mastery(db, user_id, (slo.code for slo, _ in examined))
        items = []
        for slo, domain in examined:
            attempts, mastery = progress.get(slo.code, (0, None))
            items.append(
                (
                    slo,
                    domain,
                    ProgressSloDto(
                        code=slo.code,
                        description=slo.description,
                        domain_code=domain.code,
                        mastery=mastery,
                        attempts=attempts,
                    ),
                )
            )
        practised = [(slo, dto) for slo, _, dto in items if dto.mastery is not None]

        domains = []
        for domain in grade_subject.domains:
            in_domain = [dto for _, d, dto in items if d.id == domain.id]
            if not in_domain:
                continue
            done = [dto.mastery for dto in in_domain if dto.mastery is not None]
            domains.append(
                DomainProgressDto(
                    code=domain.code,
                    name=domain.name,
                    examined_count=len(in_domain),
                    practised_count=len(done),
                    mastery=round(sum(done) / len(done), 3) if done else None,
                )
            )

        weakest = sorted(
            (dto for _, dto in practised if dto.mastery < WEAK_BELOW),
            key=lambda dto: dto.mastery,
        )[:5]
        suggested = [
            dto
            for slo, _, dto in sorted(
                (item for item in items if item[2].mastery is None),
                key=lambda item: -(item[0].periods or 0),
            )
        ][:3]

        base.examined_count = len(items)
        base.practised_count = len(practised)
        base.mastery = (
            round(sum(dto.mastery for _, dto in practised) / len(practised), 3)
            if practised
            else None
        )
        base.predicted = self._predict(items, practised)
        base.domains = domains
        base.weakest = weakest
        base.suggested = suggested
        return base

    @staticmethod
    def _predict(items, practised) -> PredictedGradeDto | None:
        if not practised:
            return None
        weight = lambda slo: slo.periods or 1  # noqa: E731
        total = sum(weight(slo) for slo, _, _ in items)
        covered = sum(weight(slo) for slo, _ in practised)
        percent = 100 * sum(weight(slo) * dto.mastery for slo, dto in practised) / covered
        coverage = covered / total if total else 0.0
        grade, descriptor = grade_for(percent)
        return PredictedGradeDto(
            percent=round(percent),
            grade=grade,
            descriptor=descriptor,
            coverage=round(coverage, 3),
            confidence="high" if coverage >= 0.6 else "medium" if coverage >= 0.2 else "low",
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
