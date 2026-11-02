"""Factory for chat and embedding models.

The provider is selected with ``LLM_PROVIDER``:

- ``azure`` (default): Azure OpenAI. Uses ``AZURE_OPENAI_API_KEY`` when set,
  otherwise Entra ID via ``DefaultAzureCredential``.
- ``gemini``: Google Gemini API (AI Studio key) through its OpenAI-compatible endpoint.
- ``vertex``: Gemini on Google Cloud Vertex AI through its OpenAI-compatible
  endpoint, authenticated with Application Default Credentials (the Cloud Run
  service account, or ``gcloud auth application-default login`` locally).
- ``openai``: OpenAI, or any other OpenAI-compatible endpoint via ``LLM_BASE_URL``.

Models can be set per task (``LLM_TUTOR_MODEL``, ``LLM_GENERATION_MODEL``,
``LLM_MARKING_MODEL``, ``LLM_OCR_MODEL``), falling back to ``LLM_CHAT_MODEL``.
For Gemini and Vertex, ``LLM_FALLBACK_MODELS`` (comma separated) lists models
to try when a call hits a rate limit or a server error.

Settings are read from the environment, the repository root ``.env`` and the
``.env`` in the current working directory (the latter wins).
"""

import base64
import logging
import threading
import time
from collections.abc import AsyncIterator, Iterator
from functools import lru_cache
from pathlib import Path

import httpx
import openai
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from edu_core.code_run import CodeRun, read_parts
from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatGenerationChunk, ChatResult
from langchain_openai import (
    AzureChatOpenAI,
    AzureOpenAIEmbeddings,
    ChatOpenAI,
    OpenAIEmbeddings,
)
from pydantic import PrivateAttr
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

GEMINI_OPENAI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
GEMINI_GENERATE_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)
GEMINI_DEFAULT_CHAT_MODEL = "gemini-3.5-flash"
GEMINI_DEFAULT_EMBEDDING_MODEL = "gemini-embedding-001"
OPENAI_DEFAULT_CHAT_MODEL = "gpt-4o"
OPENAI_DEFAULT_EMBEDDING_MODEL = "text-embedding-3-large"
AZURE_COGNITIVE_SCOPE = "https://cognitiveservices.azure.com/.default"
GOOGLE_CLOUD_SCOPE = "https://www.googleapis.com/auth/cloud-platform"
OPENAI_COMPATIBLE_PROVIDERS = ("gemini", "vertex", "openai")
GOOGLE_PROVIDERS = ("gemini", "vertex")

# Tasks that can use their own model
TUTOR = "tutor"
GENERATION = "generation"
MARKING = "marking"
OCR = "ocr"

# Errors that move a call on to the next fallback model
FALLBACK_ERRORS = (
    openai.RateLimitError,
    openai.InternalServerError,
    openai.APIConnectionError,
    openai.APITimeoutError,
)
# Retries per model when a fallback model is available after it
RETRIES_BEFORE_FALLBACK = 2


def _env_files() -> tuple[str, ...]:
    files: list[str] = []
    try:
        files.append(str(Path(__file__).resolve().parents[5] / ".env"))
    except IndexError:
        pass
    files.append(".env")
    return tuple(files)


