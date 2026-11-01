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
    image_path: str | None = Field(
        None, description="Where the diagram lives in the bucket; signed before use"
    )
    image_alt: str | None = Field(
        None, description="What the question's diagram shows, if it has one"
    )
    image_url: str | None = Field(
        None,
        description=(
            "A temporary link to the question's diagram. Signed when the "
            "question is read, so it is absent on a question without one."
        ),
    )
    image_credit: dict | None = Field(
        None,
        description=(
            "Who the diagram belongs to: author, licence, licence_url, "
            "source_url, source and a ready-made line. Present when the "
            "diagram came from an openly licensed source, and shown with it "
            "wherever it appears, because naming them is a condition of the "
            "licence."
        ),
    )
    option_images: dict | None = Field(
        None,
        description='Stored pictures for the options, as {"a": {path, alt, credit}}',
    )
    option_image_urls: dict | None = Field(
        None,
        description=(
            "Temporary links to the pictures on the options, as {a: url}. "
            "Present only on a question whose options are pictures to choose "
            "between."
        ),
    )
    position: int = Field(..., description="Position for ordering within quiz")
    slo_code: str | None = Field(None, description="FBISE SLO code, e.g. P-11-B-05")
    cognitive_level: str | None = Field(
        None, description="Cognitive level: K, U or A"
    )
    created_at: datetime = Field(
        ..., description="Date and time the question was created"
    )
