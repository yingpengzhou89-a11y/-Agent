from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Interview Copilot Agent"
    app_env: str = "development"

    # Production must override this value via environment variable.
    app_secret_key: str = Field(
        default="dev-only-change-me",
        min_length=1,
    )

    jwt_algorithm: str = "HS256"

    access_token_expire_minutes: int = Field(
        default=60,
        ge=5,
        le=1440,
    )

    # Rate limiting
    rate_limit_enabled: bool = True

    # Default limit applied to API routes unless a route has a more specific limit.
    rate_limit_default: str = "120/minute"

    # Authentication endpoint limits.
    rate_limit_login: str = "10/minute"
    rate_limit_register: str = "5/hour"

    # Development defaults to in-memory storage.
    # Production can override with Redis, e.g.:
    # redis://redis:6379/0
    rate_limit_storage_uri: str = "memory://"

    database_url: str = (
        "postgresql+asyncpg://interview:interview@localhost:5432/interview_copilot"
    )

    chat_base_url: str | None = None
    chat_api_key: str | None = None
    chat_model: str | None = None

    llm_timeout_seconds: int = Field(
        default=90,
        ge=1,
        le=300,
    )

    llm_max_retries: int = Field(
        default=2,
        ge=0,
        le=5,
    )

    embedding_base_url: str | None = None
    embedding_api_key: str | None = None
    embedding_model: str = "text-embedding-v4"

    embedding_dimensions: int = Field(
        default=1024,
        ge=1024,
        le=1024,
    )

    max_upload_mb: int = Field(
        default=20,
        ge=1,
        le=100,
    )

    storage_dir: str = "data/uploads"

    model_config = SettingsConfigDict(
        env_file="../.env",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