class LLMSettings(BaseSettings):
    """Model provider settings."""

    model_config = SettingsConfigDict(
        env_file=_env_files(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    llm_provider: str = "azure"
    llm_api_key: str = ""
    gemini_api_key: str = ""
    llm_base_url: str = ""
    llm_chat_model: str = ""
    llm_tutor_model: str = ""
    llm_generation_model: str = ""
    llm_marking_model: str = ""
    llm_ocr_model: str = ""
    llm_fallback_models: str = ""
    llm_embedding_model: str = ""
    llm_embedding_dimensions: int | None = None
    # Retries (with backoff) on rate limits and transient errors. Kept low
    # because each model in the fallback chain retries in turn, so the attempts
    # multiply: three models at eight retries each is well over a hundred.
    llm_max_retries: int = 3
    # Seconds to wait for one response before giving up on it and letting the
    # retry or the fallback take over. Without a timeout a stalled connection
    # waits for ever, and a paper gathers every question before it finishes, so
    # one stuck call leaves the whole paper preparing indefinitely.
    llm_request_timeout: float = 90.0

    # Vertex AI
    google_cloud_project: str = ""
    vertex_location: str = "global"

    azure_openai_api_key: str = ""
    azure_openai_endpoint: str = ""
    azure_openai_chat_deployment: str = ""
    azure_openai_embedding_deployment: str = ""
    azure_openai_api_version: str = ""

    @property
    def provider(self) -> str:
        return self.llm_provider.strip().lower() or "azure"

    @property
    def is_openai_compatible(self) -> bool:
        return self.provider in OPENAI_COMPATIBLE_PROVIDERS

    @property
    def api_key(self) -> str:
        if self.provider == "gemini":
            return self.llm_api_key or self.gemini_api_key
        return self.llm_api_key

    @property
    def vertex_host(self) -> str:
        if self.vertex_location == "global":
            return "https://aiplatform.googleapis.com"
        return f"https://{self.vertex_location}-aiplatform.googleapis.com"

    @property
    def vertex_prefix(self) -> str:
        return (
            f"{self.vertex_host}/v1/projects/{self.google_cloud_project}"
            f"/locations/{self.vertex_location}"
        )

    @property
    def base_url(self) -> str | None:
        if self.llm_base_url:
            return self.llm_base_url
        if self.provider == "gemini":
            return GEMINI_OPENAI_BASE_URL
        if self.provider == "vertex":
            return f"{self.vertex_prefix}/endpoints/openapi"
        return None

    @property
    def chat_model(self) -> str:
        if self.llm_chat_model:
            return self.llm_chat_model
        if self.provider in GOOGLE_PROVIDERS:
            return GEMINI_DEFAULT_CHAT_MODEL
        return OPENAI_DEFAULT_CHAT_MODEL

    @property
    def embedding_model(self) -> str:
        if self.llm_embedding_model:
            return self.llm_embedding_model
        if self.provider in GOOGLE_PROVIDERS:
            return GEMINI_DEFAULT_EMBEDDING_MODEL
        return OPENAI_DEFAULT_EMBEDDING_MODEL

    @property
    def fallback_models(self) -> list[str]:
        return [m.strip() for m in self.llm_fallback_models.split(",") if m.strip()]

    def model_for(self, task: str) -> str:
        """Model name for a task, falling back to the general chat model."""
        per_task = {
            TUTOR: self.llm_tutor_model,
            GENERATION: self.llm_generation_model,
            MARKING: self.llm_marking_model,
            OCR: self.llm_ocr_model,
        }
        return per_task.get(task) or self.chat_model

    def api_model_name(self, model: str) -> str:
        """Model name as the endpoint expects it (Vertex uses ``google/<model>``)."""
        if self.provider == "vertex" and "/" not in model:
            return f"google/{model}"
        return model


@lru_cache
def get_llm_settings() -> LLMSettings:
    """Get cached model provider settings."""
    return LLMSettings()


class GoogleAccessToken:
    """Callable returning a fresh Google Cloud access token (for Vertex AI)."""

    def __init__(self) -> None:
        self._credentials = None
        self._lock = threading.Lock()

    def __call__(self) -> str:
        import google.auth
        from google.auth.transport.requests import Request

        with self._lock:
            if self._credentials is None:
                self._credentials, _ = google.auth.default(scopes=[GOOGLE_CLOUD_SCOPE])
            if not self._credentials.valid:
                self._credentials.refresh(Request())
            return self._credentials.token


@lru_cache
def _google_access_token() -> GoogleAccessToken:
    return GoogleAccessToken()


def _openai_compatible_api_key(settings: LLMSettings):
    if settings.provider == "vertex":
        return _google_access_token()
    return settings.api_key


def is_llm_configured(azure_endpoint: str | None = None) -> bool:
    """Whether a chat model can be created with the current settings."""
    settings = get_llm_settings()
    if settings.provider == "vertex":
        return bool(settings.google_cloud_project)
    if settings.is_openai_compatible:
        return bool(settings.api_key)
    return bool(azure_endpoint or settings.azure_openai_endpoint)


THOUGHT_SIGNATURES_KEY = "gemini_thought_signatures"


def _tool_call_signatures(tool_calls: list[dict] | None) -> dict[str, str]:
    signatures = {}
    for tool_call in tool_calls or []:
        google = (tool_call.get("extra_content") or {}).get("google") or {}
        if (signature := google.get("thought_signature")) and tool_call.get("id"):
            signatures[tool_call["id"]] = signature
    return signatures


def _attach_signatures(message: BaseMessage, signatures: dict[str, str]) -> None:
    if signatures:
        message.additional_kwargs[THOUGHT_SIGNATURES_KEY] = {
            **message.additional_kwargs.get(THOUGHT_SIGNATURES_KEY, {}),
            **signatures,
        }


class GeminiChatOpenAI(ChatOpenAI):
    """ChatOpenAI for Gemini's OpenAI-compatible endpoints (Gemini API and Vertex AI).

    - Thought signatures: Gemini 3 returns one with each tool call
      (``tool_calls[].extra_content.google.thought_signature``) and rejects the
      follow-up request unless it is sent back unchanged. ChatOpenAI drops that
      field, so it is kept in ``additional_kwargs`` and re-attached here.
    - Fallback: on rate limits or server errors the call is retried with the
      next model in the chain. Streams only fall back before the first chunk.
    """

    _fallback_model: "GeminiChatOpenAI | None" = PrivateAttr(default=None)

    def with_fallback(self, model: "GeminiChatOpenAI | None") -> "GeminiChatOpenAI":
        self._fallback_model = model
        return self

    def _warn_fallback(self, error: Exception) -> None:
        logger.warning(
            "Model %s failed (%s); falling back to %s",
            self.model_name,
            type(error).__name__,
            self._fallback_model.model_name if self._fallback_model else None,
        )

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        if self.streaming or self._fallback_model is None:
            # Streaming generation goes through _stream, which handles fallback
            return super()._generate(messages, stop, run_manager, **kwargs)
        try:
            return super()._generate(messages, stop, run_manager, **kwargs)
        except FALLBACK_ERRORS as e:
            self._warn_fallback(e)
            return self._fallback_model._generate(messages, stop, run_manager, **kwargs)

    async def _agenerate(
        self, messages, stop=None, run_manager=None, **kwargs
    ) -> ChatResult:
        if self.streaming or self._fallback_model is None:
            return await super()._agenerate(messages, stop, run_manager, **kwargs)
        try:
            return await super()._agenerate(messages, stop, run_manager, **kwargs)
        except FALLBACK_ERRORS as e:
            self._warn_fallback(e)
            return await self._fallback_model._agenerate(
                messages, stop, run_manager, **kwargs
            )

    def _stream(
        self, messages, stop=None, run_manager=None, **kwargs
    ) -> Iterator[ChatGenerationChunk]:
        started = False
        try:
            for chunk in super()._stream(messages, stop, run_manager, **kwargs):
                started = True
                yield chunk
        except FALLBACK_ERRORS as e:
            if started or self._fallback_model is None:
                raise
            self._warn_fallback(e)
            yield from self._fallback_model._stream(messages, stop, run_manager, **kwargs)

    async def _astream(
        self, messages, stop=None, run_manager=None, **kwargs
    ) -> AsyncIterator[ChatGenerationChunk]:
        started = False
        try:
            async for chunk in super()._astream(messages, stop, run_manager, **kwargs):
                started = True
                yield chunk
        except FALLBACK_ERRORS as e:
            if started or self._fallback_model is None:
                raise
            self._warn_fallback(e)
            async for chunk in self._fallback_model._astream(
                messages, stop, run_manager, **kwargs
            ):
                yield chunk

    def _convert_chunk_to_generation_chunk(
        self,
        chunk: dict,
        default_chunk_class: type,
        base_generation_info: dict | None,
    ) -> ChatGenerationChunk | None:
        generation_chunk = super()._convert_chunk_to_generation_chunk(
            chunk, default_chunk_class, base_generation_info
        )
        choices = chunk.get("choices") or []
        if generation_chunk is not None and choices:
            delta = choices[0].get("delta") or {}
            _attach_signatures(
                generation_chunk.message, _tool_call_signatures(delta.get("tool_calls"))
            )
        return generation_chunk

    def _create_chat_result(self, response, generation_info=None) -> ChatResult:
        result = super()._create_chat_result(response, generation_info)
        response_dict = response if isinstance(response, dict) else response.model_dump()
        for generation, choice in zip(
            result.generations, response_dict.get("choices") or [], strict=False
        ):
            message = choice.get("message") or {}
            _attach_signatures(
                generation.message, _tool_call_signatures(message.get("tool_calls"))
            )
        return result

    def _get_request_payload(self, input_, *, stop=None, **kwargs) -> dict:
        payload = super()._get_request_payload(input_, stop=stop, **kwargs)
        signatures: dict[str, str] = {}
        for message in self._convert_input(input_).to_messages():
            signatures.update(message.additional_kwargs.get(THOUGHT_SIGNATURES_KEY) or {})
        if signatures:
            for message in payload.get("messages", []):
                for tool_call in message.get("tool_calls") or []:
                    if signature := signatures.get(tool_call.get("id")):
                        tool_call["extra_content"] = {
                            "google": {"thought_signature": signature}
                        }
        return payload


class VertexEmbeddings(Embeddings):
    """Gemini embeddings through Vertex AI's native ``:predict`` API.

    Vertex's OpenAI-compatible endpoint returns server errors for embeddings, so
    this calls the native API. Stored chunks and search queries use the matching
    retrieval task types, which improves search quality.
    """

    batch_size = 20

    def __init__(self, url: str, max_retries: int, dimensions: int | None = None):
        self.url = url
        self.max_retries = max_retries
        self.dimensions = dimensions

    def _post(self, body: dict) -> dict:
        for attempt in range(self.max_retries + 1):
            last_attempt = attempt == self.max_retries
            try:
                response = httpx.post(
                    self.url,
                    headers={"Authorization": f"Bearer {_google_access_token()()}"},
                    json=body,
                    timeout=120,
                )
            except httpx.TransportError:
                if last_attempt:
                    raise
            else:
                retryable = response.status_code == 429 or response.status_code >= 500
                if response.status_code < 400:
                    return response.json()
                if not retryable or last_attempt:
                    response.raise_for_status()
            time.sleep(min(2**attempt, 30))
        raise RuntimeError("unreachable")

    def _embed(self, texts: list[str], task_type: str) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self.batch_size):
            body: dict = {
                "instances": [
                    {"content": text, "task_type": task_type}
                    for text in texts[start : start + self.batch_size]
                ]
            }
            if self.dimensions:
                body["parameters"] = {"outputDimensionality": self.dimensions}
            vectors.extend(
                prediction["embeddings"]["values"]
                for prediction in self._post(body)["predictions"]
            )
        return vectors

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embed(list(texts), "RETRIEVAL_DOCUMENT")

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text], "RETRIEVAL_QUERY")[0]


