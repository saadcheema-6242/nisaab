"""Generate an illustration with Imagen on Vertex AI.

Used for the one thing the drawn diagrams cannot do: a picture of a situation.
A trolley on an inclined plane, a beaker over a flame, a person pulling a crate
- scenes that set up a question but carry no measurement.

The prompt asks for no text at all, because an image model cannot spell: any
wording it drew would be letters that spell nothing. So anything exact - a
value, a label, an axis - belongs in the question and the options, not in the
picture. Callers go through edu_core.study_images, which anchors the prompt to
the student's subject and keeps this to study material.

Called over REST with the credentials the service already has, so this adds no
dependency - httpx and google-auth are both in use already.
"""

import base64
import os

import httpx

# Imagen is not served from the "global" endpoint that the text models use
DEFAULT_LOCATION = "us-central1"
DEFAULT_MODEL = "imagen-4.0-generate-001"
TIMEOUT = 120.0

# Asking for no words is the single most useful instruction: an image model
# cannot spell, and a mislabelled diagram is worse than an unlabelled one.
STYLE = (
    "Clean educational illustration for a school science textbook, flat vector "
    "style, plain white background, simple shapes, clear outlines, muted colours. "
    "No text, no letters, no numbers, no labels, no watermark, no captions."
)


class ImageGenerationError(RuntimeError):
    """Vertex would not produce an image."""


def _settings() -> tuple[str, str, str]:
    project = (
        os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT") or ""
    ).strip()
    if not project:
        raise ImageGenerationError("GOOGLE_CLOUD_PROJECT is not set")
    location = (os.getenv("IMAGE_LOCATION") or DEFAULT_LOCATION).strip()
    model = (os.getenv("IMAGE_MODEL") or DEFAULT_MODEL).strip()
    return project, location, model


def _token() -> str:
    import google.auth
    from google.auth.transport.requests import Request

    credentials, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    credentials.refresh(Request())
    return credentials.token


def generate(prompt: str, aspect_ratio: str = "4:3") -> bytes:
    """Return one PNG for ``prompt``.

    Raises:
        ImageGenerationError: If Vertex refuses, times out, or filters the
            prompt. The caller is expected to carry on without the picture.
    """
    description = " ".join((prompt or "").split())
    if not description:
        raise ImageGenerationError("An illustration needs a description")

    project, location, model = _settings()
    url = (
        f"https://{location}-aiplatform.googleapis.com/v1/projects/{project}"
        f"/locations/{location}/publishers/google/models/{model}:predict"
    )
    body = {
        "instances": [{"prompt": f"{description}. {STYLE}"}],
        "parameters": {
            "sampleCount": 1,
            "aspectRatio": aspect_ratio,
            # Students are the audience, so keep the filter tight and keep
            # people out of the picture entirely
            "safetySetting": "block_medium_and_above",
            "personGeneration": "dont_allow",
        },
    }

    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            reply = client.post(
                url,
                headers={
                    "Authorization": f"Bearer {_token()}",
                    "Content-Type": "application/json",
                },
                json=body,
            )
    except httpx.HTTPError as error:
        raise ImageGenerationError(f"Vertex could not be reached: {error}") from error

    if reply.status_code != 200:
        raise ImageGenerationError(
            f"Vertex refused the image ({reply.status_code}): {reply.text[:300]}"
        )

    predictions = reply.json().get("predictions") or []
    if not predictions:
        # An empty list is what a blocked prompt looks like: there is no error
        raise ImageGenerationError(
            "Vertex returned no image. The prompt was most likely filtered; "
            "describe the situation more plainly."
        )

    encoded = predictions[0].get("bytesBase64Encoded")
    if not encoded:
        raise ImageGenerationError("Vertex returned a prediction with no image data")
    return base64.b64decode(encoded)


def available() -> bool:
    """Whether a project is configured at all, without calling Vertex."""
    return bool(
        (os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT") or "").strip()
    )
