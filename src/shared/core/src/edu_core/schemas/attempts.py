from datetime import datetime

from pydantic import BaseModel, Field


class QuizAnswerResultDto(BaseModel):
    question_id: str = Field(..., description="ID of the quiz question")
    chosen: str | None = Field(None, description="Option the student chose: a, b, c or d")
    correct_option: str = Field(..., description="The correct option")
    is_correct: bool = Field(..., description="Whether the student was right")


class QuizAttemptDto(BaseModel):
    """A finished attempt at a quiz."""

    id: str = Field(..., description="Unique ID of the attempt")
    quiz_id: str = Field(..., description="ID of the quiz")
    number: int = Field(1, description="Attempt number at this quiz: 1 for the first try")
    score: float = Field(..., description="Number of correct answers")
    max_score: float = Field(..., description="Number of questions")
    answers: list[QuizAnswerResultDto] = Field(..., description="Result per question")
    created_at: datetime = Field(..., description="When the attempt was submitted")


class AttemptSummaryDto(BaseModel):
    """The score of one attempt, for a list of earlier attempts."""

    id: str = Field(..., description="Unique ID of the attempt")
    number: int = Field(..., description="Attempt number: 1 for the first try")
    score: float = Field(..., description="Marks or correct answers")
    max_score: float = Field(..., description="Marks available")
    created_at: datetime = Field(..., description="When the attempt was submitted")


class QuizAttemptStateDto(BaseModel):
    attempt: QuizAttemptDto | None = Field(
        None, description="The latest attempt, or null if the quiz was not attempted yet"
    )
    history: list[AttemptSummaryDto] = Field(
        default_factory=list, description="Every attempt at this quiz, first to last"
    )


class FlashcardResultDto(BaseModel):
    flashcard_id: str = Field(..., description="ID of the flashcard")
    knew: bool = Field(..., description="Whether the student said they knew it")


class FlashcardAttemptDto(BaseModel):
    """A finished run through a flashcard set."""

    id: str = Field(..., description="Unique ID of the attempt")
    group_id: str = Field(..., description="ID of the flashcard set")
    number: int = Field(1, description="Run number through this set: 1 for the first")
    known: float = Field(..., description="Cards the student knew")
    total: float = Field(..., description="Cards rated")
    results: list[FlashcardResultDto] = Field(..., description="Result per card")
    created_at: datetime = Field(..., description="When the run was finished")


class FlashcardAttemptStateDto(BaseModel):
    attempt: FlashcardAttemptDto | None = Field(
        None, description="The latest run, or null if the set was not studied yet"
    )


class PracticeHistoryItemDto(BaseModel):
    """One finished attempt in the student's practice history."""

    id: str = Field(..., description="Unique ID of the attempt")
    kind: str = Field(..., description="quiz, flashcards or paper")
    ref_id: str = Field(..., description="ID of the quiz, flashcard set or paper")
    title: str = Field(..., description="Name of the quiz, flashcard set or paper")
    number: int = Field(..., description="Attempt number at this item: 1 for the first try")
    score: float = Field(..., description="Marks, correct answers or cards known")
    max_score: float = Field(..., description="Marks, questions or cards")
    created_at: datetime = Field(..., description="When the attempt was submitted")