def _azure_auth_kwargs(settings: LLMSettings) -> dict:
    if settings.azure_openai_api_key:
        return {"api_key": settings.azure_openai_api_key}
    return {
        "azure_ad_token_provider": get_bearer_token_provider(
            DefaultAzureCredential(), AZURE_COGNITIVE_SCOPE
        )
    }


def _create_google_chat_chain(
    settings: LLMSettings, task: str, streaming: bool, temperature: float
) -> GeminiChatOpenAI:
    models = [settings.model_for(task)]
    models += [m for m in settings.fallback_models if m not in models]

    chain: GeminiChatOpenAI | None = None
    # Build from the last model backwards so each links to the next one
    for index, model in reversed(list(enumerate(models))):
        is_last = index == len(models) - 1
        chain = GeminiChatOpenAI(
            model=settings.api_model_name(model),
            api_key=_openai_compatible_api_key(settings),
            base_url=settings.base_url,
            temperature=temperature,
            streaming=streaming,
            timeout=settings.llm_request_timeout,
            max_retries=settings.llm_max_retries
            if is_last
            else min(RETRIES_BEFORE_FALLBACK, settings.llm_max_retries),
        ).with_fallback(chain)
    return chain


def create_chat_model(
    *,
    task: str = GENERATION,
    streaming: bool = False,
    temperature: float = 0.25,
    azure_deployment: str | None = None,
    azure_endpoint: str | None = None,
    azure_api_version: str | None = None,
) -> BaseChatModel:
    """Create a chat model for the configured provider.

    Args:
        task: What the model is used for (``TUTOR``, ``GENERATION``, ``MARKING``, ``OCR``)
        streaming: Whether to stream responses
        temperature: Sampling temperature
        azure_deployment: Azure only; defaults to ``AZURE_OPENAI_CHAT_DEPLOYMENT``
        azure_endpoint: Azure only; defaults to ``AZURE_OPENAI_ENDPOINT``
        azure_api_version: Azure only; defaults to ``AZURE_OPENAI_API_VERSION``
    """
    settings = get_llm_settings()

    if settings.provider in GOOGLE_PROVIDERS:
        return _create_google_chat_chain(settings, task, streaming, temperature)

    if settings.is_openai_compatible:
        return ChatOpenAI(
            model=settings.model_for(task),
            api_key=settings.api_key,
            base_url=settings.base_url,
            temperature=temperature,
            streaming=streaming,
            timeout=settings.llm_request_timeout,
            max_retries=settings.llm_max_retries,
        )

    kwargs = {
        "azure_deployment": azure_deployment
        or settings.azure_openai_chat_deployment,
        "azure_endpoint": azure_endpoint or settings.azure_openai_endpoint,
        "temperature": temperature,
        "streaming": streaming,
        "timeout": settings.llm_request_timeout,
        "max_retries": settings.llm_max_retries,
        **_azure_auth_kwargs(settings),
    }
    api_version = azure_api_version or settings.azure_openai_api_version
    if api_version:
        kwargs["api_version"] = api_version
    return AzureChatOpenAI(**kwargs)


