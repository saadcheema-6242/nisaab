"""Public, read-only links to a quiz or a paper.

Two routers, deliberately separate files' worth of thinking in one:

    /api/v1/shares needs a signed-in account. Making a link, listing
    your own, withdrawing one.

    /api/v1/public/shares/{token} needs nothing at all. It is the only
    unauthenticated route in NISAAB, so it is written to do as little as
    possible: it reads one row found by an unguessable token, reads the
    quiz or paper that row names, bumps a counter, and returns. It never
    creates, never marks, never calls a model, and never touches
    anybody's progress - which is what makes it safe to leave open.

The token is checked for shape in the service before the database is
asked, so this route cannot be used to make the server run a query for
every string somebody tries.
"""

from auth import get_current_user
from dependencies import get_share_service
from edu_core.exceptions import NotFoundError
from edu_core.schemas.users import UserDto
from edu_core.services.shares import ShareService
from edu_core.sharing import ShareError, share_path
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1/shares", tags=["shares"])
public_router = APIRouter(prefix="/api/v1/public", tags=["shares"])


class ShareCreate(BaseModel):
    kind: str = Field(..., description="quiz or paper")
    target_id: str = Field(..., description="The quiz or paper being shared")
    title: str | None = Field(None, description="Shown on the shared page")


class ShareDto(BaseModel):
    id: str
    token: str
    kind: str
    target_id: str
    title: str | None
    created_at: object
    opened_count: int
    # The path rather than a whole URL: the same API serves localhost,
    # the Firebase domain and the custom domain, and a link that named
    # one of them would be wrong on the other two. The page joins it to
    # whatever origin it is being read from.
    path: str

    model_config = {"from_attributes": True}


def _dto(row) -> ShareDto:
    return ShareDto(
        id=row.id,
        token=row.token,
        kind=row.kind,
        target_id=row.target_id,
        title=row.title,
        created_at=row.created_at,
        opened_count=row.opened_count or 0,
        path=share_path(row.token),
    )


@router.post("", response_model=ShareDto, status_code=201)
def create_share(
    body: ShareCreate,
    current_user: UserDto = Depends(get_current_user),
    service: ShareService = Depends(get_share_service),
):
    """Share a quiz or a paper. Pressing it twice returns the same link."""
    try:
        return _dto(
            service.create(
                user_id=current_user.id,
                kind=body.kind,
                target_id=body.target_id,
                title=body.title,
            )
        )
    except ShareError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("", response_model=list[ShareDto])
def my_shares(
    current_user: UserDto = Depends(get_current_user),
    service: ShareService = Depends(get_share_service),
):
    """Every live link this account has made."""
    return [_dto(r) for r in service.mine(current_user.id)]


@router.delete("/{share_id}", status_code=204)
def revoke_share(
    share_id: str,
    current_user: UserDto = Depends(get_current_user),
    service: ShareService = Depends(get_share_service),
):
    """Withdraw a link. The quiz or paper itself is untouched."""
    try:
        service.revoke(share_id=share_id, user_id=current_user.id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@public_router.get("/shares/{token}")
def read_share(
    token: str,
    service: ShareService = Depends(get_share_service),
):
    """Read a shared quiz or paper. No account needed.

    Everything returned is content the owner chose to publish, plus the
    owner's display name so a reader knows whose work they are looking
    at. No email, no ids belonging to anybody else, and nothing about
    the reader is recorded beyond a count of opens.

    A revoked link, a token that is not ours, and a quiz deleted after
    it was shared all answer the same way: 404. A reader has no business
    being able to tell those apart, and a stale link is not an error on
    their part.
    """
    try:
        return service.read(token)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail="No such link") from exc
