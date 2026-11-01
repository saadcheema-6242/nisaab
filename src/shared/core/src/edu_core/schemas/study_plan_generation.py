from typing import Literal

from pydantic import BaseModel, Field


class StudyResource(BaseModel):
    id: str = Field(description="ID of the resource (quiz or flashcard)")
    parent_id: str | None = Field(None, description="ID of the parent (e.g. Flashcard Group ID or Quiz ID) for navigation")
    type: Literal["quiz", "flashcard"] = Field(description="Type of the resource")
    title: str = Field(description="Title of the resource")
    description: str | None = Field(None, description="Optional description")


class WeeklyScheduleDay(BaseModel):
    day: str = Field(description="e.g. 'Monday' or 'Day 1'")
    tasks: list[str] = Field(description="List of tasks for the day")


class StudyPlanItem(BaseModel):
    """One thing to do, on one day, against one FBISE outcome.

    Rows rather than prose, because an item carries the outcome it practises
    and so can be ticked off from the student's own practice records - the plan
    keeps up with them instead of going stale the day after it is written.
    """

    day: int = Field(description="Which day of the plan, starting at 1")
    slo_code: str = Field(description="The FBISE outcome, e.g. P-11-B-05")
    action: Literal["read", "flashcards", "quiz", "srq", "paper"] = Field(
        description="What the student does"
    )
    title: str = Field(description="What to do, in one line a student can follow")
    minutes: int = Field(description="How long to spend on it")
    target: str | None = Field(
        None, description="What counts as done, e.g. 'Score 70% or more'"
    )
    domain: str = Field("", description="The syllabus domain this outcome sits in")
    standing: str = Field(
        "", description="Why it is here: struggling, weak, unknown or solid"
    )


class StudyPlanContent(BaseModel):
    """Schema for structured study plan content.

    Every field has a default so that plans written before the plan became a
    day-by-day schedule still load. Only ``analysis``, ``items`` and
    ``encouragement`` are written now.
    """

    analysis: str = Field("", description="Brief summary of current performance and analysis.")
    focus_areas: list[str] = Field(
        default_factory=list, description="The outcomes this plan concentrates on."
    )
    items: list[StudyPlanItem] = Field(
        default_factory=list, description="The plan itself: what to do, when."
    )
    encouragement: str = Field("", description="Encouraging closing message.")

    # Written by earlier versions; kept so old plans still load and display.
    action_items: list[StudyResource] = Field(default_factory=list)
    schedule: list[WeeklyScheduleDay] = Field(default_factory=list)
