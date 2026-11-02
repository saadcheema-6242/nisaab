"""Draw the student a figure, by writing the code that draws it.

There are two kinds of picture a student needs, and they are not the same job.

A lung, a leaf section, a distillation set-up: these already exist, drawn from
life by people who knew what they were looking at, and find_diagram searches
for them. Nothing plotted will ever produce one.

A graph of their own readings, the vector triangle for their own question, the
ray diagram for their own lens: these do not exist anywhere, because they are
about this question. They have to be drawn. A model cannot draw them - it
cannot place a 60 degree angle or spell "8.0 km" - but it can write the
matplotlib that does, and Google runs that in its own sandbox and hands back
the picture. The geometry is then Python's, not a guess.

This is why the image maker was removed and this put in its place: the same
need, answered by code that is right by construction instead of a drawing that
is confidently wrong.

Plain typed arguments, not an object: a dict argument becomes a schema with no
properties and Gemini rejects a function declared that way, which would break
every turn in the chat rather than only the ones wanting a figure.
"""

import json
from uuid import uuid4

from edu_core.code_run import figure_prompt
from langchain.tools import ToolRuntime, tool

from edu_ai.chatbot.context import ChatbotContext
from edu_ai.llm import run_code, supports_code_execution

# As long as a found diagram's link, for the same reason: a V4 signed URL may
# last at most seven days, so reopening an old chat finds the picture gone
# while the question and the answer still read.
LINK_SECONDS = 7 * 24 * 60 * 60


def stored_path(project_id: str, key: str) -> str:
    """Where a drawn figure lives in the bucket."""
    return f"{project_id}/media/{key}.png"


def _cannot(message: str) -> str:
    """A failure the tutor can act on, rather than a dead turn."""
    return json.dumps({"message": message})


@tool(
    "draw_figure",
    description=(
        "Draw a figure for this question and show it in the chat: a graph, a "
        "vector diagram, a free-body diagram, a ray diagram, a circuit, a "
        "geometric construction, a plotted curve. The figure is drawn by "
        "running real code, so its angles, scales and values are exact. "
        "Use it whenever a question is about something with a shape or a "
        "trend - 'draw the graph', 'show the resultant', 'sketch v against "
        "t' - and whenever a figure would make an explanation land. "
        "description is what to draw, in plain English, said as you would say "
        "it to someone who will draw it: 'velocity-time graph for a body "
        "starting at rest, accelerating at 2 m s^-2 for 5 s, then constant', "
        "'head-to-tail addition of three displacement vectors with the "
        "resultant from the origin'. "
        "given is every number from the student's own question - magnitudes, "
        "angles, readings, units - copied exactly. Leave it empty only when "
        "the question truly has no numbers. Never make a value up; a figure "
        "with invented readings is worse than none. "
        "subject is their subject, e.g. 'Physics' or 'Mathematics'. "
        "Do NOT use this for a photograph or anything drawn from life - a "
        "lung, a cell, a leaf section, laboratory apparatus. Those are found "
        "with find_diagram instead."
    ),
)
async def draw_figure(
    description: str,
    runtime: ToolRuntime[ChatbotContext],
    given: str = "",
    subject: str = "",
) -> str:
    """Write the code, run it, keep the picture, and hand back a link."""
    ctx = runtime.context

    if ctx.storage is None:
        return _cannot(
            "Figures cannot be shown here. Explain it in words instead, and "
            "do not claim the student can see one."
        )
    if not supports_code_execution():
        return _cannot(
            "Drawing is not available on this setup. Explain it in words "
            "instead, and do not describe a picture the student cannot see."
        )

    try:
        run = run_code(figure_prompt(description, subject=subject, given=given))
    except Exception as error:  # noqa: BLE001 - never lose a turn over a picture
        print(f"draw_figure failed: {type(error).__name__}: {error}")
        return _cannot(
            f"The figure could not be drawn ({error}). Explain it in words "
            "instead."
        )

    if not run.drew_something:
        # Worth logging the difference: code that failed is a prompt or a
        # sandbox problem, no code at all is the model answering in words.
        print(
            "draw_figure produced no picture "
            f"(outcome={run.outcome or 'no code ran'}, output={run.output[:200]!r})"
        )
        return _cannot(
            "No figure came back. Explain it in words instead, and do not "
            "describe a picture the student cannot see."
        )

    try:
        path = stored_path(ctx.project_id, f"figure-{uuid4()}")
        ctx.storage.upload(path, run.pictures[0], content_type="image/png")
        url = ctx.storage.signed_url(path, expires_in=LINK_SECONDS)
    except Exception as error:  # noqa: BLE001
        print(f"draw_figure store failed: {type(error).__name__}: {error}")
        return _cannot(
            f"The figure could not be saved ({error}). Explain it in words "
            "instead."
        )

    return json.dumps(
        {
            "image_url": url,
            "image_path": path,
            "alt": description[:200],
            "message": (
                "The figure is now shown in the chat and the student can see "
                "it. Say one or two sentences about how to read it - what the "
                "axes or the arrows mean, and what it shows. Do not list the "
                "numbers again and do not describe it from top to bottom."
            ),
        }
    )


tools = [draw_figure]
