# tests/conftest.py
"""
Shared test fixtures for the Drupal Ticket Generator.
Provides async database session, test engine, and sample data fixtures.
"""
import pytest
import asyncio
from typing import AsyncGenerator
from uuid import uuid4
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# Use in-memory SQLite for tests (faster, no external deps)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    """Create test database engine."""
    from app.models.base import Base

    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Drop all tables after tests
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session with transaction rollback."""
    async_session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session_factory() as session:
        yield session
        await session.rollback()


@pytest.fixture
def sample_session_data():
    """Sample data for creating a session."""
    return {
        "jira_user_id": "test-user-123",
        "jira_display_name": "Test User",
        "site_name": "Test University",
        "site_description": "Test site for unit tests",
        "llm_provider_choice": "openai",
        "jira_project_key": "TEST"
    }


@pytest.fixture
def sample_ticket_data():
    """Sample data for creating a ticket."""
    return {
        "title": "Configure Content Type: Article",
        "description": "## Issue\nConfigure the Article content type...",
        "entity_group": "Content",
        "user_order": 1,
        "csv_source_files": [{"filename": "bundles.csv", "rows": [1, 2]}]
    }


@pytest.fixture
def sample_uploaded_file_data():
    """Sample data for creating an uploaded file."""
    return {
        "original_filename": "bundles.csv",
        "stored_filename": f"{uuid4()}.csv",
        "file_size": 1024,
        "mime_type": "text/csv",
        "csv_type": "bundles",
        "entity_count": 10
    }


@pytest.fixture
def sample_auth_token_data():
    """Sample data for creating auth tokens."""
    return {
        "jira_user_id": "test-user-123",
        "access_token_encrypted": b"encrypted_access_token",
        "refresh_token_encrypted": b"encrypted_refresh_token",
        "granted_scopes": ["read:jira-work", "write:jira-work"]
    }
