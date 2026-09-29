from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Shared settings live in the repository root .env; a .env next to the
# service (the working directory) can override them.
ROOT_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    """Worker settings loaded from environment variables and .env files."""

    model_config = SettingsConfigDict(
        env_file=(ROOT_ENV_FILE, ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database (Supabase Postgres)
    database_url: str = ""

    # File storage: "gcs" (Google Cloud Storage) or "supabase" (local development)
    storage_backend: str = "supabase"
    storage_bucket: str = "documents"
    supabase_url: str = ""
    supabase_service_role_key: str = ""

    # Azure Content Understanding (optional; documents are read locally when unset)
    azure_cu_endpoint: str = ""
    azure_cu_key: str = ""
    azure_cu_analyzer_id: str = "prebuilt-documentAnalyzer"

    # Azure OpenAI (only used when LLM_PROVIDER=azure, see edu_ai.llm)
    azure_openai_endpoint: str = ""
    azure_openai_chat_deployment: str = "gpt-4o-mini"
    azure_openai_embedding_deployment: str = "text-embedding-3-large"
    azure_openai_api_version: str = "2024-12-01-preview"

    # Number of jobs processed in parallel
    worker_concurrency: int = 5
    # Poll the jobs table continuously. Turn off on Cloud Run when the worker scales
    # to zero and is woken by Cloud Scheduler calling POST /drain instead.
    worker_poll: bool = True
    # Seconds between polls of the jobs table when it is empty
    worker_poll_interval: float = 2.0
    # HTTP port for /health and /drain (Cloud Run sets PORT); 0 disables the server
    port: int = 0


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
