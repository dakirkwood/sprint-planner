"""Tests for application configuration."""

import os
import pytest
from pydantic_settings import BaseSettings

from app.core.config import Settings, get_settings


class TestSettings:
    """Test application settings."""

    def test_default_settings(self):
        """Test default setting values."""
        settings = Settings()

        assert settings.APP_NAME == "Drupal Ticket Generator"
        assert settings.APP_DEBUG_MODE is False
        assert settings.APP_VERSION == "0.1.0"

    def test_database_url_default(self):
        """Test default database URL."""
        settings = Settings()

        assert "postgresql+asyncpg" in settings.DATABASE_URL
        assert "drupal_ticket_gen" in settings.DATABASE_URL

    def test_redis_url_default(self):
        """Test default Redis URL."""
        settings = Settings()

        assert settings.REDIS_URL == "redis://localhost:6379/0"

    def test_arq_settings_defaults(self):
        """Test default ARQ settings."""
        settings = Settings()

        assert settings.ARQ_MAX_JOBS == 2
        assert settings.ARQ_JOB_TIMEOUT == 1800
        assert settings.ARQ_KEEP_RESULT == 3600
        assert settings.ARQ_RETRY_DELAY == 30

    def test_session_retention_default(self):
        """Test default session retention."""
        settings = Settings()

        assert settings.SESSION_RETENTION_DAYS == 7
        assert settings.AUDIT_LOG_RETENTION_DAYS == 90
        assert settings.TOKEN_GRACE_PERIOD_DAYS == 30

    def test_optional_settings_are_optional(self):
        """Test optional settings are typed as Optional."""
        # These should be typed as Optional[str] and not required
        settings = Settings()

        # Just verify these attributes exist and can be accessed
        # without raising errors (they may be None or set from environment)
        _ = settings.JIRA_CLIENT_ID
        _ = settings.JIRA_CLIENT_SECRET
        _ = settings.OPENAI_API_KEY
        _ = settings.ANTHROPIC_API_KEY
        _ = settings.TOKEN_ENCRYPTION_KEY


class TestGetSettings:
    """Test get_settings function."""

    def test_get_settings_returns_settings_instance(self):
        """get_settings returns a Settings instance."""
        settings = get_settings()

        assert isinstance(settings, Settings)

    def test_get_settings_is_cached(self):
        """get_settings returns cached instance."""
        # Clear cache first
        get_settings.cache_clear()

        settings1 = get_settings()
        settings2 = get_settings()

        # Should be the same object due to caching
        assert settings1 is settings2
