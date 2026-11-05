from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Shared settings live in the repository root .env; a .env next to the
# service (the working directory) can override them.
ROOT_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    """API settings loaded from environment variables and .env files."""

    model_config = SettingsConfigDict(
        env_file=(ROOT_ENV_FILE, ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Server port (Cloud Run sets PORT)
    port: int = 8000

    # Database (Supabase Postgres)
    database_url: str = ""

    # Login tokens: Google Identity Platform (Firebase Auth) when set, else Supabase
    firebase_project_id: str = ""

    # Supabase Auth + Storage (local development)
    supabase_url: str = ""
    supabase_jwt_secret: str = ""
    supabase_service_role_key: str = ""

    # File storage: "gcs" (Google Cloud Storage) or "supabase"
    storage_backend: str = "supabase"
    storage_bucket: str = "documents"

    # Azure OpenAI (only used when LLM_PROVIDER=azure, see edu_ai.llm)
    azure_openai_chat_deployment: str = ""
    azure_openai_endpoint: str = ""
    azure_openai_api_version: str = ""
    azure_openai_embedding_deployment: str = ""

    # Usage Limits (per day per user); quiz generations also count SRQs
    max_chat_messages_per_day: int = 100
    max_flashcard_generations_per_day: int = 20
    max_quiz_generations_per_day: int = 30
    max_document_uploads_per_day: int = 10

    # Comma-separated emails of subject teachers who review the shared content
    reviewer_emails: str = ""
    # Comma-separated emails allowed to manage accounts. Deliberately not a
    # column on the user: a flag in the database can be set by anything that
    # can write to the database, whereas changing this needs a deploy.
    admin_emails: str = ""


    @property
    def reviewers(self) -> set[str]:
        return {e.strip().lower() for e in self.reviewer_emails.split(",") if e.strip()}

    @property
    def admins(self) -> set[str]:
        return {e.strip().lower() for e in self.admin_emails.split(",") if e.strip()}


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
