from datetime import datetime

from pydantic import BaseModel, Field


class CommunityPostDto(BaseModel):
    """One message, as the people in the room see it."""

    id: str = Field(..., description="ID of the post")
    body: str = Field(..., description="What was written")
    author_name: str = Field(..., description="Who wrote it, as they are known")
    is_mine: bool = Field(False, description="Whether the reader wrote it")
    created_at: datetime = Field(..., description="When it was posted")
    replies: list["CommunityPostDto"] = Field(
        default_factory=list,
        description="Replies to this post, oldest first. One level only.",
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
