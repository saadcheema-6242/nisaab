import json
from contextlib import suppress
from typing import Any

from edu_core.tool_loops import calls_since_student, loop_note

from edu_ai.agents.slo_context import language_name
from edu_ai.chatbot.context import ChatbotContext, ChatbotState
from edu_ai.prompts.prompts_utils import render_prompt
from edu_ai.tools.diagram import tools as diagram_tools
from edu_ai.tools.figure import tools as figure_tools
from edu_ai.tools.flashcard import tools as flashcard_tools
from edu_ai.tools.mind_map import tools as mind_map_tools
from edu_ai.tools.note import tools as note_tools
from edu_ai.tools.practice import tools as practice_tools
from edu_ai.tools.quiz import tools as quiz_tools
from edu_ai.tools.rag import tools as rag_tools
from edu_ai.tools.study_plan import tools as study_plan_tools
from edu_ai.tools.syllabus import tools as syllabus_tools
from edu_ai.tools.web import tools as web_tools
from langchain.agents import create_agent
from langchain.agents.middleware import (
    ModelRequest,
    after_model,
    dynamic_prompt,
    wrap_tool_call,
)
from langchain_core.messages import ToolMessage
from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.runtime import Runtime


@wrap_tool_call
async def stop_repeating_yourself(request, handler):
    """Let a repeated tool call run, then tell the model it has enough.

    A student asked for a picture of computer architecture and watched
    "Checked the FBISE syllabus" five times over three minutes before anything
    was written. Each of those is a whole round trip to the model, so a loop
    costs the student the answer, not just the time.

    The result is still returned - cutting it off would lose real information -
    but a line is added saying the ground has been covered. The model stops
    because it is told it already has what it went looking for, which is both
    true and the only thing that ends a loop from inside.

    The counting is in edu_core.tool_loops, where it can be checked without an
    agent, a model or a framework to stand it up.
    """
    result = await handler(request)
    if not isinstance(result, ToolMessage):
        return result
    with suppress(Exception):
        name = getattr(request.tool, "name", "")
        calls = calls_since_student(request.state.get("messages"), name)
        if note := loop_note(name, calls):
            result.content = f"{result.content}\n\n{note}"
    return result


@wrap_tool_call
async def capture_sources_from_rag(request, handler):
    """Capture sources when RAG search tool is used."""
    # Execute the tool
    result = await handler(request)

    # Check if this was a search_project_documents call
    if request.tool.name == "search_project_documents" and isinstance(
        result, ToolMessage
    ):
        with suppress(Exception):
            # Parse the content to extract sources
            content = (
                json.loads(result.content)
                if isinstance(result.content, str)
                else result.content
            )
            sources = content.get("sources", [])

            # Store sources in state
            if sources:
                request.state["sources"] = sources
                # Also store in additional_kwargs so we can access it in the stream
                if (
                    not hasattr(result, "additional_kwargs")
                    or result.additional_kwargs is None
                ):
                    result.additional_kwargs = {}
                result.additional_kwargs["sources"] = sources

            # Return just the content string to the agent
            result.content = content.get("content", result.content)

    return result


# Cache system prompts by language and FBISE subject for performance
_prompt_cache: dict[tuple, str] = {}


def get_instructions(language: str = "English") -> str:
    """Load and render the system prompt template."""
    return render_prompt("system_prompt", language=language)


def get_fbise_instructions(ctx: ChatbotContext) -> str:
    """The FBISE tutor prompt for a subject workspace, e.g. Physics XI."""
    fbise = ctx.fbise
    return render_prompt(
        "system_prompt_fbise",
        subject=fbise.subject,
        grade_label=fbise.grade_label,
        curriculum=fbise.curriculum,
        has_slos=fbise.has_slos,
        has_web_search=bool(web_tools),
        language_code=ctx.language,
        language_name=language_name(ctx.language),
    )


@dynamic_prompt
async def dynamic_system_prompt(request: ModelRequest) -> str:
    """Generate dynamic system prompt."""
    ctx = request.runtime.context
    language = ctx.language or "en"
    key = (language, ctx.fbise.model_dump_json() if ctx.fbise else None)

    # Return cached prompt if available
    if key not in _prompt_cache:
        if ctx.fbise:
            _prompt_cache[key] = get_fbise_instructions(ctx)
        else:
            _prompt_cache[key] = get_instructions(language_name(language))

    # The student's choice changes per message, so it is appended rather than
    # cached - the cache is keyed on language and subject only.
    return _prompt_cache[key] + _choice_note(ctx)


def _choice_note(ctx: ChatbotContext) -> str:
    """What the student ticked beside the message box, if anything."""
    notes = []
    if ctx.allowed_tools:
        notes.append(
            "For this message the student chose which tools you may use: "
            f"{', '.join(ctx.allowed_tools)}. Use only those. If what they ask "
            "for needs a different one, say so plainly instead of using it."
        )
    if ctx.web_search is False:
        notes.append(
            "The student has turned web search off for this message. Do not "
            "search the web; answer from the syllabus and what you know."
        )
    if not notes:
        return ""
    return "\n\n" + "\n".join(notes)


@after_model(state_schema=ChatbotState)
def ensure_sources_in_stream(
    state: ChatbotState, runtime: Runtime[ChatbotContext]
) -> dict[str, Any] | None:
    """Ensure sources are included in the model node update for streaming."""
    sources = state.get("sources", [])
    return {"sources": sources} if sources else None


# Tools the student never picks from the menu: the tutor needs them to answer
# at all, so a choice of "only the quiz maker" must not take away its ability
# to look up a syllabus outcome or read the student's own notes.
ALWAYS_AVAILABLE = {"find_syllabus_slos", "search_project_documents"}


def make_chatbot(
    llm: BaseChatModel,
    allowed_tools: list[str] | None = None,
    web_search: bool | None = None,
):
    """Build the agent, optionally limited to the tools the student ticked.

    The limit is applied here, by leaving tools out, rather than by refusing a
    call once the model has made it. The model then cannot try a tool that is
    not on offer, so no turn is wasted on a refusal - and this does not depend
    on the shape of the middleware's request object, which is version specific.
    """
    tools = [
        *rag_tools,
        *syllabus_tools,
        *web_tools,
        *practice_tools,
        *diagram_tools,
        *figure_tools,
        *flashcard_tools,
        *quiz_tools,
        *note_tools,
        *mind_map_tools,
        *study_plan_tools,
    ]

    if web_search is False:
        tools = [t for t in tools if t.name != "search_web"]
    if allowed_tools:
        keep = set(allowed_tools) | ALWAYS_AVAILABLE
        tools = [t for t in tools if t.name in keep]

    return create_agent(
        model=llm,
        tools=tools,
        middleware=[
            stop_repeating_yourself,
            capture_sources_from_rag,
            dynamic_system_prompt,
            ensure_sources_in_stream,
        ],
        state_schema=ChatbotState,
        context_schema=ChatbotContext,
    )
