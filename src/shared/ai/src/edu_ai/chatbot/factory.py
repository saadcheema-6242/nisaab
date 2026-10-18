import json
from contextlib import suppress
from typing import Any

from edu_ai.agents.slo_context import language_name
from edu_ai.chatbot.context import ChatbotContext, ChatbotState
from edu_ai.prompts.prompts_utils import render_prompt
from edu_ai.tools.flashcard import tools as flashcard_tools
from edu_ai.tools.mind_map import tools as mind_map_tools
from edu_ai.tools.note import tools as note_tools
from edu_ai.tools.practice import tools as practice_tools
from edu_ai.tools.quiz import tools as quiz_tools
from edu_ai.tools.rag import tools as rag_tools
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
    if key in _prompt_cache:
        return _prompt_cache[key]

    # Generate and cache the prompt
    if ctx.fbise:
        prompt = get_fbise_instructions(ctx)
    else:
        prompt = get_instructions(language_name(language))

    _prompt_cache[key] = prompt
    return prompt


@after_model(state_schema=ChatbotState)
def ensure_sources_in_stream(
    state: ChatbotState, runtime: Runtime[ChatbotContext]
) -> dict[str, Any] | None:
    """Ensure sources are included in the model node update for streaming."""
    sources = state.get("sources", [])
    return {"sources": sources} if sources else None


def make_chatbot(llm: BaseChatModel):
    tools = [
        *rag_tools,
        *syllabus_tools,
        *web_tools,
        *practice_tools,
        *flashcard_tools,
        *quiz_tools,
        *note_tools,
        *mind_map_tools,
    ]

    return create_agent(
        model=llm,
        tools=tools,
        middleware=[
            capture_sources_from_rag,
            dynamic_system_prompt,
            ensure_sources_in_stream,
        ],
        state_schema=ChatbotState,
        context_schema=ChatbotContext,
    )
