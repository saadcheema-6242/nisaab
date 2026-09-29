from typing import Literal

from pydantic import BaseModel, Field


class ProgressSloDto(BaseModel):
    code: str = Field(..., description="FBISE SLO code")
    description: str = Field(..., description="SLO text")
    domain_code: str = Field(..., description="Domain code")
    mastery: float | None = Field(None, description="Mastery 0..1, null if not practised")
    attempts: int = Field(0, description="Practice answers recorded")


class DomainProgressDto(BaseModel):
    code: str = Field(..., description="Domain code, e.g. B")
    name: str = Field(..., description="Domain name, e.g. Mechanics")
    examined_count: int = Field(..., description="Examined (summative) SLOs")
    practised_count: int = Field(..., description="Examined SLOs practised at least once")
    mastery: float | None = Field(None, description="Average mastery of practised SLOs")


class PredictedGradeDto(BaseModel):
    """An estimate, not a result: based only on the SLOs practised so far."""

    percent: int = Field(..., description="Estimated percentage in the theory paper")
    grade: str = Field(..., description="IBCC grade band, e.g. B+")
    descriptor: str = Field(..., description="Band descriptor, e.g. Very Good")
    coverage: float = Field(
        ..., description="Share of the examined syllabus (by teaching time) practised, 0..1"
    )
    confidence: Literal["low", "medium", "high"] = Field(
        ..., description="How much of the syllabus the estimate is based on"
    )


class SubjectProgressDto(BaseModel):
    project_id: str = Field(..., description="ID of the subject workspace")
    grade_subject_id: str = Field(..., description="ID of the grade subject")
    subject_code: str = Field(..., description="PHY, CHEM, BIO or MATH")
    name: str = Field(..., description="Workspace name, e.g. Physics XI")
    has_slos: bool = Field(..., description="False while the SLO map is coming soon")
    examined_count: int = Field(0, description="Examined (summative) SLOs")
    practised_count: int = Field(0, description="Examined SLOs practised at least once")
    mastery: float | None = Field(None, description="Average mastery of practised SLOs")
    predicted: PredictedGradeDto | None = Field(None, description="Estimated grade band")
    domains: list[DomainProgressDto] = Field(default_factory=list)
    weakest: list[ProgressSloDto] = Field(
        default_factory=list, description="Practised SLOs with the lowest mastery"
    )
    suggested: list[ProgressSloDto] = Field(
        default_factory=list, description="Examined SLOs not practised yet, largest first"
    )


class ProgressDto(BaseModel):
    subjects: list[SubjectProgressDto]
