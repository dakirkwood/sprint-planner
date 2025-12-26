"""Shared pytest fixtures for all tests."""

import pytest
import pytest_asyncio
from typing import AsyncGenerator
from uuid import uuid4
from datetime import datetime

from sqlalchemy import JSON, TypeDecorator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker


# Custom type that works with both PostgreSQL (JSONB) and SQLite (JSON)
class JSONB_Compatible(TypeDecorator):
    """JSONB type that falls back to JSON for SQLite."""
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            from sqlalchemy.dialects.postgresql import JSONB
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(JSON())


# Monkey-patch the JSONB import in models to use our compatible type
import sqlalchemy.dialects.postgresql
sqlalchemy.dialects.postgresql.JSONB = JSONB_Compatible  # type: ignore

from app.models.base import Base
from app.models import (
    Session,
    SessionTask,
    SessionValidation,
    UploadedFile,
    Ticket,
    TicketDependency,
    Attachment,
    JiraAuthToken,
    JiraProjectContext,
    SessionError,
    AuditLog,
)
from app.schemas.base import (
    SessionStage,
    SessionStatus,
    TaskType,
    TaskStatus,
    FileValidationStatus,
    AdfValidationStatus,
    JiraUploadStatus,
    ErrorCategory,
    ErrorSeverity,
    EventCategory,
    AuditLevel,
)

# Test database URL - uses SQLite for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Drop all tables after tests
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session with transaction rollback."""
    async_session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_factory() as session:
        yield session
        await session.rollback()


# =============================================================================
# SESSION FIXTURES
# =============================================================================


@pytest.fixture
def sample_session_data():
    """Sample data for creating a session."""
    return {
        "jira_user_id": "test-user-123",
        "jira_display_name": "Test User",
        "site_name": "Test University",
        "site_description": "Test site for unit tests",
        "llm_provider_choice": "openai",
        "jira_project_key": "TEST",
    }


@pytest_asyncio.fixture
async def sample_session(db_session, sample_session_data):
    """Create a sample session in the database."""
    session = Session(**sample_session_data)
    db_session.add(session)
    await db_session.flush()
    return session


# =============================================================================
# TICKET FIXTURES
# =============================================================================


@pytest.fixture
def sample_ticket_data():
    """Sample data for creating a ticket."""
    return {
        "title": "Configure Content Type: Article",
        "description": "## Issue\nConfigure the Article content type...",
        "entity_group": "Content",
        "user_order": 1,
        "csv_source_files": [{"filename": "bundles.csv", "rows": [1, 2]}],
    }


@pytest_asyncio.fixture
async def sample_ticket(db_session, sample_session, sample_ticket_data):
    """Create a sample ticket in the database."""
    ticket = Ticket(
        session_id=sample_session.id,
        **sample_ticket_data,
    )
    db_session.add(ticket)
    await db_session.flush()
    return ticket


# =============================================================================
# UPLOAD FIXTURES
# =============================================================================


@pytest.fixture
def sample_file_data():
    """Sample data for creating an uploaded file."""
    return {
        "filename": "test_bundles.csv",
        "file_size_bytes": 1024,
        "parsed_content": {
            "headers": ["id", "name", "description"],
            "rows": [
                {"id": "1", "name": "Article", "description": "Article content type"},
                {"id": "2", "name": "Page", "description": "Basic page"},
            ],
        },
        "row_count": 2,
        "csv_type": "bundles",
    }


@pytest_asyncio.fixture
async def sample_uploaded_file(db_session, sample_session, sample_file_data):
    """Create a sample uploaded file in the database."""
    uploaded_file = UploadedFile(
        session_id=sample_session.id,
        **sample_file_data,
    )
    db_session.add(uploaded_file)
    await db_session.flush()
    return uploaded_file


# =============================================================================
# AUTH FIXTURES
# =============================================================================


@pytest.fixture
def sample_auth_token_data():
    """Sample data for creating an auth token."""
    return {
        "jira_user_id": "test-user-123",
        "encrypted_access_token": "encrypted_access_token_value",
        "encrypted_refresh_token": "encrypted_refresh_token_value",
        "token_expires_at": datetime(2025, 12, 31, 23, 59, 59),
        "granted_scopes": ["read:jira-work", "write:jira-work"],
    }


@pytest.fixture
def sample_project_context_data():
    """Sample data for creating project context."""
    return {
        "project_key": "TEST",
        "project_name": "Test Project",
        "can_create_tickets": True,
        "can_assign_tickets": True,
        "available_sprints": [
            {"name": "Sprint 1", "state": "active"},
            {"name": "Sprint 2", "state": "future"},
        ],
        "team_members": [
            {
                "account_id": "user-1",
                "display_name": "John Doe",
                "email": "john@example.com",
                "active": True,
            },
            {
                "account_id": "user-2",
                "display_name": "Jane Smith",
                "email": "jane@example.com",
                "active": True,
            },
        ],
    }


# =============================================================================
# ERROR FIXTURES
# =============================================================================


@pytest.fixture
def sample_error_data():
    """Sample data for creating a session error."""
    return {
        "error_category": ErrorCategory.USER_FIXABLE.value,
        "severity": ErrorSeverity.BLOCKING.value,
        "operation_stage": "upload",
        "user_message": "Invalid CSV format",
        "recovery_actions": {"actions": ["Re-upload the file", "Check CSV format"]},
        "technical_details": {"line": 5, "error": "Missing header"},
        "error_code": "INVALID_CSV_FORMAT",
    }


@pytest.fixture
def sample_audit_log_data():
    """Sample data for creating an audit log."""
    return {
        "event_type": "session_created",
        "event_category": EventCategory.SESSION.value,
        "description": "Session created for user test-user-123",
        "jira_user_id": "test-user-123",
    }
