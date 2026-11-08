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


# ---- over time, and by cognitive level ------------------------------------


class TrendPointDto(BaseModel):
    """Where mastery stood at the end of one week."""

    week_start: str = Field(..., description="Monday of the week, ISO date")
    mastery: float | None = Field(None, description="Mastery 0..1, null before any practice")
    attempts: int = Field(0, description="Answers recorded up to the end of that week")


class CognitiveLevelDto(BaseModel):
    """How a student is doing at one FBISE cognitive level.

    The paper weight is what the examination gives this level, so the student
    can see the gap that actually costs marks: 40% on Application is a
    different problem from 40% on Understanding, because Understanding is
    half the paper.
    """

    level: str = Field(..., description="K, U or A")
    name: str = Field(..., description="Knowledge, Understanding or Application")
    paper_weight: int = Field(..., description="Share of the FBISE paper, as a percentage")
    mastery: float | None = Field(None, description="Mastery 0..1, null if not practised")
    examined_count: int = Field(0, description="Examined SLOs at this level")
    practised_count: int = Field(0, description="Of those, practised at least once")


class WeakestLevelDto(BaseModel):
    """The level costing the most marks, weighted by what the paper gives it."""

    level: str = Field(..., description="K, U or A")
    name: str = Field(..., description="Its name")
    marks_at_stake: int = Field(..., description="Roughly how many marks are being lost")


class ActivityDayDto(BaseModel):
    """One day on the practice calendar, including the empty ones."""

    day: str = Field(..., description="ISO date, in the student's own timezone")
    answers: int = Field(0, description="Answers recorded that day")


class ConsistencyDto(BaseModel):
    """How regularly the student actually practises.

    Counted in the student's own day. Pakistan is five hours ahead of UTC, so
    a streak counted on the server's clock breaks for anyone revising in the
    evening, which is most of them.
    """

    current_streak: int = Field(0, description="Days in a row, up to today")
    longest_streak: int = Field(0, description="The best run so far")
    days_practised: int = Field(0, description="Distinct days with any practice")
    answers_this_week: int = Field(0, description="Answers since Monday")
    last_day: str | None = Field(None, description="The most recent day practised")
    calendar: list[ActivityDayDto] = Field(
        default_factory=list, description="Recent days, newest last, gaps included"
    )


class SubjectGraphsDto(BaseModel):
    """The graphs for one subject."""

    project_id: str = Field(..., description="ID of the subject workspace")
    subject_code: str = Field(..., description="PHY, CHEM, BIO, MATH or CS")
    name: str = Field(..., description="Workspace name, e.g. Physics XI")
    mastery: float | None = Field(None, description="Mastery now, matching the overview")
    trend: list[TrendPointDto] = Field(default_factory=list)
    cognitive: list[CognitiveLevelDto] = Field(default_factory=list)
    weakest_level: WeakestLevelDto | None = Field(None)


class ProgressGraphsDto(BaseModel):
    """Everything the graphs tab needs, in one call."""

    subjects: list[SubjectGraphsDto] = Field(default_factory=list)
    consistency: ConsistencyDto = Field(..., description="Across every subject")
    overall_trend: list[TrendPointDto] = Field(
        default_factory=list, description="Mastery across all subjects together"
    )
