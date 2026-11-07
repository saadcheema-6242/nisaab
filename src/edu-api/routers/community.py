"""Router for the room a student shares with the rest of their class."""

import json

from auth import get_current_user
from dependencies import get_community_service, get_usage_service
from edu_core.community_media import MAX_ATTACHMENTS
from edu_core.exceptions import NotFoundError
from edu_core.schemas.community import CommunityPostDto, CommunityRoomDto
from edu_core.schemas.users import UserDto
from edu_core.services.community import CommunityService
from edu_core.services.usage import UsageService
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from starlette.responses import Response

router = APIRouter(prefix="/api/v1/community", tags=["community"])

# Read in slices so a file that lies about its length cannot be streamed into
# memory. The declared size is a claim like any other.
CHUNK = 1024 * 1024


class PostCreate(BaseModel):
    """What a student sends when they write something.

    There is no grade or group here on purpose. The room is read from the
    student's own profile on the server, so there is nothing in the request
    that could put a post in somebody else's class.
    """

    body: str = Field("", description="What to say")
    parent_id: str | None = Field(None, description="The post being replied to")
    poll_question: str | None = Field(None, description="Makes this post a poll")
    poll_options: list[str] | None = Field(None, description="The poll's options")


class ReportCreate(BaseModel):
    """A student saying a post needs looking at."""

    reason: str | None = Field(None, description="Which reason they picked")
    note: str | None = Field(None, description="Anything they want to add")


def _posts_left(usage: UsageService, user_id: str) -> int:
    """How many more posts today, for the page to show before they run out."""
    try:
        used = usage.get_usage(user_id)
        return max(
            0,
            usage.max_community_posts_per_day
            - getattr(used, "community_posts_today", 0),
        )
    except Exception:  # noqa: BLE001 - a counter must never break the room
        return usage.max_community_posts_per_day


@router.get("", response_model=CommunityRoomDto)
async def get_room(
    current_user: UserDto = Depends(get_current_user),
    service: CommunityService = Depends(get_community_service),
    usage: UsageService = Depends(get_usage_service),
):
    """The student's own class room: who is in it and what has been said."""
    try:
        return service.get_room(
            user_id=current_user.id,
            posts_left=_posts_left(usage, current_user.id),
        )
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error))


@router.post("", response_model=CommunityPostDto, status_code=201)
async def add_post(
    post: PostCreate,
    current_user: UserDto = Depends(get_current_user),
    service: CommunityService = Depends(get_community_service),
    usage: UsageService = Depends(get_usage_service),
):
    """Say something in the student's own room, or reply to a post in it."""
    # Counted before the work, and not caught: main.py turns a
    # UsageLimitExceededError into a 429 with the limit in it, so the
    # student is told how many they get rather than that something broke.
    usage.check_and_increment(user_id=current_user.id, usage_type="community_post")
    try:
        return service.add_post(
            user_id=current_user.id,
            body=post.body,
            parent_id=post.parent_id,
            poll_question=post.poll_question,
            poll_options=post.poll_options,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error))


@router.post("/with-files", response_model=CommunityPostDto, status_code=201)
async def add_post_with_files(
    body: str = Form(""),
    parent_id: str | None = Form(None),
    durations: str | None = Form(
        None, description="JSON list of seconds, one per file, for voice notes"
    ),
    files: list[UploadFile] = File(default_factory=list),
    current_user: UserDto = Depends(get_current_user),
    service: CommunityService = Depends(get_community_service),
    usage: UsageService = Depends(get_usage_service),
):
    """A post with photos, files or a voice note attached.

    Separate from the JSON route because multipart and JSON cannot share a
    body, not because it is a different kind of post.
    """
    if len(files) > MAX_ATTACHMENTS:
        raise HTTPException(
            status_code=400,
            detail=f"At most {MAX_ATTACHMENTS} files on one post.",
        )

    spoken: list[int | None] = []
    if durations:
        try:
            spoken = list(json.loads(durations))
        except (ValueError, TypeError):
            spoken = []

    usage.check_and_increment(user_id=current_user.id, usage_type="community_post")

    uploads = []
    for index, upload in enumerate(files):
        data = await upload.read()
        uploads.append(
            (
                upload.filename,
                upload.content_type or "application/octet-stream",
                data,
                spoken[index] if index < len(spoken) else None,
            )
        )

    try:
        return service.add_post(
            user_id=current_user.id,
            body=body,
            parent_id=parent_id,
            uploads=uploads,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error))


@router.post("/{post_id}/report", status_code=204)
async def report_post(
    post_id: str,
    report: ReportCreate,
    current_user: UserDto = Depends(get_current_user),
    service: CommunityService = Depends(get_community_service),
):
    """Tell a teacher this post needs looking at."""
    try:
        service.report_post(
            user_id=current_user.id,
            post_id=post_id,
            reason=report.reason,
            note=report.note,
        )
        return None
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error))


@router.post("/{post_id}/vote/{option_id}", response_model=CommunityPostDto)
async def vote(
    post_id: str,
    option_id: str,
    current_user: UserDto = Depends(get_current_user),
    service: CommunityService = Depends(get_community_service),
):
    """Pick an option in a poll, or change an earlier pick."""
    try:
        return service.vote(
            user_id=current_user.id, post_id=post_id, option_id=option_id
        )
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error))


@router.get("/attachments/{attachment_id}")
async def download_attachment(
    attachment_id: str,
    current_user: UserDto = Depends(get_current_user),
    service: CommunityService = Depends(get_community_service),
):
    """Download a file from the student's own room.

    Goes through the API rather than straight to the bucket so the room is
    checked. A signed link is fine inside a page for a few hours; it is not
    a way to reach a file belonging to another class.
    """
    try:
        data, filename, content_type = service.attachment_bytes(
            user_id=current_user.id, attachment_id=attachment_id
        )
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error))

    # The filename is quoted and already stripped of paths by safe_name, so
    # it cannot break out of the header or name a directory.
    safe = filename.replace('"', "")
    return Response(
        content=data,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{safe}"'},
    )


@router.post("/warnings/seen", status_code=204)
async def mark_warnings_seen(
    current_user: UserDto = Depends(get_current_user),
    service: CommunityService = Depends(get_community_service),
):
    """The student has read their warnings, so stop showing them."""
    service.mark_warnings_seen(user_id=current_user.id)
    return None


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
