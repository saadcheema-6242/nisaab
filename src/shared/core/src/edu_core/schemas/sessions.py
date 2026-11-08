"""What a weekly class session looks like to each of the three audiences.

An administrator sees everything, including the link, at all times, because
they have to check it. A teacher sees their own, with the link, because they
have to start the class. A student sees theirs with the link withheld until
the class is nearly due.

Three DTOs rather than one with optional fields, so the rule is in the type
rather than in whoever remembers to blank the column.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class TeacherDto(BaseModel):
    """A teacher as a student sees them on the card."""

    id: str | None = Field(None, description="Their account, once they have one")
    name: str = Field(..., description="The name shown on the session")
    headline: str | None = Field(
        None, description="A short line of credentials, shown under the name"
    )


class StudentSessionDto(BaseModel):
    """A session on a student's timetable."""

    id: str
    title: str
    description: str | None = None
    subject_code: str = Field(..., description="PHY, CHEM, BIO, MATH or CS")
    subject_name: str
    grade: int
    teacher: TeacherDto | None = None
    starts_at: datetime
    duration_minutes: int
    when: str = Field(
        ..., description="How a student would say it: 'Today at 5:00 pm'"
    )
    state: str = Field(..., description="upcoming, open or ended")
    join_url: str | None = Field(
        None,
        description=(
            "Only present while the session is open, from fifteen minutes "
            "before it starts until it ends. Withheld at every other moment, "
            "so a link cannot be collected days early and passed on."
        ),
    )


class TeacherSessionDto(BaseModel):
    """A session on a teacher's own dashboard. The link is always present."""

    id: str
    title: str
    description: str | None = None
    subject_code: str
    subject_name: str
    grade: int
    starts_at: datetime
    duration_minutes: int
    when: str
    state: str
    join_url: str | None = None
    groups: list[str] = Field(
        ..., description="Which groups this class serves, for the teacher to see"
    )


class AdminSessionDto(BaseModel):
    """A session as the person who scheduled it sees it."""

    id: str
    title: str
    description: str | None = None
    subject_code: str
    subject_name: str
    grade: int
    teacher: TeacherDto | None = None
    starts_at: datetime
    duration_minutes: int
    when: str
    state: str
    join_url: str | None = None
    meeting_source: str
    groups: list[str]
    cancelled_at: datetime | None = None


class TeacherOptionDto(BaseModel):
    """A teacher an administrator can assign to a class."""

    id: str
    name: str
    email: str | None = None
    headline: str | None = None


class SessionListDto(BaseModel):
    sessions: list[StudentSessionDto]


class TeacherDashboardDto(BaseModel):
    """Everything the teacher's page needs in one call."""

    teacher: TeacherDto
    next_session: TeacherSessionDto | None = None
    sessions: list[TeacherSessionDto]


class AdminSessionListDto(BaseModel):
    sessions: list[AdminSessionDto]
    teachers: list[TeacherOptionDto] = Field(
        ..., description="Who can be put in front of a class"
    )
