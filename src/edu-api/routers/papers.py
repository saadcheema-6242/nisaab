"""Router for FBISE-style practice papers."""

from auth import get_current_user
from dependencies import get_paper_service, get_usage_service
from edu_core.schemas.papers import PaperDto, PaperSummaryDto
from edu_core.schemas.users import UserDto
from edu_core.services import PaperService, UsageService
from fastapi import APIRouter, Depends

from routers.schemas import PaperAnswers, PaperCreate

router = APIRouter(prefix="/api/v1/projects/{project_id}/papers", tags=["papers"])


@router.post("", response_model=PaperDto, status_code=201)
async def create_paper(
    project_id: str,
    request: PaperCreate,
    current_user: UserDto = Depends(get_current_user),
    service: PaperService = Depends(get_paper_service),
    usage_service: UsageService = Depends(get_usage_service),
):
    """Assemble a practice paper (takes a few seconds)."""
    usage_service.check_and_increment(current_user.id, "quiz_generation")
    return await service.create(
        project_id=project_id,
        user_id=current_user.id,
        length=request.length,
        topic=request.topic,
    )


@router.get("", response_model=list[PaperSummaryDto])
async def list_papers(
    project_id: str,
    current_user: UserDto = Depends(get_current_user),
    service: PaperService = Depends(get_paper_service),
):
    """The student's practice papers in this workspace, newest first."""
    return service.list_papers(project_id=project_id, user_id=current_user.id)


@router.get("/{paper_id}", response_model=PaperDto)
async def get_paper(
    paper_id: str,
    current_user: UserDto = Depends(get_current_user),
    service: PaperService = Depends(get_paper_service),
):
    """A paper; marks and model answers are included once it is submitted."""
    return service.get(paper_id=paper_id, user_id=current_user.id)


@router.put("/{paper_id}/answers", status_code=204)
async def save_paper_answers(
    paper_id: str,
    request: PaperAnswers,
    current_user: UserDto = Depends(get_current_user),
    service: PaperService = Depends(get_paper_service),
):
    """Save answers while the student works."""
    service.save_answers(paper_id=paper_id, user_id=current_user.id, answers=request.answers)


@router.post("/{paper_id}/submit", response_model=PaperDto)
async def submit_paper(
    paper_id: str,
    request: PaperAnswers,
    current_user: UserDto = Depends(get_current_user),
    service: PaperService = Depends(get_paper_service),
):
    """Submit and mark the paper (written answers are AI-estimated, like an examiner)."""
    return await service.submit(
        paper_id=paper_id, user_id=current_user.id, answers=request.answers
    )