def create_embeddings(
    *,
    azure_deployment: str | None = None,
    azure_endpoint: str | None = None,
    azure_api_version: str | None = None,
) -> Embeddings:
    """Create an embeddings model for the configured provider.

    The database stores 3072-dimensional vectors, so the model must produce
    vectors of that size (set ``LLM_EMBEDDING_DIMENSIONS`` if it supports it).
    """
    settings = get_llm_settings()

    if settings.provider == "vertex":
        model = settings.embedding_model.removeprefix("google/")
        return VertexEmbeddings(
            url=f"{settings.vertex_prefix}/publishers/google/models/{model}:predict",
            max_retries=settings.llm_max_retries,
            dimensions=settings.llm_embedding_dimensions,
        )

    if settings.is_openai_compatible:
        kwargs = {
            "model": settings.api_model_name(settings.embedding_model),
            "api_key": _openai_compatible_api_key(settings),
            "base_url": settings.base_url,
            # Non-OpenAI endpoints expect raw text, not tiktoken token arrays.
            "check_embedding_ctx_length": False,
            "chunk_size": 100,
            "max_retries": settings.llm_max_retries,
        }
        if settings.llm_embedding_dimensions:
            kwargs["dimensions"] = settings.llm_embedding_dimensions
        return OpenAIEmbeddings(**kwargs)

    kwargs = {
        "azure_deployment": azure_deployment
        or settings.azure_openai_embedding_deployment,
        "azure_endpoint": azure_endpoint or settings.azure_openai_endpoint,
        **_azure_auth_kwargs(settings),
    }
    api_version = azure_api_version or settings.azure_openai_api_version
    if api_version:
        kwargs["api_version"] = api_version
    return AzureOpenAIEmbeddings(**kwargs)


