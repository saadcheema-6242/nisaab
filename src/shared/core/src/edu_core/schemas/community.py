from datetime import datetime

from pydantic import BaseModel, Field


class CommunityAttachmentDto(BaseModel):
    """A photo, voice note or file on a post, as the page needs it."""

    id: str = Field(..., description="ID of the attachment")
    kind: str = Field(..., description="image, audio or file")
    filename: str = Field(..., description="What the student called it")
    content_type: str = Field(..., description="The media type")
    size_bytes: int = Field(..., description="How big it is")
    duration_seconds: int | None = Field(
        None, description="How long a voice note runs"
    )
    url: str = Field(
        ...,
        description=(
            "A temporary link to the file. Signed and short lived, so the "
            "bucket stays private and a link cannot be passed on."
        ),
    )
    download_url: str = Field(
        ..., description="The same file, as a download rather than inline"
    )


class CommunityPollOptionDto(BaseModel):
    """One answer in a poll, with how it is doing."""

    id: str = Field(..., description="ID of the option")
    text: str = Field(..., description="The option")
    votes: int = Field(0, description="How many picked it")
    percent: int = Field(0, description="Share of the vote; these total 100")
    is_mine: bool = Field(False, description="Whether the reader picked it")
    is_winning: bool = Field(
        False, description="Whether it leads. Several can, on a tie."
    )


class CommunityPollDto(BaseModel):
    """A poll: a post with options."""

    question: str = Field(..., description="What is being asked")
    options: list[CommunityPollOptionDto] = Field(default_factory=list)
    total_votes: int = Field(0, description="How many students have voted")
    has_voted: bool = Field(False, description="Whether the reader has voted")


class CommunityPostDto(BaseModel):
    """One message, as the people in the room see it."""

    id: str = Field(..., description="ID of the post")
    body: str = Field(..., description="What was written")
    author_name: str = Field(..., description="Who wrote it, as they are known")
    author_role: str | None = Field(
        None,
        description=(
            "'admin' or 'teacher' when the author is one, else null. A "
            "badge beside the real name rather than a replacement for it: "
            "renaming the author to 'Admin' would hide who actually posted, "
            "and any student could then call themselves that."
        ),
    )
    is_mine: bool = Field(False, description="Whether the reader wrote it")
    created_at: datetime = Field(..., description="When it was posted")
    attachments: list[CommunityAttachmentDto] = Field(default_factory=list)
    poll: CommunityPollDto | None = Field(
        None, description="Set when this post is a poll"
    )
    reported_by_me: bool = Field(
        False, description="Whether the reader has already reported it"
    )
    # Deliberately not here: the model's verdict, the report count, and who
    # reported it. A room that shows its own moderation turns into an
    # argument about the moderation, and a student who can see that a post
    # was flagged can work out what gets flagged.
    replies: list["CommunityPostDto"] = Field(
        default_factory=list,
        description="Replies to this post, oldest first. One level only.",
    )


class CommunityWarningDto(BaseModel):
    """Something a teacher needs the author to read.

    Shown once, to the author alone. Nobody else in the room is told that a
    post was warned about.
    """

    post_id: str = Field(..., description="The post it is about")
    message: str = Field(..., description="What the student is told")
    created_at: datetime = Field(..., description="When it was sent")
    is_support: bool = Field(
        False,
        description=(
            "True when this is an offer of help rather than a warning, so "
            "the page can show it gently instead of as a telling-off."
        ),
    )


class CommunityRoomDto(BaseModel):
    """The room a student belongs to, and what has been said in it.

    A room is a grade and a group together - Pre-Medical XI is not the same
    room as Pre-Engineering XI - because that pair decides which papers a
    student actually sits, and so what is worth talking about.
    """

    grade: int = Field(..., description="11 or 12")
    group_code: str = Field(..., description="PRE_MED, PRE_ENG or ICS")
    room_name: str = Field(..., description="What the room is called, e.g. Pre-Medical XI")
    member_count: int = Field(0, description="Students in this grade and group")
    posts: list[CommunityPostDto] = Field(
        default_factory=list, description="Newest first, each with its replies"
    )
    posts_left_today: int = Field(
        0, description="How many more the reader may write today"
    )
    warnings: list[CommunityWarningDto] = Field(
        default_factory=list,
        description="Unread messages from moderation, for the reader only",
    )


# ---- what an administrator sees -------------------------------------------


class ModerationReportDto(BaseModel):
    """One student saying a post needs looking at."""

    reporter_name: str = Field(..., description="Who reported it")
    reason: str | None = Field(None, description="Which reason they picked")
    note: str | None = Field(None, description="Anything they added")
    created_at: datetime = Field(..., description="When")


class ModerationItemDto(BaseModel):
    """A post waiting for an administrator, with everything needed to judge it."""

    post_id: str = Field(..., description="ID of the post")
    body: str = Field(..., description="What was written, in full")
    room_name: str = Field(..., description="Which room it is in")
    grade: int = Field(..., description="11 or 12")
    group_code: str = Field(..., description="PRE_MED, PRE_ENG or ICS")
    author_id: str = Field(..., description="Who wrote it")
    author_name: str = Field(..., description="Their name")
    author_email: str | None = Field(
        None, description="Shown to an administrator only, never in the room"
    )
    created_at: datetime = Field(..., description="When it was posted")

    finding: str | None = Field(
        None,
        description=(
            "What the model made of it, or null if it was never reviewed. "
            "Null is not the same as clean."
        ),
    )
    finding_label: str = Field("", description="The finding in plain words")
    confidence: float | None = Field(None, description="How sure the model was")
    why: str | None = Field(None, description="The model's one line of reasoning")
    severity: int = Field(0, description="How soon an adult should look. Higher first.")
    is_urgent: bool = Field(
        False, description="Distress, a threat or sexual content: look today"
    )

    report_count: int = Field(0, description="How many students reported it")
    reports: list[ModerationReportDto] = Field(default_factory=list)

    warned_at: datetime | None = Field(None, description="When the author was told")
    reviewed_at: datetime | None = Field(
        None, description="When an administrator cleared it, if they have"
    )
    attachment_count: int = Field(0, description="How many files are on it")


class ModerationQueueDto(BaseModel):
    """Everything an administrator needs to look at, worst first."""

    items: list[ModerationItemDto] = Field(default_factory=list)
    urgent_count: int = Field(0, description="How many need attention today")
    flagged_count: int = Field(0, description="How many the model flagged")
    reported_count: int = Field(0, description="How many students reported")
    unreviewed_count: int = Field(
        0, description="Never looked at by the model, which is not the same as clean"
    )
