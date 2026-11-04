from datetime import datetime

from pydantic import BaseModel, Field


class AdminUsageDto(BaseModel):
    """What this account has spent today, against what it is allowed."""

    chat_messages: int = 0
    flashcard_generations: int = 0
    quiz_generations: int = 0
    mindmap_generations: int = 0
    document_uploads: int = 0
    last_reset: datetime | None = Field(
        None, description="When the daily counters were last cleared"
    )


class AdminUserDto(BaseModel):
    """One account, as it appears in the administrator's list."""

    id: str
    name: str | None = None
    email: str | None = None
    created_at: datetime
    grade: int | None = Field(None, description="11 or 12, once onboarded")
    group_code: str | None = Field(None, description="PRE_MED, PRE_ENG or ICS")
    language: str | None = Field(None, description="en, ur or ur-Latn")
    onboarded: bool = False
    ban_state: str = Field("active", description="active, temporary or permanent")
    banned_until: datetime | None = None
    ban_reason: str | None = None
    banned_by: str | None = None
    usage: AdminUsageDto = Field(default_factory=AdminUsageDto)
    # A single number for "is this account actually being used", so the list
    # can be read without opening every row
    practice_answers: int = 0


class AdminUserDetailDto(AdminUserDto):
    """One account with everything it owns, counted.

    Counts rather than contents. An administrator needs to know how much there
    is before deleting it; reading a student's chats is a different decision
    and is not what this screen is for.
    """

    projects: int = 0
    chats: int = 0
    messages: int = 0
    documents: int = 0
    quizzes: int = 0
    flashcard_groups: int = 0
    notes: int = 0
    mind_maps: int = 0
    papers: int = 0
    study_plans: int = 0
    srq_attempts: int = 0
    community_posts: int = 0
    subjects: list[str] = Field(
        default_factory=list, description="Workspace names, e.g. Physics XI"
    )


class AdminOverviewDto(BaseModel):
    """The numbers worth seeing before reading any single account."""

    total_users: int = 0
    onboarded_users: int = 0
    banned_users: int = 0
    active_today: int = Field(0, description="Accounts that used something today")
    by_group: dict[str, int] = Field(
        default_factory=dict, description="How many students in each group"
    )
    by_grade: dict[str, int] = Field(default_factory=dict)
    practice_answers: int = Field(0, description="Questions answered, all users")


class AdminUserListDto(BaseModel):
    overview: AdminOverviewDto
    users: list[AdminUserDto] = Field(default_factory=list)
    total: int = Field(0, description="Accounts matching the search")


class DeletionReportDto(BaseModel):
    """What was actually removed, so the administrator sees the consequence."""

    user_id: str
    email: str | None = None
    deleted: dict[str, int] = Field(
        default_factory=dict, description="Rows removed, per kind"
    )
    note: str = Field("", description="Anything the administrator must still do")
