"""Router for user operations."""

from auth import get_current_user
from dependencies import get_user_service
from edu_core.exceptions import NotFoundError
from edu_core.schemas.users import UserDto
from edu_core.services import UserService
from fastapi import APIRouter, Depends, HTTPException

router = APIRouter(prefix="/api/v1/users", tags=["users"])


def _only_self(user_id: str, current_user: UserDto) -> None:
    """Students may only see or delete their own account."""
    if user_id != current_user.id:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found")


@router.get("/{user_id}", response_model=UserDto, summary="Get your own account")
async def get_user(
    user_id: str,
    current_user: UserDto = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
):
    """Get a user by ID (only your own)."""
    _only_self(user_id, current_user)
    try:
        return service.get_user(user_id=user_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=list[UserDto], summary="Get your own account as a list")
async def list_users(
    current_user: UserDto = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
):
    """List users: only your own account, so no one can see other students' emails."""
    try:
        return [service.get_user(user_id=current_user.id)]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{user_id}", status_code=204, summary="Delete your own account")
async def delete_user(
    user_id: str,
    current_user: UserDto = Depends(get_current_user),
    service: UserService = Depends(get_user_service),
):
    """Delete a user (only your own)."""
    _only_self(user_id, current_user)
    try:
        service.delete_user(user_id=user_id)
        return None
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
