"""Make a picture for the student, on request, in the chat.

The same generator the quiz uses, offered to the tutor directly so a student
can ask: "show me a picture of a block on a slope", "trolley ki picture dikhao".

For study material only. The tool description says so, the prompt is anchored
to the student's subject, and anything off the syllabus is refused in words
rather than drawn.
"""

import json
from uuid import uuid4

from edu_core.study_images import ImageError, StudyImageSpec, store
from langchain.tools import ToolRuntime, tool
from pydantic import ValidationError

from edu_ai.chatbot.context import ChatbotContext

# A V4 signed URL may last at most seven days. The chat shows the picture from
# this link, so reopening a conversation much later finds it expired - the
# question and the answer still read, only the image is gone.
LINK_SECONDS = 7 * 24 * 60 * 60


@tool(
    "generate_image",
    description=(
        "Make a picture and show it to the student in the chat. Use it when a "
        "picture genuinely helps and the student has asked for one or cannot "
        "follow without it - a situation, an apparatus, a shape to recognise. "
        "prompt is the scene in plain words, for example 'a wooden block resting "
        "on a wooden ramp, side view'. subject is the FSc subject it belongs to. "
        "caption is one line to show under it. "
        "Only for what the student is studying: if the request is not about "
        "their FSc subjects, say you only make pictures for their studies and "
        "do not call this. The picture is generated, so it cannot carry "
        "labels, arrows, values or any text - describe those in your reply "
        "instead, and never say the picture shows a word or a number."
    ),
)
async def generate_image(
    prompt: str,
    runtime: ToolRuntime[ChatbotContext],
    subject: str = "",
    caption: str = "",
) -> str:
    """Draw the picture and return a link to it.

    Plain typed arguments, not an object. A ``dict`` argument becomes a schema
    with no properties, and Gemini rejects a function declared that way - which
    takes down every turn in the chat, not just the ones that want a picture,
    because the tool list goes out with every model call. Every other tool here
    takes scalars for the same reason.
    """
    ctx = runtime.context
    if ctx.storage is None:
        return json.dumps(
            {
                "message": (
                    "Pictures cannot be made here. Describe it in words instead, "
                    "and do not claim the student can see one."
                )
            }
        )

    # The subject the student is working in, unless the model named one itself
    if not subject and ctx.fbise:
        subject = getattr(ctx.fbise, "subject", "") or ""

    try:
        checked = StudyImageSpec(prompt=prompt, subject=subject, caption=caption)
    except ValidationError as error:
        return json.dumps(
            {
                "message": (
                    "That picture request is not valid, so nothing was made: "
                    f"{error.errors()[:3]}. Either correct it and call the tool "
                    "once more, or explain in words."
                )
            }
        )

    try:
        path, alt = store(ctx.storage, ctx.project_id, f"chat-{uuid4()}", checked)
        url = ctx.storage.signed_url(path, expires_in=LINK_SECONDS)
    except Exception as error:  # noqa: BLE001 - never fail a turn over a picture
        # Printed as well as returned: the tool's reply only reaches the model,
        # so without this a failure leaves nothing in the logs to diagnose.
        print(f"generate_image failed: {type(error).__name__}: {error}")
        return json.dumps(
            {
                "message": (
                    f"The picture could not be made ({error}). Explain it in "
                    "words instead, and do not claim the student can see one."
                )
            }
        )

    return json.dumps(
        {
            "image_url": url,
            "image_path": path,
            "alt": alt,
            "message": (
                "The picture is now shown in the chat, above your reply. The "
                "student can see it. Add one short sentence about what it shows "
                "- do not describe it line by line, and remember it carries no "
                "labels or numbers."
            ),
        }
    )


tools = [generate_image]
