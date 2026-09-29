from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class SloExplainerDto(BaseModel):
    slo_code: str = Field(..., description="FBISE SLO code")
    title: str = Field(..., description="Explainer title")
    content: str = Field(..., description="Explainer in Markdown with LaTeX")
    reviewed: bool = Field(..., description="True once a subject teacher approved it")


class SloExplainerStateDto(BaseModel):
    explainer: SloExplainerDto | None = Field(
        None, description="The explainer, or null if none has been written yet"
    )


class ContentItemDto(BaseModel):
    """A shared content item for one SLO, as shown in the review queue."""

    id: str = Field(..., description="Unique ID of the item")
    grade_subject_id: str = Field(..., description="ID of the grade subject")
    slo_code: str = Field(..., description="FBISE SLO code")
    slo_description: str = Field("", description="SLO text")
    kind: Literal["explainer", "mcq", "srq"] = Field(..., description="Type of item")
    payload: dict[str, Any] = Field(
        ...,
        description=(
            "explainer: {title, content}; mcq: {question_text, option_a..option_d, "
            "correct_option, explanation, cognitive_level}; srq: {question, marks, "
            "model_answer, rubric}"
        ),
    )
    review_status: Literal["draft", "approved", "rejected"] = Field(..., description="Review status")
    review_note: str | None = Field(None, description="Reviewer's note")
    reviewed_by: str | None = Field(None, description="Reviewer's email")
    created_at: datetime = Field(..., description="When the item was generated")


class ContentSummaryDto(BaseModel):
    kind: str = Field(..., description="explainer, mcq or srq")
    review_status: str = Field(..., description="draft, approved or rejected")
    count: int = Field(..., description="Number of items")


class ReviewerStateDto(BaseModel):
    is_reviewer: bool = Field(..., description="True if this user may review content")
