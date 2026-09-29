from datetime import datetime

from pydantic import BaseModel, Field


class RubricPointDto(BaseModel):
    point: str = Field(..., description="What the answer must contain for these marks")
    marks: float = Field(..., description="Marks for this point")


class SrqQuestionDto(BaseModel):
    """A short-response question; the rubric and model answer are shown after marking."""

    id: str = Field(..., description="Unique ID of the question")
    project_id: str = Field(..., description="ID of the project")
    slo_code: str | None = Field(None, description="FBISE SLO code, e.g. P-11-B-05")
    question: str = Field(..., description="Question text (Markdown with LaTeX)")
    marks: int = Field(..., description="Total marks")
    cognitive_level: str | None = Field(None, description="K, U or A")
    created_at: datetime = Field(..., description="When the question was created")


class SrqPointResultDto(BaseModel):
    point: str = Field(..., description="The rubric point")
    marks: float = Field(..., description="Marks available for this point")
    awarded: float = Field(..., description="Marks awarded")
    comment: str = Field("", description="What the student wrote or missed")


class SrqAttemptDto(BaseModel):
    """A marked written answer. Marks are AI-estimated."""

    id: str = Field(..., description="Unique ID of the attempt")
    question_id: str = Field(..., description="ID of the question")
    answer: str = Field(..., description="The student's answer")
    awarded_marks: float = Field(..., description="AI-estimated marks")
    max_marks: int = Field(..., description="Total marks")
    points: list[SrqPointResultDto] = Field(..., description="Marks per rubric point")
    feedback: str = Field("", description="How to get full marks")
    missing: list[str] = Field(default_factory=list, description="Rubric points not fully earned")
    model_answer: str = Field(..., description="A full-marks answer")
    created_at: datetime = Field(..., description="When the answer was marked")


class SrqDetailDto(BaseModel):
    question: SrqQuestionDto
    attempts: list[SrqAttemptDto] = Field(..., description="The student's attempts, newest first")
