"""Router for the FBISE curriculum (syllabus map)."""

from auth import get_current_user
from dependencies import get_content_service, get_curriculum_service
from edu_core.schemas.content import SloExplainerStateDto
from edu_core.schemas.curriculum import CurriculumTreeDto, GradeSubjectDto, SloDto
from edu_core.schemas.users import UserDto
from edu_core.services import ContentService, CurriculumService
from fastapi import APIRouter, Depends, Query

router = APIRouter(prefix="/api/v1/curriculum", tags=["curriculum"])


@router.get("/grade-subjects", response_model=list[GradeSubjectDto])
async def list_grade_subjects(
    grade: int | None = Query(None, description="Only this grade (11 or 12)"),
    current_user: UserDto = Depends(get_current_user),
    service: CurriculumService = Depends(get_curriculum_service),
):
    """List FSc subjects per grade and whether their SLOs are available."""
    return service.list_grade_subjects(grade=grade)


@router.get("/grade-subjects/{grade_subject_id}/tree", response_model=CurriculumTreeDto)
async def get_curriculum_tree(
    grade_subject_id: str,
    current_user: UserDto = Depends(get_current_user),
    service: CurriculumService = Depends(get_curriculum_service),
):
    """Get the syllabus map: domains and SLOs with the student's mastery."""
    return service.get_tree(grade_subject_id=grade_subject_id, user_id=current_user.id)


@router.get("/slos/{code}", response_model=SloDto)
async def get_slo(
    code: str,
    grade_subject_id: str | None = Query(None, description="Limit to one grade subject"),
    current_user: UserDto = Depends(get_current_user),
    service: CurriculumService = Depends(get_curriculum_service),
):
    """Get one SLO by its FBISE code, e.g. P-11-B-05."""
    return service.get_slo(
        code=code, user_id=current_user.id, grade_subject_id=grade_subject_id
    )


@router.get(
    "/grade-subjects/{grade_subject_id}/slos/{code}/explainer",
    response_model=SloExplainerStateDto,
)
async def get_slo_explainer(
    grade_subject_id: str,
    code: str,
    current_user: UserDto = Depends(get_current_user),
    service: ContentService = Depends(get_content_service),
):
    """The prepared explainer for an SLO, if one has been written."""
    return SloExplainerStateDto(explainer=service.get_explainer(grade_subject_id, code))
