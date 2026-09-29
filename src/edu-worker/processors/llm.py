"""LLM helper utilities for worker processes."""

from edu_ai.llm import create_chat_model
from langchain_core.language_models.chat_models import BaseChatModel


def create_llm(
    azure_openai_chat_deployment: str,
    azure_openai_endpoint: str,
    azure_openai_api_version: str,
    streaming: bool = True,
    temperature: float = 0.25,
) -> BaseChatModel:
    """Create a chat model for worker processes.

    Args:
        azure_openai_chat_deployment: Azure OpenAI chat deployment name
        azure_openai_endpoint: Azure OpenAI endpoint URL
        azure_openai_api_version: Azure OpenAI API version
        streaming: Whether to enable streaming
        temperature: Temperature for the LLM

    Returns:
        Chat model for the configured provider (see ``edu_ai.llm``)
    """
    return create_chat_model(
        streaming=streaming,
        temperature=temperature,
        azure_deployment=azure_openai_chat_deployment,
        azure_endpoint=azure_openai_endpoint,
        azure_api_version=azure_openai_api_version,
    )


def create_llm_non_streaming(
    azure_openai_chat_deployment: str,
    azure_openai_endpoint: str,
    azure_openai_api_version: str,
    temperature: float = 0.25,
) -> BaseChatModel:
    """Create a non-streaming chat model for worker processes.

    Args:
        azure_openai_chat_deployment: Azure OpenAI chat deployment name
        azure_openai_endpoint: Azure OpenAI endpoint URL
        azure_openai_api_version: Azure OpenAI API version
        temperature: Temperature for the LLM

    Returns:
        Non-streaming chat model for the configured provider
    """
    return create_llm(
        azure_openai_chat_deployment,
        azure_openai_endpoint,
        azure_openai_api_version,
        streaming=False,
        temperature=temperature,
    )
