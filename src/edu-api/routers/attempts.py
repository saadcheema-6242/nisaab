"""Router for the student's practice history (finished quizzes, flashcards and papers)."""

from auth import get_current_user
from dependencies import get_attempt_service
from edu_core.schemas.attempts import PracticeHistoryItemDto
from edu_core.schemas.users import UserDto
from edu_core.services import AttemptService
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/api/v1/projects/{project_id}/attempts", tags=["attempts"])


@router.get("", response_model=list[PracticeHistoryItemDto])
async def list_practice_history(
    project_id: str,
    current_user: UserDto = Depends(get_current_user),
    service: AttemptService = Depends(get_attempt_service),
):
    """Every finished quiz, flashcard run and paper in this workspace, newest first."""
    return service.history(user_id=current_user.id, project_id=project_id)
