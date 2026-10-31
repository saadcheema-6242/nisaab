"""Router for quiz CRUD operations."""

from collections.abc import AsyncGenerator

from auth import get_current_user
from config import get_settings
from dependencies import get_storage
from dependencies import (
    get_attempt_service,
    get_quiz_service,
    get_usage_service,
)
from edu_core.schemas.attempts import QuizAttemptDto, QuizAttemptStateDto
from edu_core.exceptions import NotFoundError
from edu_core.schemas.quizzes import QuizDto, QuizQuestionDto
from edu_core.schemas.users import UserDto
from edu_core.services import AttemptService, QuizService, UsageService
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from routers.schemas import (
    GenerateRequest,
    QuizAttemptCreate,
    QuizCreate,
    QuizQuestionCreate,
    QuizQuestionReorder,
    QuizQuestionUpdate,
    QuizUpdate,
)

router = APIRouter(prefix="/api/v1/projects/{project_id}/quizzes", tags=["quizzes"])


@router.post("", response_model=QuizDto, status_code=201)
async def create_quiz(
    project_id: str,
    quiz: QuizCreate,
    current_user: UserDto = Depends(get_current_user),
    service: QuizService = Depends(get_quiz_service),
):
    """Create a new quiz."""
    try:
        return service.create_quiz(
            project_id=project_id,
            name=quiz.name,
            description=quiz.description,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{quiz_id}", response_model=QuizDto)
async def get_quiz(
    project_id: str,
    quiz_id: str,
    current_user: UserDto = Depends(get_current_user),
    service: QuizService = Depends(get_quiz_service),
):
    """Get a quiz by ID."""
    try:
        return service.get_quiz(quiz_id=quiz_id, project_id=project_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=list[QuizDto])
async def list_quizzes(
    project_id: str,
    current_user: UserDto = Depends(get_current_user),
    service: QuizService = Depends(get_quiz_service),
):
    """List all quizzes for a project."""
    try:
        return service.list_quizzes(project_id=project_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{quiz_id}", response_model=QuizDto)
async def update_quiz(
    project_id: str,
    quiz_id: str,
    quiz: QuizUpdate,
    current_user: UserDto = Depends(get_current_user),
    service: QuizService = Depends(get_quiz_service),
):
    """Update a quiz."""
    try:
        return service.update_quiz(
            quiz_id=quiz_id,
            project_id=project_id,
            name=quiz.name,
            description=quiz.description,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{quiz_id}", status_code=204)
async def delete_quiz(
    project_id: str,
    quiz_id: str,
    current_user: UserDto = Depends(get_current_user),
    service: QuizService = Depends(get_quiz_service),
):
    """Delete a quiz."""
    try:
        service.delete_quiz(quiz_id=quiz_id, project_id=project_id)
        return None
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class GenerationProgressUpdate(BaseModel):
    """Progress update for generation streaming."""

    status: str = Field(..., description="Status: searching, generating, saving, done")
    message: str = Field(..., description="Progress message")
    error: str | None = Field(None, description="Error message if any")


@router.post("/{quiz_id}/generate", response_model=QuizDto)
async def generate_quiz(
    project_id: str,
    quiz_id: str,
    request: GenerateRequest,
    current_user: UserDto = Depends(get_current_user),
    service: QuizService = Depends(get_quiz_service),
    usage_service: UsageService = Depends(get_usage_service),
):
    """Queue quiz generation request to be processed by a worker."""
    # Check usage limit before processing
    usage_service.check_and_increment(current_user.id, "quiz_generation")
    try:
        return service.queue_generation(
            quiz_id=quiz_id,
            project_id=project_id,
            topic=request.topic,
            custom_instructions=request.custom_instructions,
            count=request.count,
            user_id=current_user.id,
            slo_code=request.slo_code,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{quiz_id}/generate/stream", status_code=200)
async def generate_quiz_stream(
    project_id: str,
    quiz_id: str,
    request: GenerateRequest,
    current_user: UserDto = Depends(get_current_user),
    service: QuizService = Depends(get_quiz_service),
    usage_service: UsageService = Depends(get_usage_service),
):
    """Queue quiz generation request with streaming progress updates."""
    # Check usage limit before processing
    usage_service.check_and_increment(current_user.id, "quiz_generation")

    async def generate_stream() -> AsyncGenerator[bytes]:
        """Generate streaming progress updates"""
        try:
            # Queuing request
            progress = GenerationProgressUpdate(
                status="queuing", message="Queuing quiz generation request..."
            )
            yield f"data: {progress.model_dump_json()}\n\n".encode()

            service.queue_generation(
                quiz_id=quiz_id,
                project_id=project_id,
                topic=request.topic,
                custom_instructions=request.custom_instructions,
                count=request.count,
                user_id=current_user.id,
                slo_code=request.slo_code,
            )

            # Done (queued)
            progress = GenerationProgressUpdate(
                status="done", message="Quiz generation request queued successfully"
            )
            yield f"data: {progress.model_dump_json()}\n\n".encode()

        except NotFoundError as e:
            error_progress = GenerationProgressUpdate(
                status="done", message="Error queuing quiz generation", error=str(e)
            )
            yield f"data: {error_progress.model_dump_json()}\n\n".encode()
        except Exception as e:
            error_progress = GenerationProgressUpdate(
                status="done", message="Error queuing quiz generation", error=str(e)
            )
            yield f"data: {error_progress.model_dump_json()}\n\n".encode()

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
        },
    )


@router.get("/{quiz_id}/questions", response_model=list[QuizQuestionDto])
async def list_quiz_questions(
    project_id: str,
    quiz_id: str,
    current_user: UserDto = Depends(get_current_user),
    service: QuizService = Depends(get_quiz_service),
):
    """List all questions in a quiz."""
    try:
        return _with_image_urls(
            service.list_quiz_questions(quiz_id=quiz_id, project_id=project_id)
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _with_image_urls(questions: list[QuizQuestionDto]) -> list[QuizQuestionDto]:
    """Sign a temporary link for each question that carries a diagram.

    Signing costs a call to the IAM API, so it is only done for questions that
    actually have an image - which is most of them not at all. A diagram that
    cannot be signed is dropped rather than failing the whole request: the
    question still reads.
    """
    if not any(q.image_path or q.option_images for q in questions):
        return questions

    storage = get_storage()

    def sign(path: str) -> str | None:
        try:
            return storage.signed_url(path, expires_in=3600)
        except Exception:  # noqa: BLE001 - a missing picture must not break the quiz
            return None

    for question in questions:
        if question.image_path:
            question.image_url = sign(question.image_path)
        if question.option_images:
            links = {
                letter: url
                for letter, item in question.option_images.items()
                if isinstance(item, dict) and item.get("path")
                and (url := sign(item["path"]))
            }
            question.option_image_urls = links or None
    return questions


class GoogleFormDto(BaseModel):
    """Where a quiz published as a Google Form can be opened."""

    form_id: str = Field(..., description="Google's ID for the form")
    responder_url: str = Field(..., description="The link to share; anyone may attempt it")
    edit_url: str = Field(..., description="Where the form can be edited or deleted")


@router.post("/{quiz_id}/google-form", response_model=GoogleFormDto)
async def publish_quiz_as_google_form(
    project_id: str,
    quiz_id: str,
    current_user: UserDto = Depends(get_current_user),
    service: QuizService = Depends(get_quiz_service),
):
    """Publish this quiz as a shareable Google Form quiz.

    The form carries the answer key and the explanations, so whoever attempts it
    sees their score and what they got wrong on the form itself. Nothing comes
    back here.
    """
    from edu_core.services.google_forms import (
        FormsNotConfiguredError,
        GoogleFormsService,
    )

    try:
        quiz = service.get_quiz(quiz_id=quiz_id, project_id=project_id)
        questions = service.list_quiz_questions(quiz_id=quiz_id, project_id=project_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    if not questions:
        raise HTTPException(status_code=400, detail="This quiz has no questions yet")

    questions = _with_image_urls(questions)

    settings = get_settings()
    try:
        form = GoogleFormsService(
            client_id=settings.google_oauth_client_id,
            client_secret=settings.google_oauth_client_secret,
            refresh_token=settings.google_oauth_refresh_token,
        ).publish_quiz(
            title=quiz.name,
            questions=[q.model_dump() for q in questions],
            description=f"A NISAAB practice quiz{f' · SLO {quiz.slo_code}' if quiz.slo_code else ''}.",
        )
    except FormsNotConfiguredError as e:
        # Not the student's fault and not Google's, so say which it is
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=502, detail=f"Google would not create the form: {e}"
        )
    return GoogleFormDto(
        form_id=form.form_id,
        responder_url=form.responder_url,
        edit_url=form.edit_url,
    )


@router.post("/{quiz_id}/questions", response_model=QuizQuestionDto, status_code=201)
async def create_quiz_question(
    project_id: str,
    quiz_id: str,
    question: QuizQuestionCreate,
    current_user: UserDto = Depends(get_current_user),
    service: QuizService = Depends(get_quiz_service),
):
    """Create a new question in a quiz."""
    try:
        return service.create_quiz_question(
            quiz_id=quiz_id,
            project_id=project_id,
            question_text=question.question_text,
            option_a=question.option_a,
            option_b=question.option_b,
            option_c=question.option_c,
            option_d=question.option_d,
            correct_option=question.correct_option,
            explanation=question.explanation,
            difficulty_level=question.difficulty_level,
            position=question.position,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{quiz_id}/questions/{question_id}", response_model=QuizQuestionDto)
async def get_quiz_question(
    project_id: str,
    quiz_id: str,
    question_id: str,
    current_user: UserDto = Depends(get_current_user),
    service: QuizService = Depends(get_quiz_service),
):
    """Get a question by ID."""
    try:
        return service.get_quiz_question(
            question_id=question_id,
            quiz_id=quiz_id,
            project_id=project_id,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{quiz_id}/questions/{question_id}", response_model=QuizQuestionDto)
async def update_quiz_question(
    project_id: str,
    quiz_id: str,
    question_id: str,
    question: QuizQuestionUpdate,
    current_user: UserDto = Depends(get_current_user),
    service: QuizService = Depends(get_quiz_service),
):
    """Update a question."""
    try:
        return service.update_quiz_question(
            question_id=question_id,
            quiz_id=quiz_id,
            project_id=project_id,
            question_text=question.question_text,
            option_a=question.option_a,
            option_b=question.option_b,
            option_c=question.option_c,
            option_d=question.option_d,
            correct_option=question.correct_option,
            explanation=question.explanation,
            difficulty_level=question.difficulty_level,
            position=question.position,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{quiz_id}/questions/{question_id}", status_code=204)
async def delete_quiz_question(
    project_id: str,
    quiz_id: str,
    question_id: str,
    current_user: UserDto = Depends(get_current_user),
    service: QuizService = Depends(get_quiz_service),
):
    """Delete a question."""
    try:
        service.delete_quiz_question(
            question_id=question_id,
            quiz_id=quiz_id,
            project_id=project_id,
        )
        return None
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{quiz_id}/questions/reorder", response_model=list[QuizQuestionDto])
async def reorder_quiz_questions(
    project_id: str,
    quiz_id: str,
    reorder: QuizQuestionReorder,
    current_user: UserDto = Depends(get_current_user),
    service: QuizService = Depends(get_quiz_service),
):
    """Reorder questions in a quiz."""
    try:
        return service.reorder_quiz_questions(
            quiz_id=quiz_id,
            project_id=project_id,
            question_ids=reorder.question_ids,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{quiz_id}/attempts", response_model=QuizAttemptDto, status_code=201)
async def submit_quiz_attempt(
    project_id: str,
    quiz_id: str,
    attempt: QuizAttemptCreate,
    current_user: UserDto = Depends(get_current_user),
    service: AttemptService = Depends(get_attempt_service),
):
    """Score a finished quiz on the server and record the answers for SLO mastery."""
    return service.submit_quiz(
        user_id=current_user.id,
        project_id=project_id,
        quiz_id=quiz_id,
        answers={a.question_id: a.option for a in attempt.answers},
    )


@router.get("/{quiz_id}/attempts/latest", response_model=QuizAttemptStateDto)
async def get_latest_quiz_attempt(
    project_id: str,
    quiz_id: str,
    current_user: UserDto = Depends(get_current_user),
    service: AttemptService = Depends(get_attempt_service),
):
    """The student's most recent attempt at this quiz (if any) and all their attempts."""
    attempt, history = service.latest_quiz_attempt(
        user_id=current_user.id, project_id=project_id, quiz_id=quiz_id
    )
    return QuizAttemptStateDto(attempt=attempt, history=history)
