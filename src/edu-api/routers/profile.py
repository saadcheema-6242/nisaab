"""Router for the student profile and onboarding."""

from auth import get_current_user
from dependencies import get_profile_service
from edu_core.schemas.profiles import (
    OnboardingResultDto,
    ProfileStateDto,
    StudentProfileDto,
)
from edu_core.schemas.users import UserDto
from edu_core.services import ProfileService
from fastapi import APIRouter, Depends

from routers.schemas import OnboardingRequest, ProfileUpdate

router = APIRouter(prefix="/api/v1", tags=["profile"])


@router.get("/profile", response_model=ProfileStateDto)
async def get_profile(
    current_user: UserDto = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
):
    """Get the student's profile and whether onboarding is complete."""
    return service.get_profile_state(user_id=current_user.id)


@router.put("/profile", response_model=StudentProfileDto)
async def update_profile(
    update: ProfileUpdate,
    current_user: UserDto = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
):
    """Update the explanation language or exam year."""
    return service.update_profile(
        user_id=current_user.id,
        explanation_language=update.explanation_language,
        exam_year=update.exam_year,
    )


@router.post("/onboarding", response_model=OnboardingResultDto)
async def complete_onboarding(
    onboarding: OnboardingRequest,
    current_user: UserDto = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
):
    """Save grade, group and language, and create the subject workspaces."""
    return service.complete_onboarding(
        user_id=current_user.id,
        grade=onboarding.grade,
        group_code=onboarding.group_code,
        explanation_language=onboarding.explanation_language,
        exam_year=onboarding.exam_year,
    )
