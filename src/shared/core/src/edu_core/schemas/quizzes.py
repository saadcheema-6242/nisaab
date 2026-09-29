from datetime import datetime

from pydantic import BaseModel, Field


class QuizDto(BaseModel):
    model_config = {"from_attributes": True}

    id: str = Field(..., description="Unique ID of the quiz")
    project_id: str = Field(..., description="ID of the project the quiz belongs to")
    name: str = Field(..., description="Name of the quiz")
    description: str | None = Field(None, description="Description of the quiz")
    slo_code: str | None = Field(None, description="FBISE SLO code, e.g. P-11-B-05")
    created_at: datetime = Field(..., description="Date and time the quiz was created")
    updated_at: datetime = Field(..., description="Date and time the quiz was updated")


class QuizQuestionDto(BaseModel):
    """Quiz question data transfer object."""

    model_config = {"from_attributes": True}

    id: str = Field(..., description="Unique ID of the quiz question")
    quiz_id: str = Field(..., description="ID of the quiz this question belongs to")
    project_id: str = Field(..., description="ID of the project")
    question_text: str = Field(..., description="The quiz question text")
    option_a: str = Field(..., description="Option A")
    option_b: str = Field(..., description="Option B")
    option_c: str = Field(..., description="Option C")
    option_d: str = Field(..., description="Option D")
    correct_option: str = Field(..., description="Correct option: a, b, c, or d")
    explanation: str | None = Field(
        None, description="Explanation for the correct answer"
    )
    difficulty_level: str = Field(
        ..., description="Difficulty level: easy, medium, or hard"
    )
    position: int = Field(..., description="Position for ordering within quiz")
    slo_code: str | None = Field(None, description="FBISE SLO code, e.g. P-11-B-05")
    cognitive_level: str | None = Field(
        None, description="Cognitive level: K, U or A"
    )
    created_at: datetime = Field(
        ..., description="Date and time the question was created"
    )
