import logging
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, TypeVar

from edu_db.session import get_session_factory
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.language_models.chat_models import BaseChatModel
from pydantic import BaseModel

from edu_ai.latex import clean_latex_deep
from edu_ai.llm import create_chat_model
from edu_ai.prompts.prompts_utils import render_prompt

if TYPE_CHECKING:
    from edu_core.services import SearchService

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class ContentAgentConfig(BaseModel):
    azure_openai_chat_deployment: str
    azure_openai_endpoint: str
    azure_openai_api_version: str


@contextmanager
def get_db_session():
    """Context manager for database sessions with transaction handling.

    Yields:
        Database session

    Raises:
        Exception: If transaction fails, automatically rolls back
    """
    SessionLocal = get_session_factory()
    db = SessionLocal(expire_on_commit=False)
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def create_llm(config: ContentAgentConfig) -> BaseChatModel:
    """Create a chat model from a config.

    Args:
        config: The ContentAgentConfig

    Returns:
        Chat model for the configured provider (see ``edu_ai.llm``)
    """
    return create_chat_model(
        temperature=0.7,
        azure_deployment=config.azure_openai_chat_deployment,
        azure_endpoint=config.azure_openai_endpoint,
        azure_api_version=config.azure_openai_api_version,
    )


async def get_context(
    project_id: str, topic: str, search_service: "SearchService"
) -> str:
    """Fetch relevant document segments directly from DocumentService."""
    if not topic:
        logger.warning(f"No topic provided for project: {project_id}")
        return ""

    # Use existing search logic in DocumentService
    # We request top 10 chunks to give the AI enough context
    results = await search_service.search_documents(
        query=topic, project_id=project_id, top_k=10
    )

    if not results:
        logger.warning(f"No documents found for topic: {topic}")
        return "No relevant documents found in the project."

    # Join content blocks
    return "\n\n---\n\n".join([r.content for r in results])


async def generate[T](
    llm: BaseChatModel,
    search_service: "SearchService",
    output_model: type[T],
    prompt_template: str,
    project_id: str,
    topic: str,
    language_code: str,
    custom_instructions: str | None = None,
    document_content: str | None = None,
    structured: bool = True,
    **kwargs: Any,
) -> T:
    """
    Main generation flow:
    1. Search documents using 'topic'
    2. Build Prompt (Context + Instructions)
    3. Call LLM
    4. Parse Result

    Set ``structured=False`` for output models that function calling cannot
    express (e.g. recursive schemas); they are parsed from plain JSON instead.
    """
    logger.info(f"Generating for topic: {topic}")

    # 1. RAG Search or use provided content
    if document_content:
        context_text = document_content
    else:
        context_text = await get_context(project_id, topic, search_service)

    # 2. Prepare Parser
    parser = JsonOutputParser(pydantic_object=output_model)

    # 3. Render Prompt
    prompt_input = render_prompt(
        prompt_template,
        document_content=context_text,
        topic=topic,
        custom_instructions=custom_instructions or "No specific instructions.",
        format_instructions=parser.get_format_instructions(),
        language_code=language_code or "en",
        **kwargs,  # Pass extra args like 'count', 'difficulty'
    )

    # 4. Invoke LLM. Structured output (function calling) keeps LaTeX backslashes
    # intact; free-text JSON often breaks on them (e.g. "\theta" parsed as a tab).
    if structured:
        try:
            result = await llm.with_structured_output(
                output_model, method="function_calling"
            ).ainvoke(prompt_input)
            if result is not None:
                return output_model(**clean_latex_deep(result.model_dump()))
            logger.warning(
                "Structured generation returned nothing, retrying as plain JSON"
            )
        except Exception as e:
            logger.warning(f"Structured generation failed, retrying as plain JSON: {e}")

    try:
        response = await llm.ainvoke(prompt_input)
        parsed_data = parser.parse(response.content)
        return output_model(**clean_latex_deep(parsed_data))
    except Exception as e:
        logger.error(f"AI Generation failed: {e}")
        raise
