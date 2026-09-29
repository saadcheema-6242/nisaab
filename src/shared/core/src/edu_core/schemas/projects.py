from datetime import datetime

from pydantic import BaseModel, Field


class ProjectDto(BaseModel):
    model_config = {"from_attributes": True}

    id: str = Field(..., description="Unique ID of the project")
    owner_id: str = Field(..., description="ID of the user who owns the project")
    name: str = Field(..., description="Name of the project")
    description: str | None = Field(None, description="Description of the project")
    language_code: str = Field(
        ..., description="Language code for the project: en, ur or ur-Latn (Roman Urdu)"
    )
    kind: str = Field(
        "custom",
        description="subject_workspace (one FBISE subject, created by onboarding) or custom",
    )
    grade_subject_id: str | None = Field(
        None, description="ID of the FBISE grade subject of a subject workspace"
    )
    subject_code: str | None = Field(
        None, description="Subject code of a subject workspace: PHY, CHEM, BIO or MATH"
    )
    created_at: datetime = Field(
        ..., description="Date and time the project was created"
    )
