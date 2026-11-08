"""Router for the student's progress dashboard."""

from auth import get_current_user
from dependencies import get_progress_service
from edu_core.schemas.progress import ProgressDto, ProgressGraphsDto
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


@router.get("/graphs", response_model=ProgressGraphsDto)
async def get_graphs(
    current_user: UserDto = Depends(get_current_user),
    service: ProgressService = Depends(get_progress_service),
):
    """Mastery over time, by FBISE cognitive level, and how often they practise.

    Its own route rather than more fields on the one above. The overview is
    what loads when the page opens and needs no history; this reads every
    answer the student has ever recorded, and the tab most people never open
    should not slow down the one they all do.
    """
    return service.get_graphs(user_id=current_user.id)
