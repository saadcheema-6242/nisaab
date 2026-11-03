"""Router for the room a student shares with the rest of their class."""

from auth import get_current_user
from dependencies import get_community_service
from edu_core.exceptions import NotFoundError
from edu_core.schemas.community import CommunityPostDto, CommunityRoomDto
from edu_core.schemas.users import UserDto
from edu_core.services.community import CommunityService
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1/community", tags=["community"])


class PostCreate(BaseModel):
    """What a student sends when they write something.

    There is no grade or group here on purpose. The room is read from the
    student's own profile on the server, so there is nothing in the request
    that could put a post in somebody else's class.
    """

    body: str = Field(..., description="What to say")
    parent_id: str | None = Field(None, description="The post being replied to")


@router.get("", response_model=CommunityRoomDto)
async def get_room(
    current_user: UserDto = Depends(get_current_user),
    service: CommunityService = Depends(get_community_service),
):
    """The student's own class room: who is in it and what has been said."""
    try:
        return service.get_room(user_id=current_user.id)
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error))


@router.post("", response_model=CommunityPostDto, status_code=201)
async def add_post(
    post: PostCreate,
    current_user: UserDto = Depends(get_current_user),
    service: CommunityService = Depends(get_community_service),
):
    """Say something in the student's own room, or reply to a post in it."""
    try:
        return service.add_post(
            user_id=current_user.id, body=post.body, parent_id=post.parent_id
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error))


@router.delete("/{post_id}", status_code=204)
async def delete_post(
    post_id: str,
    current_user: UserDto = Depends(get_current_user),
    service: CommunityService = Depends(get_community_service),
):
    """Remove a post the student wrote themselves."""
    try:
        service.delete_post(user_id=current_user.id, post_id=post_id)
        return None
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error))
