from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from edu_core.schemas.projects import ProjectDto

GroupCode = Literal["PRE_MED", "PRE_ENG"]
ExplanationLanguage = Literal["en", "ur", "ur-Latn"]


class StudentProfileDto(BaseModel):
    """The student's FSc details."""

    model_config = {"from_attributes": True}

    user_id: str = Field(..., description="ID of the user")
    grade: int = Field(..., description="Grade: 11 (HSSC-I) or 12 (HSSC-II)")
    group_code: GroupCode = Field(..., description="FSc group")
    explanation_language: ExplanationLanguage = Field(
        ..., description="Language the tutor explains in: English, Urdu or Roman Urdu"
    )
    exam_year: int | None = Field(None, description="Year of the student's annual exam")
    onboarding_completed_at: datetime | None = Field(
        None, description="When onboarding was completed"
    )


class ProfileStateDto(BaseModel):
    """Whether the student has completed onboarding, and their profile if so."""

    onboarded: bool = Field(..., description="True once onboarding is complete")
    profile: StudentProfileDto | None = Field(None, description="The student's profile")


class OnboardingResultDto(BaseModel):
    """The profile and the subject workspaces created by onboarding."""

    profile: StudentProfileDto
    projects: list[ProjectDto] = Field(..., description="The subject workspaces")
