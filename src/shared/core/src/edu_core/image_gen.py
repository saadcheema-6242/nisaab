"""Generate a picture with Google's image models on Vertex AI.

The prompt asks for no text at all, because an image model cannot spell: any
wording it drew would be letters that spell nothing. So anything exact - a
value, a label, an axis - belongs in the question and the options, not in the
picture. Callers go through edu_core.study_images, which anchors the prompt to
the student's subject and keeps this to study material.

Two families, two different calls
---------------------------------
Google has retired the Imagen 4 endpoints, and the current image models are the
Gemini ones. They are not drop-in replacements: Imagen answers ``:predict`` with
``instances``/``parameters``, while a Gemini model answers ``:generateContent``
with ``contents`` and ``responseModalities``. Which call to make is decided from
the model name, so moving between them is a settings change.

Called over REST with the credentials the service already has, so this adds no
dependency - httpx and google-auth are both in use already.
"""

import base64
import os

import httpx

# Image models are not served from the "global" endpoint the text models use
DEFAULT_LOCATION = "us-central1"
DEFAULT_MODEL = "gemini-2.5-flash-image"
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


def uses_predict(model: str) -> bool:
    """Imagen answers :predict; the Gemini image models answer :generateContent."""
    name = model.lower()
    return name.startswith(("imagen", "imagegeneration"))


def _imagen_body(described: str, aspect_ratio: str) -> dict:
    return {
        "instances": [{"prompt": described}],
        "parameters": {
            "sampleCount": 1,
            "aspectRatio": aspect_ratio,
            # Students are the audience, so keep the filter tight and keep
            # people out of the picture entirely
            "safetySetting": "block_medium_and_above",
            "personGeneration": "dont_allow",
        },
    }


def _gemini_body(described: str) -> dict:
    return {
        "contents": [{"role": "user", "parts": [{"text": described}]}],
        # Without this the model replies with words describing a picture
        "generationConfig": {"responseModalities": ["IMAGE"]},
    }


def _imagen_image(payload: dict) -> bytes:
    predictions = payload.get("predictions") or []
    if not predictions:
        raise ImageGenerationError(
            "Vertex returned no image. The prompt was most likely filtered; "
            "describe the situation more plainly."
        )
    encoded = predictions[0].get("bytesBase64Encoded")
    if not encoded:
        raise ImageGenerationError("Vertex returned a prediction with no image data")
    return base64.b64decode(encoded)


def _gemini_image(payload: dict) -> bytes:
    for candidate in payload.get("candidates") or []:
        for part in (candidate.get("content") or {}).get("parts") or []:
            inline = part.get("inlineData") or part.get("inline_data")
            if inline and inline.get("data"):
                return base64.b64decode(inline["data"])
    # A model that answers in words has usually refused the prompt
    raise ImageGenerationError(
        "The model replied without an image. The prompt was most likely "
        "filtered; describe the situation more plainly."
    )


def generate(prompt: str, aspect_ratio: str = "4:3") -> bytes:
    """Return one PNG for ``prompt``.

    Raises:
        ImageGenerationError: If Vertex refuses, times out, or filters the
            prompt. The caller is expected to carry on without the picture.
    """
    described = " ".join((prompt or "").split())
    if not described:
        raise ImageGenerationError("An illustration needs a description")

    project, location, model = _settings()
    predict = uses_predict(model)
    verb = "predict" if predict else "generateContent"
    url = (
        f"https://{location}-aiplatform.googleapis.com/v1/projects/{project}"
        f"/locations/{location}/publishers/google/models/{model}:{verb}"
    )
    described = f"{described}. {STYLE}"
    body = _imagen_body(described, aspect_ratio) if predict else _gemini_body(described)

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

    payload = reply.json()
    return _imagen_image(payload) if predict else _gemini_image(payload)


def available() -> bool:
    """Whether a project is configured at all, without calling Vertex."""
    return bool(
        (os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT") or "").strip()
    )
