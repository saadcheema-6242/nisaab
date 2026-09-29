"""Router for the student's progress dashboard."""

from auth import get_current_user
from dependencies import get_progress_service
from edu_core.schemas.progress import ProgressDto
from edu_core.schemas.users import UserDto
from edu_core.services import ProgressService
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/api/v1/progress", tags=["progress"])


@router.get("", response_model=ProgressDto)
async def get_progress(
    current_user: UserDto = Depends(get_current_user),
    service: ProgressService = Depends(get_progress_service),
):
    """Mastery per subject and domain, weakest SLOs and a predicted grade band."""
    return service.get_progress(user_id=current_user.id)
