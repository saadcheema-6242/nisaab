"""History and Library: everything a student has made, and everything they uploaded.

Both are cross-project reads. They exist because the per-project views
answer "what is in Physics", and a student looking for the quiz they made
last week is asking "where is my work", which is a different question.

Read-only, and scoped to the caller in the service rather than here, so
there is no id in the path that could be swapped for somebody else's.
"""

from auth import get_current_user
from dependencies import get_library_service
from edu_core.schemas.users import UserDto
from edu_core.services.library import LibraryService
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/api/v1/library", tags=["library"])


@router.get("/history")
def history(
    current_user: UserDto = Depends(get_current_user),
    service: LibraryService = Depends(get_library_service),
):
    """Quizzes, papers, flashcards, notes, mind maps and plans, newest first."""
    return service.history(current_user.id)


@router.get("/documents")
def documents(
    current_user: UserDto = Depends(get_current_user),
    service: LibraryService = Depends(get_library_service),
):
    """Every uploaded document, newest first."""
    return service.library(current_user.id)
