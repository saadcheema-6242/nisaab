"""Router for looking after accounts: who is on the system, and what to do.

Who counts as an administrator is decided once, here, from ADMIN_EMAILS, the
same way content reviewers are. It is not a column on the user, deliberately:
a flag in the database can be set by anything that can write to the database,
whereas this needs a deploy.
"""

from auth import get_current_user
from config import get_settings
from dependencies import get_admin_service
from edu_core.exceptions import NotFoundError
from edu_core.schemas.admin import (
    AdminUserDetailDto,
    AdminUserDto,
    AdminUserListDto,
    DeletionReportDto,
)
from edu_core.schemas.users import UserDto
from edu_core.services.admin import AdminService
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


def is_admin(user: UserDto) -> bool:
    return bool(user.email) and user.email.lower() in get_settings().admins


def require_admin(current_user: UserDto = Depends(get_current_user)) -> UserDto:
    # 404 rather than 403, so the existence of this section is not advertised
    # to every signed-in student who guesses the URL.
    if not is_admin(current_user):
        raise HTTPException(status_code=404, detail="Not found")
    return current_user


class AdminStateDto(BaseModel):
    is_admin: bool = Field(..., description="True if this user may manage accounts")


class BanRequest(BaseModel):
    """A suspension. Leave days empty or zero for a permanent one."""

    days: int | None = Field(None, description="How long it lasts; empty means forever")
    reason: str = Field(..., description="Shown to the student when they are turned away")


@router.get("/me", response_model=AdminStateDto)
async def get_admin_state(current_user: UserDto = Depends(get_current_user)):
    """Whether the signed-in user may manage accounts.

    Open to anyone signed in, because the student interface asks it to decide
    whether to show the menu entry at all. It answers false, which tells a
    student nothing they could not already work out.
    """
    return AdminStateDto(is_admin=is_admin(current_user))


@router.get("/users", response_model=AdminUserListDto)
async def list_users(
    search: str = Query("", description="Match on email, name or exact id"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _: UserDto = Depends(require_admin),
    service: AdminService = Depends(get_admin_service),
):
    """Every account, newest first, with a summary of the whole system."""
    return service.list_users(search=search, limit=limit, offset=offset)


@router.get("/users/{user_id}", response_model=AdminUserDetailDto)
async def get_user(
    user_id: str,
    _: UserDto = Depends(require_admin),
    service: AdminService = Depends(get_admin_service),
):
    """One account, with everything it owns counted."""
    try:
        return service.get_user(user_id)
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error))


@router.post("/users/{user_id}/ban", response_model=AdminUserDto)
async def ban_user(
    user_id: str,
    ban: BanRequest,
    current_user: UserDto = Depends(require_admin),
    service: AdminService = Depends(get_admin_service),
):
    """Suspend an account, temporarily or permanently."""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot suspend yourself")
    try:
        return service.set_ban(
            user_id=user_id,
            days=ban.days,
            reason=ban.reason,
            by=current_user.email or current_user.id,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error))


@router.post("/users/{user_id}/unban", response_model=AdminUserDto)
async def unban_user(
    user_id: str,
    _: UserDto = Depends(require_admin),
    service: AdminService = Depends(get_admin_service),
):
    """Let a suspended account back in."""
    try:
        return service.lift_ban(user_id)
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error))


@router.delete("/users/{user_id}", response_model=DeletionReportDto)
async def delete_user(
    user_id: str,
    confirm_email: str = Query(
        ...,
        description="The account's own email, typed again. Guards against "
        "deleting the row the mouse happened to be over.",
    ),
    current_user: UserDto = Depends(require_admin),
    service: AdminService = Depends(get_admin_service),
):
    """Delete an account and everything it owns. There is no undo."""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot delete yourself")

    try:
        account = service.get_user(user_id)
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error))

    # Typing the email again is the whole safety mechanism. A confirmation
    # dialog is clicked through; an address has to be read off the row first.
    if (confirm_email or "").strip().lower() != (account.email or "").strip().lower():
        raise HTTPException(
            status_code=400,
            detail="That is not this account's email address. Nothing was deleted.",
        )

    try:
        return service.delete_user(user_id)
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error))


# What has to be typed, exactly, to wipe the system. A phrase rather than a
# checkbox: it cannot be clicked through, it cannot be hit by a stray Enter,
# and it says out loud what is about to happen.
WIPE_PHRASE = "DELETE ALL USERS"


@router.delete("/users", response_model=DeletionReportDto)
async def delete_all_users(
    confirm: str = Query(
        ...,
        description=f'Type exactly "{WIPE_PHRASE}". Anything else deletes nothing.',
    ),
    expected_count: int = Query(
        ...,
        ge=0,
        description="How many accounts you expect to delete, excluding your own. "
        "If the real number differs, nothing is deleted.",
    ),
    current_user: UserDto = Depends(require_admin),
    service: AdminService = Depends(get_admin_service),
):
    """Delete every account except your own. There is no undo.

    Two guards, and they catch different mistakes. The phrase stops the action
    being taken by accident. The count stops it being taken on a different
    system from the one being looked at - a number read off a staging screen
    will not match production, and the request is refused instead of wiping
    the wrong database.
    """
    if confirm != WIPE_PHRASE:
        raise HTTPException(
            status_code=400,
            detail=f'Type "{WIPE_PHRASE}" exactly. Nothing was deleted.',
        )

    listing = service.list_users(limit=1)
    others = max(0, listing.overview.total_users - 1)
    if others != expected_count:
        raise HTTPException(
            status_code=409,
            detail=(
                f"There are {others} other accounts, not {expected_count}. "
                "Nothing was deleted. Reload and check what you are looking at."
            ),
        )

    return service.delete_everyone(keep_user_id=current_user.id)
