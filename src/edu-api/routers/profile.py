"""Router for the student profile and onboarding."""

from auth import get_current_user
from config import get_settings
from dependencies import get_profile_service
from edu_core.exceptions import NotFoundError
from edu_core.schemas.profiles import (
    OnboardingResultDto,
    ProfileStateDto,
    StudentProfileDto,
)
from edu_core.group_change import describe, is_group
from edu_core.schemas.users import UserDto
from edu_core.services import ProfileService
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

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
    """Save grade, group and language, and create the subject workspaces.

    An administrator gets every FSc subject in both years rather than one
    group's three: they are a student of all of it, as well as a teacher and
    an administrator. Decided here from the email list, not from anything
    the request says, so claiming to be an administrator in the body buys
    nothing.
    """
    admin = bool(current_user.email) and current_user.email.lower() in get_settings().admins
    return service.complete_onboarding(
        user_id=current_user.id,
        grade=onboarding.grade,
        group_code=onboarding.group_code,
        explanation_language=onboarding.explanation_language,
        exam_year=onboarding.exam_year,
        all_cohorts=admin,
    )


class GroupChange(BaseModel):
    """Which FSc group to move to."""

    group_code: str = Field(..., description="PRE_MED, PRE_ENG or ICS")


@router.get("/profile/group-change")
async def preview_group_change(
    group_code: str,
    current_user: UserDto = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
):
    """What moving to this group would add and hide, before committing to it.

    Named subjects rather than a count: "2 subjects will be hidden" is not
    something a student can check, and "Chemistry and Biology" is.
    """
    if not is_group(group_code):
        raise HTTPException(status_code=400, detail=f"{group_code} is not an FSc group")
    state = service.get_profile_state(user_id=current_user.id)
    current = state.profile.group_code if state.profile else None
    return {"summary": describe(current, group_code), "current_group": current}


@router.post("/profile/group", response_model=OnboardingResultDto)
async def change_group(
    change: GroupChange,
    current_user: UserDto = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
):
    """Move to another FSc group.

    Subjects the new group does not study are hidden, not deleted, so moving
    back restores them with the work still in them.
    """
    if not is_group(change.group_code):
        raise HTTPException(
            status_code=400, detail=f"{change.group_code} is not an FSc group"
        )
    try:
        return service.change_group(
            user_id=current_user.id, group_code=change.group_code
        )
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error))
