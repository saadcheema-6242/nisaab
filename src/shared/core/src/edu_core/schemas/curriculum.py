from typing import Literal

from pydantic import BaseModel, Field


class GradeSubjectDto(BaseModel):
    """A subject in one grade, e.g. Physics XI."""

    id: str = Field(..., description="Unique ID of the grade subject")
    subject_code: str = Field(..., description="Subject code: PHY, CHEM, BIO or MATH")
    subject_name: str = Field(..., description="Subject name, e.g. Physics")
    grade: int = Field(..., description="Grade: 11 (HSSC-I) or 12 (HSSC-II)")
    scheme: str = Field(..., description="FBISE scheme of studies, e.g. ISS-2024")
    curriculum: str | None = Field(None, description="Curriculum, e.g. NCP 2022-23")
    source_url: str | None = Field(
        None, description="FBISE Assessment Framework the SLOs come from"
    )
    status: Literal["available", "coming_soon"] = Field(
        ..., description="available once the SLOs are loaded"
    )
    slo_count: int = Field(0, description="Number of SLOs")


class SloDto(BaseModel):
    """A Student Learning Outcome with the student's progress on it."""

    id: str = Field(..., description="Unique ID of the SLO")
    code: str = Field(..., description="FBISE SLO code, e.g. P-11-B-05")
    grade_subject_id: str = Field(..., description="ID of the grade subject")
    domain_code: str = Field(..., description="Domain code, e.g. B")
    domain_name: str = Field(..., description="Domain name, e.g. Mechanics")
    content_area: str | None = Field(None, description="Content area, e.g. Vectors")
    description: str = Field(..., description="SLO text as published by FBISE")
    assessment_form: Literal["summative", "formative", "practical", "unknown"] = Field(
        ...,
        description=(
            "summative: examined in the annual exam; formative: classroom only; "
            "practical: assessed in the practical exam"
        ),
    )
    cognitive_levels: list[Literal["K", "U", "A"]] = Field(
        default_factory=list,
        description="Knowledge, Understanding, Application",
    )
    periods: int | None = Field(None, description="Teaching periods (40 minutes each)")
    attempts: int = Field(0, description="Practice answers recorded for this SLO")
    mastery: float | None = Field(
        None, description="Estimated mastery 0..1, null before any practice"
    )


class DomainDto(BaseModel):
    """A curriculum domain with its SLOs."""

    code: str = Field(..., description="Domain code, e.g. B")
    name: str = Field(..., description="Domain name, e.g. Mechanics")
    slo_count: int = Field(..., description="Number of SLOs")
    examined_count: int = Field(..., description="Number of summative (examined) SLOs")
    mastery: float | None = Field(
        None, description="Average mastery of the practised SLOs, 0..1"
    )
    slos: list[SloDto] = Field(default_factory=list)


class CurriculumTreeDto(BaseModel):
    """The syllabus map of one grade subject."""

    grade_subject: GradeSubjectDto
    domains: list[DomainDto]
