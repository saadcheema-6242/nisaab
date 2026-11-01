"""Note tools for agent."""

import asyncio
import json
from contextlib import suppress

from edu_ai.chatbot.context import ChatbotContext
from edu_core.schemas.notes import NoteDto
from edu_core.services.notes import NoteService
from langchain.tools import tool
from langgraph.prebuilt import ToolRuntime


def build_enhanced_prompt(
    custom_instructions: str | None,
    query: str | None = None,
    document_ids: list[str] | None = None,
) -> str:
    """Build enhanced prompt with optional query and document filtering."""
    prompt = custom_instructions or ""
    if query:
        prompt += f" Focus on: {query}"
    if document_ids:
        prompt += f" Based on specific documents: {', '.join(document_ids)}"
    return prompt


def increment_usage(usage, user_id: str, feature: str) -> None:
    """Increment usage tracking, log errors but don't fail."""
    if not usage:
        return
    with suppress(Exception):
        usage.check_and_increment(user_id, feature)


@tool(
    "note_create",
    description=(
        "Write the student a full set of study notes on a topic, saved to "
        "their Study tab. "
        "topic is what the notes are about. "
        "custom_instructions is anything the student asked for in their own "
        "words - shorter, only one section, more examples, exam-focused - and "
        "it overrides the defaults, so pass it through rather than tidying it. "
        "difficulty is Beginner, Intermediate or Advanced: Beginner defines "
        "every term first, Advanced goes into derivations and exceptions. Ask "
        "which they want if the topic is new to them and they have not said. "
        "page_range limits the notes to pages of their own uploaded document, "
        "e.g. '12-20'. "
        "include_keywords adds a key-terms list at the end, which is what a "
        "student wants the night before a paper."
    ),
)
async def create_note(
    topic: str,
    runtime: ToolRuntime[ChatbotContext],
    custom_instructions: str | None = None,
    difficulty: str = "",
    page_range: str = "",
    include_keywords: bool = False,
) -> str:
    """Create a study note from project documents."""
    ctx = runtime.context
    increment_usage(ctx.usage, ctx.user_id, "note_generation")

    svc = NoteService(queue_service=ctx.queue)
    # Create a new note first
    note = svc.create_note(
        project_id=ctx.project_id,
        title="Generated Note",
        description="AI-generated study note",
        content="",
    )

    # Send message to queue
    svc.queue_generation(
        note_id=note.id,
        project_id=ctx.project_id,
        topic=topic,
        custom_instructions=custom_instructions,
        user_id=ctx.user_id,
        difficulty=difficulty.strip() or None,
        page_range=page_range.strip() or None,
        include_keywords=include_keywords,
    )

    return json.dumps(
        {
            "status": "queued",
            "message": "Queued. The student sees it in this chat as a card with an Open button (and in the Study tab) within about a minute. Reply with one short sentence only: do not write out its questions, cards or content, and never mention any ID.",
            "note_id": note.id,
        },
        ensure_ascii=False,
    )


@tool(
    "note_create_scoped",
    description="Create a study note from specific documents. Use when user references specific docs or IDs.",
)
async def create_note_scoped(
    custom_instructions: str,
    document_ids: list[str],
    query: str,
    runtime: ToolRuntime[ChatbotContext],
) -> str:
    """Create a study note from specific documents."""
    ctx = runtime.context
    increment_usage(ctx.usage, ctx.user_id, "note_generation")

    enhanced_prompt = build_enhanced_prompt(custom_instructions, query, document_ids)

    svc = NoteService(queue_service=ctx.queue)
    # Create a new note first
    note = svc.create_note(
        project_id=ctx.project_id,
        user_id=ctx.user_id,
        title="Generated Note",
        description="AI-generated study note",
    )

    # Send message to queue
    svc.queue_generation(
        note_id=note.id,
        project_id=ctx.project_id,
        topic=query,
        custom_instructions=enhanced_prompt,
        user_id=ctx.user_id,
    )

    return json.dumps(
        {
            "status": "queued",
            "message": "Queued. The student sees it in this chat as a card with an Open button (and in the Study tab) within about a minute. Reply with one short sentence only: do not write out its questions, cards or content, and never mention any ID.",
            "note_id": note.id,
        },
        ensure_ascii=False,
    )


@tool("note_list", description="List notes for a project")
async def list_notes(runtime: ToolRuntime[ChatbotContext]) -> str:
    """List notes for a project."""
    ctx = runtime.context
    svc = NoteService(queue_service=ctx.queue)
    notes = await asyncio.to_thread(svc.list_notes, ctx.project_id)

    notes_dto = [NoteDto.model_validate(n) for n in notes]
    result = {
        "data": [n.model_dump() for n in notes_dto],
        "count": len(notes_dto),
    }
    return json.dumps(result, ensure_ascii=False, default=str)


@tool("note_get", description="Get a specific note by ID")
async def get_note(
    note_id: str,
    runtime: ToolRuntime[ChatbotContext],
) -> str:
    """Get a specific note by ID."""
    ctx = runtime.context
    svc = NoteService(queue_service=ctx.queue)
    note = await asyncio.to_thread(svc.get_note, note_id, ctx.project_id)

    if not note:
        return json.dumps({"error": "Note not found"}, ensure_ascii=False)

    note_dto = NoteDto.model_validate(note)
    result = note_dto.model_dump()
    return json.dumps(result, ensure_ascii=False, default=str)


@tool("note_delete", description="Delete a note")
async def delete_note(
    note_id: str,
    runtime: ToolRuntime[ChatbotContext],
) -> str:
    """Delete a note."""
    ctx = runtime.context
    svc = NoteService(queue_service=ctx.queue)
    await asyncio.to_thread(svc.delete_note, note_id, ctx.project_id)

    result = {
        "success": True,
        "note_id": note_id,
        "message": "Note successfully deleted.",
    }
    return json.dumps(result, ensure_ascii=False)


tools = [
    create_note,
    # create_note_scoped,
    list_notes,
    get_note,
    delete_note,
]
