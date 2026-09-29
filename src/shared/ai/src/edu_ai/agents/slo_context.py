"""Load an FBISE SLO as prompt context for SLO-targeted generation."""

from edu_db.models import CurriculumDomain, GradeSubject, Project, Slo, Subject
from pydantic import BaseModel
from sqlalchemy.orm import Session

GRADE_LABELS = {11: "Class XI (HSSC-I)", 12: "Class XII (HSSC-II)"}
COGNITIVE_LEVELS = {"K": "Knowledge", "U": "Understanding", "A": "Application"}
LANGUAGE_NAMES = {
    "en": "English",
    "ur": "Urdu (in Urdu script)",
    "ur-Latn": "Roman Urdu (Urdu written in English letters, as Pakistani students text)",
}


def language_name(code: str | None) -> str:
    return LANGUAGE_NAMES.get(code or "en", code or "English")


class SloContext(BaseModel):
    code: str
    description: str
    domain: str
    content_area: str | None
    assessment_form: str
    cognitive_levels: list[str]
    subject: str
    grade_label: str

    @property
    def levels_text(self) -> str:
        levels = [f"{c} ({COGNITIVE_LEVELS.get(c, c)})" for c in self.cognitive_levels]
        return ", ".join(levels) or "not specified"

    def prompt_vars(self) -> dict:
        return {
            "slo": self.model_dump(),
            "slo_levels": self.levels_text,
            "subject": self.subject,
            "grade_label": self.grade_label,
        }


def load_slo(
    db: Session,
    slo_code: str,
    project: Project | None = None,
    grade_subject_id: str | None = None,
) -> SloContext | None:
    """Find an SLO by code, preferring the given (or the project's) grade subject."""
    query = (
        db.query(Slo, CurriculumDomain, GradeSubject, Subject)
        .join(CurriculumDomain, Slo.domain_id == CurriculumDomain.id)
        .join(GradeSubject, Slo.grade_subject_id == GradeSubject.id)
        .join(Subject, GradeSubject.subject_id == Subject.id)
        .filter(Slo.code == slo_code.strip().upper())
    )
    preferred = grade_subject_id or (project.grade_subject_id if project is not None else None)
    row = query.filter(Slo.grade_subject_id == preferred).first() if preferred else None
    row = row or query.first()
    if row is None:
        return None
    slo, domain, grade_subject, subject = row
    return SloContext(
        code=slo.code,
        description=slo.description,
        domain=domain.name,
        content_area=slo.content_area,
        assessment_form=slo.assessment_form,
        cognitive_levels=list(slo.cognitive_levels or []),
        subject=subject.name,
        grade_label=GRADE_LABELS.get(grade_subject.grade, f"Grade {grade_subject.grade}"),
    )
