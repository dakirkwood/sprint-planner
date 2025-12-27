# app/core/config.py
"""
Application configuration using Pydantic Settings.
Loads settings from environment variables with sensible defaults.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Application
    APP_NAME: str = "Drupal Ticket Generator"
    APP_VERSION: str = "0.1.0"
    APP_DEBUG_MODE: bool = False
    APP_SECRET_KEY: str = "change-me-in-production"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/drupal_ticket_gen"

    # Redis/ARQ
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: int = 0

    # Jira OAuth
    JIRA_CLIENT_ID: Optional[str] = None
    JIRA_CLIENT_SECRET: Optional[str] = None
    JIRA_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/callback"

    # LLM Providers
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None

    # Session Settings
    SESSION_RETENTION_DAYS: int = 7
    AUDIT_LOG_RETENTION_DAYS: int = 90

    # File Upload
    MAX_FILE_SIZE_MB: int = 10
    UPLOAD_DIRECTORY: str = "uploads"

    @property
    def redis_url(self) -> str:
        """Construct Redis URL from components."""
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()
