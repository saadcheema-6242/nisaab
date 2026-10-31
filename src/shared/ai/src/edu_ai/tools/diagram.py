"""Draw a diagram for the student, on request, in the chat.

The same drawing code the quiz generator uses, offered to the tutor directly so
a student can ask for a picture: "draw the forces on a block on a slope",
"circuit mein do resistors parallel", "show me a velocity-time graph".

As everywhere else, the model does not draw. It names one of the kinds in
edu_core.diagrams and supplies the values; the picture is drawn from them.
"""

import json
from uuid import uuid4

from edu_core.diagrams import DiagramSpec, store
from langchain.tools import ToolRuntime, tool
from pydantic import TypeAdapter, ValidationError

from edu_ai.chatbot.context import ChatbotContext

# A V4 signed URL may last at most seven days. The chat shows the picture from
# this link, so reopening a conversation much later finds it expired - the
# question and the answer still read, only the image is gone.
LINK_SECONDS = 7 * 24 * 60 * 60


@tool(
    "draw_diagram",
    description=(
        "Draw a diagram and show it to the student in the chat. Use it when a "
        "picture is genuinely needed - the forces on a body, a circuit, a "
        "plotted graph, or vectors drawn from a point - and the student has "
        "asked for one or cannot follow without it. Pass spec as an object "
        'with "kind" and that kind\'s values. '
        'circuit: {"kind":"circuit","arrangement":"series" or "parallel",'
        '"source_label":"12 V","components":[{"label":"R1 = 4 Ohm"}]}. '
        'free_body: {"kind":"free_body","body_label":"m","forces":'
        '[{"label":"W = mg","direction_degrees":270}]}. '
        'graph: {"kind":"graph","x_label":"t / s","y_label":"v / m/s",'
        '"series":[{"label":"A","points":[{"x":0,"y":0},{"x":4,"y":8}]}]}. '
        'vectors: {"kind":"vectors","show_resultant":true,"vectors":'
        '[{"label":"F1 = 6 N","magnitude":6,"angle_degrees":0}]}. '
        "Angles are degrees anticlockwise from the positive x-axis. "
        'Last kind, for a scene rather than a measurement: '
        '{"kind":"illustration","caption":"A block on a ramp","prompt":'
        '"a wooden block resting on a wooden ramp, side view"}. The '
        "illustration is generated, so it can show a situation but cannot "
        "carry labels, arrows or values, and must never be used for a circuit, "
        "a graph, vectors or forces - those four are drawn exactly, use them. "
        "For anything none of these can show, such as a ray diagram or a "
        "biological structure, say plainly that you cannot draw it yet."
    ),
)
async def draw_diagram(
    spec: dict,
    runtime: ToolRuntime[ChatbotContext],
) -> str:
    """Draw the diagram described by ``spec`` and return a link to it.

    ``spec`` is a plain dict rather than the union type, because a discriminated
    union turns into a schema the model's function calling handles badly. It is
    validated here instead, where a mistake costs one picture and a clear
    message rather than a failed turn.
    """
    ctx = runtime.context
    if ctx.storage is None:
        return json.dumps(
            {
                "message": (
                    "Diagrams cannot be drawn here. Describe it in words instead, "
                    "and do not claim the student can see a picture."
                )
            }
        )

    try:
        checked = TypeAdapter(DiagramSpec).validate_python(spec)
    except ValidationError as error:
        return json.dumps(
            {
                "message": (
                    "That diagram spec is not valid, so nothing was drawn: "
                    f"{error.errors()[:3]}. Either correct it and call the tool "
                    "once more, or explain in words. Do not tell the student "
                    "there is a picture."
                )
            }
        )

    try:
        path, alt = store(ctx.storage, ctx.project_id, f"chat-{uuid4()}", checked)
        url = ctx.storage.signed_url(path, expires_in=LINK_SECONDS)
    except Exception as error:  # noqa: BLE001 - a picture is never worth a failed turn
        return json.dumps(
            {
                "message": (
                    f"The diagram could not be drawn ({error}). Explain it in words "
                    "instead, and do not claim the student can see a picture."
                )
            }
        )

    return json.dumps(
        {
            "image_url": url,
            "image_path": path,
            "alt": alt,
            "message": (
                "The diagram is now shown in the chat, above your reply. The student "
                "can see it. Add one short sentence about what it shows or what to "
                "read off it - do not describe it line by line, and do not repeat "
                "the values that are already labelled on it."
            ),
        }
    )


tools = [draw_diagram]
