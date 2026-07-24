from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Interview Copilot Agent"
    app_env: str = "development"
    # Local MVP can start without a secret; production deployment must override it.
    app_secret_key: str = Field(default="dev-only-change-me", min_length=1)
    database_url: str = "postgresql+asyncpg://interview:interview@localhost:5432/interview_copilot"
    chat_base_url: str | None = None
    chat_api_key: str | None = None
    chat_model: str | None = None
    llm_timeout_seconds: int = Field(default=90, ge=1, le=300)
    llm_max_retries: int = Field(default=2, ge=0, le=5)
    embedding_base_url: str | None = None
    embedding_api_key: str | None = None
    embedding_model: str = "text-embedding-v4"
    embedding_dimensions: int = Field(default=1024, ge=1024, le=1024)
    max_upload_mb: int = Field(default=20, ge=1, le=100)
    storage_dir: str = "data/uploads"

    model_config = SettingsConfigDict(env_file="../.env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