def supports_file_input() -> bool:
    """Whether ``generate_from_file`` can be used (Gemini API or Vertex AI)."""
    return get_llm_settings().provider in GOOGLE_PROVIDERS and is_llm_configured()


def supports_code_execution() -> bool:
    """Whether ``run_code`` can be used (Gemini API or Vertex AI)."""
    return supports_file_input()


def _native_generate(body: dict, task: str, timeout: float, what: str) -> list[dict]:
    """Post to Gemini's own ``generateContent`` and return the reply's parts.

    The chat runs on the OpenAI-compatible endpoint, which cannot express
    Google's own tools - reading a PDF directly, running code in a sandbox - so
    the few things that need one come through here instead. Keeping it to a
    separate call is deliberate: the chat's hot path is untouched and pays
    nothing for a feature most turns never use.

    Tries the task's model, then ``LLM_FALLBACK_MODELS``, on a rate limit or a
    server error. ``what`` only names the work in the log line.
    """
    settings = get_llm_settings()
    models = [settings.model_for(task)]
    models += [m for m in settings.fallback_models if m not in models]
    last_error: Exception | None = None

    for model in models:
        if settings.provider == "vertex":
            url = f"{settings.vertex_prefix}/publishers/google/models/{model}:generateContent"
            headers = {"Authorization": f"Bearer {_google_access_token()()}"}
        else:
            url = GEMINI_GENERATE_URL.format(model=model)
            headers = {"x-goog-api-key": settings.api_key}

        try:
            response = httpx.post(url, headers=headers, json=body, timeout=timeout)
        except httpx.TransportError as e:
            last_error = e
            continue
        if response.status_code == 429 or response.status_code >= 500:
            last_error = RuntimeError(
                f"{model}: HTTP {response.status_code} {response.text[:200]}"
            )
            logger.warning("%s with %s failed; trying next model", what, model)
            continue
        response.raise_for_status()

        candidates = response.json().get("candidates") or []
        if not candidates:
            raise RuntimeError(f"Gemini returned no content for {what}")
        return candidates[0].get("content", {}).get("parts", []) or []

    raise RuntimeError(f"All models failed for {what}: {last_error}")


