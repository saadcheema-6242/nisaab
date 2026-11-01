"""Find a real diagram for the student, from sources that permit reuse.

An image model cannot draw a correct labelled diagram - it cannot spell, and a
confidently wrong diagram in an exam question is worse than no diagram. The
diagrams that are both correct and labelled already exist, drawn by people, in
Wikimedia Commons and the other openly licensed collections.

So this searches rather than draws. Only free licences are accepted, the check
is in code rather than left to the model, and the author, licence and source
are stored with the picture and shown wherever it is shown - which is what
those licences require in return.

Plain typed arguments, not an object: a dict argument becomes a schema with no
properties and Gemini rejects a function declared that way, which would break
every turn in the chat rather than only the ones wanting a diagram.
"""

import json
from uuid import uuid4

from edu_core.openly_licensed import SearchError, fetch, search
from langchain.tools import ToolRuntime, tool

from edu_ai.chatbot.context import ChatbotContext

# A V4 signed URL may last at most seven days, so reopening an old chat finds
# the picture gone. The question, the answer and the credit all still read.
LINK_SECONDS = 7 * 24 * 60 * 60


def stored_path(project_id: str, key: str) -> str:
    """Where a found diagram lives in the bucket."""
    return f"{project_id}/media/{key}.png"


@tool(
    "find_diagram",
    description=(
        "Find a real, labelled diagram for the student and show it in the "
        "chat. Use it when a picture genuinely helps - a cell, an organ, an "
        "apparatus, a structure, a labelled process. "
        "query is what to look for, in plain English, as it would be titled in "
        "an encyclopedia: 'animal cell diagram labelled', 'benzene structural "
        "formula', 'human eye anatomy'. Keep it to the thing itself; do not "
        "add 'FSc' or the student's language. "
        "These are real diagrams drawn by people, so unlike a generated "
        "picture they DO carry correct labels and values, and you may refer to "
        "what they show. "
        "If nothing is found, say so plainly and explain in words instead - "
        "never describe a picture the student cannot see."
    ),
)
async def find_diagram(
    query: str,
    runtime: ToolRuntime[ChatbotContext],
) -> str:
    """Search, keep the best match, and return a link plus its credit."""
    ctx = runtime.context
    if ctx.storage is None:
        return json.dumps(
            {
                "message": (
                    "Diagrams cannot be shown here. Explain it in words instead, "
                    "and do not claim the student can see one."
                )
            }
        )

    try:
        results = search(query, limit=4)
    except SearchError as error:
        print(f"find_diagram search failed: {error}")
        return json.dumps(
            {
                "message": (
                    f"The diagram search is not working just now ({error}). "
                    "Explain it in words instead."
                )
            }
        )

    if not results:
        return json.dumps(
            {
                "message": (
                    "No freely licensed diagram was found for that. Say so "
                    "plainly, explain it in words, and do not describe a "
                    "picture the student cannot see. A shorter, more ordinary "
                    "wording sometimes finds one."
                )
            }
        )

    best = results[0]
    try:
        path = stored_path(ctx.project_id, f"chat-{uuid4()}")
        # Taken into our own storage: a link to someone else's server breaks
        # when they move the file. The licence permits the copy; the credit
        # below is the condition attached to it.
        ctx.storage.upload(path, fetch(best.image_url), content_type="image/png")
        url = ctx.storage.signed_url(path, expires_in=LINK_SECONDS)
    except Exception as error:  # noqa: BLE001 - never lose a turn over a picture
        print(f"find_diagram store failed: {type(error).__name__}: {error}")
        return json.dumps(
            {
                "message": (
                    f"The diagram could not be saved ({error}). Explain it in "
                    "words instead."
                )
            }
        )

    credit = best.credit.as_dict()
    return json.dumps(
        {
            "image_url": url,
            "image_path": path,
            "alt": best.title,
            "credit": credit,
            "message": (
                f"The diagram '{best.title}' is now shown in the chat, with its "
                "credit underneath. The student can see it. Say one short "
                "sentence about what it shows and how to read it. Do not repeat "
                "the credit - it is displayed already."
            ),
        }
    )


tools = [find_diagram]
