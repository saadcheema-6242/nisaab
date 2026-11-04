from datetime import datetime

from pydantic import BaseModel, Field


class UserDto(BaseModel):
    id: str = Field(..., description="Unique ID of the user")
    name: str | None = Field(None, description="Name of the user")
    email: str | None = Field(None, description="Email of the user")
    created_at: datetime = Field(..., description="Date and time the user was created")
    updated_at: datetime = Field(..., description="Date and time the user was updated")

    # Suspension. Carried on the user every request already loads, so the one
    # place every signed-in call passes through can turn a banned account away
    # without a second query. Defaults keep every existing caller working.
    banned_at: datetime | None = Field(None, description="When a ban was applied")
    banned_until: datetime | None = Field(
        None, description="When the ban lifts; null while banned means permanent"
    )
    ban_reason: str | None = Field(None, description="Why the account was suspended")

    model_config = {"from_attributes": True}
