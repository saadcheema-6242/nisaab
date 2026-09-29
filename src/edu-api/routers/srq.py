"""Router for short-response questions (SRQs) and AI marking."""

from auth import get_current_user
from dependencies import get_srq_service, get_usage_service
from edu_core.schemas.srq import SrqAttemptDto, SrqDetailDto, SrqQuestionDto
from edu_core.schemas.users import UserDto
from edu_core.services import SrqService, UsageService
from fastapi import APIRouter, Depends, Query

from routers.schemas import SrqAnswer, SrqCreate

router = APIRouter(prefix="/api/v1/projects/{project_id}/srq", tags=["srq"])


@router.post("", response_model=SrqQuestionDto, status_code=201)
async def create_srq(
    project_id: str,
    request: SrqCreate,
    current_user: UserDto = Depends(get_current_user),
    service: SrqService = Depends(get_srq_service),
    usage_service: UsageService = Depends(get_usage_service),
):
    """Generate a short-response question for an SLO (takes a few seconds)."""
    usage_service.check_and_increment(current_user.id, "quiz_generation")
    return await service.generate(
        project_id=project_id, user_id=current_user.id, slo_code=request.slo_code
    )


@router.get("", response_model=list[SrqQuestionDto])
async def list_srqs(
    project_id: str,
    slo_code: str | None = Query(None, description="Only questions for this SLO"),
    current_user: UserDto = Depends(get_current_user),
    service: SrqService = Depends(get_srq_service),
):
    """List the project's short-response questions, newest first."""
    return service.list_questions(
        project_id=project_id, user_id=current_user.id, slo_code=slo_code
    )


@router.get("/{question_id}", response_model=SrqDetailDto)
async def get_srq(
    project_id: str,
    question_id: str,
    current_user: UserDto = Depends(get_current_user),
    service: SrqService = Depends(get_srq_service),
):
    """Get a question with the student's marked answers."""
    return service.get_question(
        project_id=project_id, question_id=question_id, user_id=current_user.id
    )


@router.post("/{question_id}/mark", response_model=SrqAttemptDto)
async def mark_srq(
    project_id: str,
    question_id: str,
    request: SrqAnswer,
    current_user: UserDto = Depends(get_current_user),
    service: SrqService = Depends(get_srq_service),
):
    """Mark a written answer like an FBISE examiner (AI-estimated marks)."""
    return await service.mark(
        project_id=project_id,
        question_id=question_id,
        user_id=current_user.id,
        answer=request.answer,
    )
