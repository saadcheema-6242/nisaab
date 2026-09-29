"""Router for subject teachers reviewing the shared SLO content."""

from auth import get_current_user
from config import get_settings
from dependencies import get_content_service
from edu_core.schemas.content import ContentItemDto, ContentSummaryDto, ReviewerStateDto
from edu_core.schemas.users import UserDto
from edu_core.services import ContentService
from fastapi import APIRouter, Depends, HTTPException, Query

from routers.schemas import ContentReview

router = APIRouter(prefix="/api/v1/review", tags=["review"])


def is_reviewer(user: UserDto) -> bool:
    return bool(user.email) and user.email.lower() in get_settings().reviewers


def require_reviewer(current_user: UserDto = Depends(get_current_user)) -> UserDto:
    if not is_reviewer(current_user):
        raise HTTPException(status_code=403, detail="Only content reviewers can do this")
    return current_user


@router.get("/me", response_model=ReviewerStateDto)
async def get_reviewer_state(current_user: UserDto = Depends(get_current_user)):
    """Whether the current user may review content."""
    return ReviewerStateDto(is_reviewer=is_reviewer(current_user))


@router.get("/items", response_model=list[ContentItemDto])
async def list_review_items(
    grade_subject_id: str = Query(..., description="Grade subject to review"),
    domain_code: str | None = Query(None, description="Only this domain, e.g. B"),
    kind: str | None = Query(None, description="explainer, mcq or srq"),
    review_status: str | None = Query(None, description="draft, approved or rejected"),
    slo_code: str | None = Query(None, description="Only this SLO"),
    reviewer: UserDto = Depends(require_reviewer),
    service: ContentService = Depends(get_content_service),
):
    """Content items in syllabus order."""
    return service.list_items(
        grade_subject_id=grade_subject_id,
        domain_code=domain_code,
        kind=kind,
        review_status=review_status,
        slo_code=slo_code,
    )


@router.get("/summary", response_model=list[ContentSummaryDto])
async def review_summary(
    grade_subject_id: str = Query(..., description="Grade subject"),
    reviewer: UserDto = Depends(require_reviewer),
    service: ContentService = Depends(get_content_service),
):
    """Item counts per kind and review status."""
    return service.summary(grade_subject_id=grade_subject_id)


@router.patch("/items/{item_id}", response_model=ContentItemDto)
async def review_item(
    item_id: str,
    review: ContentReview,
    reviewer: UserDto = Depends(require_reviewer),
    service: ContentService = Depends(get_content_service),
):
    """Approve or reject an item, with an optional note on what to fix."""
    return service.review(
        item_id=item_id,
        reviewer=reviewer.email or reviewer.id,
        review_status=review.review_status,
        review_note=review.review_note,
    )
