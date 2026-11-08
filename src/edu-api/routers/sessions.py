"""Weekly class sessions: the timetable, the teacher's dashboard, scheduling.

Three audiences, three gates. A student sees their own timetable and gets a
join link only while a class is open. A teacher sees the classes they are
taking. An administrator schedules them.

Scheduling is admin only, matching how the feature is meant to work: the
administrator arranges the week and names the teacher. A teacher cannot
create a class for themselves, so nothing lands on a student's timetable
without the person running the system putting it there.
"""

from datetime import datetime

from auth import get_current_user
from config import get_settings
from dependencies import get_class_session_service
from edu_core.exceptions import NotFoundError
from edu_core.schemas.sessions import (
    AdminSessionDto,
    AdminSessionListDto,
    SessionListDto,
    TeacherDashboardDto,
)
from edu_core.schemas.users import UserDto
from edu_core.services.class_sessions import ClassSessionService
from edu_core.weekly_session import SessionError
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])


def is_admin(user: UserDto) -> bool:
    return bool(user.email) and user.email.lower() in get_settings().admins


def require_admin(current_user: UserDto = Depends(get_current_user)) -> UserDto:
    # 404 rather than 403, as the admin router does: a signed-in student
    # guessing the URL learns nothing about what is behind it.
    if not is_admin(current_user):
        raise HTTPException(status_code=404, detail="Not found")
    return current_user


class SessionCreate(BaseModel):
    """What an administrator fills in. No group: the subject decides that."""

    title: str = Field(..., description="What students will see")
    description: str | None = Field(None, description="Optional detail")
    subject_code: str = Field(..., description="PHY, CHEM, BIO, MATH or CS")
    grade: int = Field(..., description="11 or 12")
    starts_at: datetime = Field(..., description="When it begins, in UTC")
    duration_minutes: int = Field(60, description="How long it runs")
    join_url: str = Field(..., description="The meeting link")
    teacher_id: str | None = Field(None, description="An account marked teacher")
    teacher_name: str | None = Field(
        None, description="Used when the teacher has not signed up yet"
    )


class RoleChange(BaseModel):
    role: str = Field(..., description="student or teacher")
    headline: str | None = Field(
        None, description="Shown under their name, e.g. 'MSc Physics'"
    )


@router.get("/mine", response_model=SessionListDto)
def my_timetable(
    current_user: UserDto = Depends(get_current_user),
    service: ClassSessionService = Depends(get_class_session_service),
):
    """The classes this student may attend."""
    return service.for_student(current_user.id)


@router.get("/teaching", response_model=TeacherDashboardDto)
def my_classes(
    current_user: UserDto = Depends(get_current_user),
    service: ClassSessionService = Depends(get_class_session_service),
):
    """The classes this teacher is taking.

    Open to any signed-in account rather than gated on the role: a student
    who calls it gets their own empty list, which is both true and harmless,
    and it means the page does not need to know the role before it can load.
    """
    try:
        return service.for_teacher(current_user.id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("", response_model=AdminSessionListDto)
def all_sessions(
    _: UserDto = Depends(require_admin),
    service: ClassSessionService = Depends(get_class_session_service),
):
    """Everything scheduled, with who can be put in front of a class."""
    return service.for_admin()


@router.post("", response_model=AdminSessionDto, status_code=201)
def schedule(
    body: SessionCreate,
    current_user: UserDto = Depends(require_admin),
    service: ClassSessionService = Depends(get_class_session_service),
):
    try:
        return service.create(
            created_by=current_user.id,
            title=body.title,
            description=body.description,
            subject_code=body.subject_code,
            grade=body.grade,
            starts_at=body.starts_at,
            duration_minutes=body.duration_minutes,
            join_url=body.join_url,
            teacher_id=body.teacher_id,
            teacher_name=body.teacher_name,
        )
    except SessionError as exc:
        # The message is written for the administrator to read and act on,
        # so it is passed through rather than replaced with "Bad request".
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{session_id}", status_code=204)
def cancel(
    session_id: str,
    _: UserDto = Depends(require_admin),
    service: ClassSessionService = Depends(get_class_session_service),
):
    """Call a class off. The record stays, marked cancelled."""
    try:
        service.cancel(session_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/teachers/{user_id}", status_code=204)
def set_role(
    user_id: str,
    body: RoleChange,
    _: UserDto = Depends(require_admin),
    service: ClassSessionService = Depends(get_class_session_service),
):
    """Make an account a teacher, or put it back to being a student."""
    try:
        service.set_role(user_id, body.role, body.headline)
    except SessionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
