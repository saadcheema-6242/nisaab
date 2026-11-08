"""Teacher accounts, as the pages need them."""

from datetime import datetime

from pydantic import BaseModel, Field


class TeacherProfileDto(BaseModel):
    """What a teacher said they teach."""

    subjects: list[str] = Field(..., description="Subject codes, e.g. PHY")
    grades: list[int] = Field(..., description="11, 12, or both")
    school: str | None = None
    about: str | None = None
    applied_at: datetime | None = None


class TeacherAccountDto(BaseModel):
    id: str
    name: str
    email: str | None = None
    headline: str | None = None
    approved: bool = Field(
        ...,
        description=(
            "True only when the role is teacher AND an administrator has "
            "approved it. Anything that reads the role alone is a hole: "
            "anyone can tick 'teacher' at signup."
        ),
    )
    approved_at: datetime | None = None
    profile: TeacherProfileDto | None = None


class TeacherQueueDto(BaseModel):
    """The administrator's view: who is waiting, and who is already in."""

    waiting: list[TeacherAccountDto] = Field(..., description="Oldest application first")
    approved: list[TeacherAccountDto]


class AccountStateDto(BaseModel):
    """Everything the app needs to decide where to send someone.

    One call, answered before any page loads. Splitting it would mean the
    router asking three questions and guessing while it waited, which is how
    a signed-in teacher briefly sees a student dashboard.
    """

    role: str = Field(..., description="student or teacher")
    is_admin: bool = Field(..., description="On the ADMIN_EMAILS list")
    onboarded: bool = Field(..., description="Has a student profile")
    teacher_approved: bool
    # Where this account must go before it can use the app, or null.
    send_to: str | None = Field(
        None, description="/onboarding, /awaiting-approval, or null"
    )
    teacher: TeacherAccountDto | None = None