def generate_from_file(
    data: bytes, mime_type: str, prompt: str, task: str = OCR, timeout: float = 600
) -> str:
    """Send a file (PDF or image) plus a prompt to Gemini and return the text reply.

    Uses the native ``generateContent`` API, which reads PDFs and images directly.
    """
    if not supports_file_input():
        raise RuntimeError("File input needs LLM_PROVIDER=gemini or vertex")

    body = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "inlineData": {
                            "mimeType": mime_type,
                            "data": base64.b64encode(data).decode(),
                        }
                    },
                    {"text": prompt},
                ],
            }
        ]
    }
    parts = _native_generate(body, task, timeout, "file input")
    return "".join(part.get("text", "") for part in parts)


def run_code(prompt: str, task: str = GENERATION, timeout: float = 180) -> CodeRun:
    """Ask the model to work something out by writing Python, and run it.

    Google runs the sandbox, not us: no network, thirty seconds, numpy, pandas
    and matplotlib already there and nothing installable. That is the whole
    reason to use it rather than execute a model's code ourselves - there is no
    sandbox of our own to get wrong, and no package to keep patched.

    A figure drawn in there comes back as PNG bytes in the reply. A model
    cannot draw a correct labelled graph; it can write the ten lines of
    matplotlib that do, and then the geometry is Python's rather than a guess.

    The call is made with temperature 0. Drawing is not a creative task, and
    the same question twice should give the same figure.
    """
    if not supports_code_execution():
        raise RuntimeError("Code execution needs LLM_PROVIDER=gemini or vertex")

    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "tools": [{"codeExecution": {}}],
        "generationConfig": {"temperature": 0},
    }
    return read_parts(_native_generate(body, task, timeout, "code execution"))
