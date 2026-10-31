"""Pictures for questions, generated with Imagen on Vertex AI.

A question sometimes cannot be asked in words: a scene, an apparatus, a shape
to recognise. The model describes what the picture should show and Imagen draws
it. The image is stored as an object and signed when it is needed, so the same
picture serves the app, the PDF export and a Google Form.

It is for study material only. The prompt is anchored to the student's subject
and to a school textbook style, and the tool descriptions say plainly that
anything unrelated to the syllabus is refused. The style also asks for no text
at all, because an image model cannot spell: any wording it drew would be
letters that spell nothing, which is worse on a question than no wording.

Replaced the earlier drawn diagrams (circuits, graphs, vectors, free-body,
ring structures), which were exact but covered only five shapes.
"""

from typing import Literal

from pydantic import BaseModel, Field

MAX_PROMPT = 600


class ImageError(RuntimeError):
    """The picture could not be made."""


class StudyImageSpec(BaseModel):
    """What a question's picture should show."""

    kind: Literal["image"] = "image"
    caption: str = Field(
        "", max_length=200, description="One line under the picture, if useful"
    )
    subject: str = Field(
        "",
        max_length=60,
        description=(
            "The FSc subject the picture belongs to, e.g. Physics. Used to keep "
            "the picture on the syllabus."
        ),
    )
    prompt: str = Field(
        ...,
        min_length=8,
        max_length=MAX_PROMPT,
        description=(
            "The scene to draw, plainly: 'a wooden block resting on a ramp, "
            "side view'. It must be something an FSc student is studying. No "
            "labels, arrows, values or units - those cannot be drawn correctly "
            "and are left out of the picture."
        ),
    )


def render(spec: StudyImageSpec) -> bytes:
    """Draw the picture and return a PNG."""
    from edu_core.image_gen import ImageGenerationError, generate

    subject = (spec.subject or "").strip()
    scene = " ".join(spec.prompt.split())[:MAX_PROMPT]
    # Anchoring to the subject is what keeps this on the syllabus rather than
    # becoming a general-purpose image generator
    described = f"{subject} textbook illustration. {scene}" if subject else scene

    try:
        return generate(described)
    except ImageGenerationError as error:
        raise ImageError(str(error)) from error


def alt_text(spec: StudyImageSpec) -> str:
    """A description for screen readers and for a Google Form's altText."""
    return (spec.caption or spec.prompt)[:400]


def image_path(project_id: str, question_id: str) -> str:
    """Where a question's picture lives in the bucket."""
    return f"{project_id}/images/{question_id}.png"


def store(storage, project_id: str, question_id: str, spec: StudyImageSpec) -> tuple[str, str]:
    """Draw the picture, put it in object storage, return (path, alt text).

    The storage client is passed in rather than built here, so this module can
    be tested without a bucket.
    """
    path = image_path(project_id, question_id)
    storage.upload(path, render(spec), content_type="image/png")
    return path, alt_text(spec)
