"""Teacher accounts: applying, waiting, and being approved.

The gate is the point of this file. Anybody can sign up and say they teach
Physics, so the claim buys nothing until an administrator agrees. Every
route here either asks for approval, grants it, or reports whether it has
been granted; nothing serves a teacher's own data without checking.
"""

from auth import get_current_user
from config import get_settings
from dependencies import get_profile_service, get_teacher_service
from edu_core.exceptions import NotFoundError
from edu_core.roles import RoleError, is_approved_teacher
from edu_core.roles import needs_onboarding as where_to_send
from edu_core.schemas.teachers import (
    AccountStateDto,
    TeacherAccountDto,
    TeacherQueueDto,
)
from edu_core.schemas.users import UserDto
from edu_core.services import ProfileService
from edu_core.services.teachers import TeacherService
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1/teachers", tags=["teachers"])


def is_admin(user: UserDto) -> bool:
    return bool(user.email) and user.email.lower() in get_settings().admins


def require_admin(current_user: UserDto = Depends(get_current_user)) -> UserDto:
    if not is_admin(current_user):
        raise HTTPException(status_code=404, detail="Not found")
    return current_user


class TeacherApplication(BaseModel):
    subjects: list[str] = Field(..., description="Subject codes they teach")
    grades: list[int] = Field(..., description="11, 12 or both")
    school: str | None = Field(None, description="Where they teach")
    headline: str | None = Field(None, description="Shown under their name")
    about: str | None = Field(None, description="In their own words")


class Decision(BaseModel):
    approve: bool = Field(..., description="False puts them back to student")


@router.get("/me", response_model=AccountStateDto)
def my_account(
    current_user: UserDto = Depends(get_current_user),
    teachers: TeacherService = Depends(get_teacher_service),
    profiles: ProfileService = Depends(get_profile_service),
):
    """Who this account is, and where it must go before using the app.

    Answered in one call because the router has to decide before any page
    renders. Asking separately would mean guessing while the answers
    arrived, which is how a teacher awaiting approval gets a glimpse of a
    student dashboard on the way to the waiting page.
    """
    try:
        account = teachers.get_account(current_user.id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    state = profiles.get_profile_state(user_id=current_user.id)
    admin = is_admin(current_user)
    role = "teacher" if account.profile or account.approved else "student"
    approved = account.approved

    return AccountStateDto(
        role=role,
        is_admin=admin,
        onboarded=state.onboarded,
        teacher_approved=approved,
        send_to=where_to_send(
            role=role,
            is_admin=admin,
            has_profile=state.onboarded,
            approved_at=account.approved_at,
        ),
        teacher=account if role == "teacher" else None,
    )


@router.post("/apply", response_model=TeacherAccountDto)
def apply(
    body: TeacherApplication,
    current_user: UserDto = Depends(get_current_user),
    service: TeacherService = Depends(get_teacher_service),
):
    """Finish signing up as a teacher. Grants nothing until approved."""
    try:
        return service.apply(
            user_id=current_user.id,
            subjects=body.subjects,
            grades=body.grades,
            school=body.school,
            headline=body.headline,
            about=body.about,
        )
    except RoleError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/withdraw", status_code=204)
def withdraw(
    current_user: UserDto = Depends(get_current_user),
    service: TeacherService = Depends(get_teacher_service),
):
    """Go back to being a student.

    The way off the waiting page. Without it, one mistaken tap on "Teacher"
    leaves an account unable to use NISAAB at all until somebody notices.
    """
    try:
        service.withdraw(current_user.id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/queue", response_model=TeacherQueueDto)
def queue(
    _: UserDto = Depends(require_admin),
    service: TeacherService = Depends(get_teacher_service),
):
    """Teachers waiting for approval, and those already approved."""
    return service.queue()


@router.put("/{user_id}/decision", response_model=TeacherAccountDto)
def decide(
    user_id: str,
    body: Decision,
    current_user: UserDto = Depends(require_admin),
    service: TeacherService = Depends(get_teacher_service),
):
    """Approve a teacher, or put them back to being a student."""
    try:
        return service.decide(
            user_id=user_id, approve=body.approve, by=current_user.id
        )
    except RoleError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


__all__ = ["router", "is_approved_teacher"]
