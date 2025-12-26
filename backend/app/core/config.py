"""Application configuration using pydantic-settings."""

from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "Drupal Ticket Generator"
    APP_DEBUG_MODE: bool = False
    APP_VERSION: str = "0.1.0"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/drupal_ticket_gen"

    # Redis Configuration
    REDIS_URL: str = "redis://localhost:6379/0"

    # ARQ Worker Configuration
    ARQ_MAX_JOBS: int = 2
    ARQ_JOB_TIMEOUT: int = 1800  # 30 minutes
    ARQ_KEEP_RESULT: int = 3600  # 1 hour
    ARQ_RETRY_DELAY: int = 30  # Base delay between retries (seconds)

    # Jira OAuth
    JIRA_CLIENT_ID: Optional[str] = None
    JIRA_CLIENT_SECRET: Optional[str] = None
    JIRA_REDIRECT_URI: Optional[str] = None

    # LLM Providers
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None

    # Security
    TOKEN_ENCRYPTION_KEY: Optional[str] = None

    # Session & Cleanup
    SESSION_RETENTION_DAYS: int = 7
    AUDIT_LOG_RETENTION_DAYS: int = 90
    TOKEN_GRACE_PERIOD_DAYS: int = 30

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
