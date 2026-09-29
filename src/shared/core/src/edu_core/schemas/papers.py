from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from edu_core.schemas.srq import SrqAttemptDto


class PaperItemDto(BaseModel):
    id: str = Field(..., description="ID of the item within the paper (SRQ/ERQ: the question ID)")
    type: Literal["mcq", "srq", "erq"] = Field(..., description="MCQ, short or long question")
    marks: float = Field(..., description="Marks for this item")
    slo_code: str | None = Field(None, description="FBISE SLO the item assesses")
    cognitive_level: str | None = Field(None, description="K, U or A")
    question: str = Field(..., description="Question text (Markdown with LaTeX)")
    options: dict[str, str] | None = Field(None, description="MCQ options a-d")


class PaperSectionDto(BaseModel):
    id: str = Field(..., description="A, B or C")
    title: str = Field(..., description="Section title")
    items: list[PaperItemDto]


class PaperItemResultDto(BaseModel):
    id: str = Field(..., description="ID of the item")
    type: Literal["mcq", "srq", "erq"]
    marks: float = Field(..., description="Marks available")
    awarded: float = Field(..., description="Marks awarded (AI-estimated for written answers)")
    chosen: str | None = Field(None, description="MCQ: the option chosen")
    correct_option: str | None = Field(None, description="MCQ: the correct option")
    explanation: str | None = Field(None, description="MCQ: why the answer is right")
    answer: str | None = Field(None, description="Written: the student's answer")
    marking: SrqAttemptDto | None = Field(None, description="Written: marks per rubric point")
    model_answer: str | None = Field(None, description="Written: a full-marks answer")


class PaperSectionResultDto(BaseModel):
    id: str
    title: str
    score: float
    max_score: float


class PaperResultDto(BaseModel):
    score: float = Field(..., description="Total marks awarded")
    max_score: float = Field(..., description="Total marks")
    percent: int = Field(..., description="Score as a percentage")
    grade: str = Field(..., description="IBCC grade band for this paper")
    descriptor: str = Field(..., description="Band descriptor")
    sections: list[PaperSectionResultDto]
    items: list[PaperItemResultDto]


class PaperDto(BaseModel):
    """A practice paper; answers and marking appear once it is submitted."""

    id: str = Field(..., description="Unique ID of the paper")
    project_id: str = Field(..., description="ID of the subject workspace")
    title: str = Field(..., description="Paper title")
    length: Literal["mini", "standard"] = Field(..., description="Paper length")
    time_limit_minutes: int = Field(..., description="Time allowed")
    total_marks: float = Field(..., description="Total marks")
    status: Literal["ready", "submitted"] = Field(..., description="ready or submitted")
    sections: list[PaperSectionDto]
    answers: dict[str, str] = Field(default_factory=dict, description="Saved answers by item ID")
    result: PaperResultDto | None = Field(None, description="Marks, once submitted")
    created_at: datetime
    submitted_at: datetime | None = None


class PaperSummaryDto(BaseModel):
    id: str
    title: str
    length: Literal["mini", "standard"]
    status: Literal["ready", "submitted"]
    total_marks: float
    score: float | None = None
    created_at: datetime
