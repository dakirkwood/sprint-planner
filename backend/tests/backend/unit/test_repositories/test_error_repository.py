# tests/backend/unit/test_repositories/test_error_repository.py
"""
Tests for ErrorRepository operations.
"""
import pytest

from app.models.session import Session
from app.repositories.sqlalchemy.error_repository import SQLAlchemyErrorRepository
from app.schemas.base import ErrorCategory, ErrorSeverity, EventCategory, AuditLevel


@pytest.mark.phase1
@pytest.mark.repositories
class TestErrorRepositorySessionErrors:
    """Test session error operations."""

    @pytest.fixture
    async def session_id(self, db_session, sample_session_data):
        session = Session(**sample_session_data)
        db_session.add(session)
        await db_session.flush()
        return session.id

    @pytest.fixture
    def repo(self, db_session):
        return SQLAlchemyErrorRepository(db_session)

    @pytest.mark.asyncio
    async def test_create_error(self, repo, session_id):
        """Should create session error record."""
        error_data = {
            "session_id": session_id,
            "category": ErrorCategory.USER_FIXABLE,
            "severity": ErrorSeverity.BLOCKING,
            "user_message": "Test error message",
            "error_code": "TEST_ERROR"
        }

        error = await repo.create_error(error_data)

        assert error.id is not None
        assert error.user_message == "Test error message"

    @pytest.mark.asyncio
    async def test_get_errors_by_session(self, repo, session_id):
        """Should get all errors for a session."""
        await repo.create_error({
            "session_id": session_id,
            "category": ErrorCategory.USER_FIXABLE,
            "severity": ErrorSeverity.BLOCKING,
            "user_message": "Error 1"
        })
        await repo.create_error({
            "session_id": session_id,
            "category": ErrorCategory.TEMPORARY,
            "severity": ErrorSeverity.WARNING,
            "user_message": "Error 2"
        })

        errors = await repo.get_errors_by_session(session_id)

        assert len(errors) == 2

    @pytest.mark.asyncio
    async def test_get_errors_by_session_filtered(self, repo, session_id):
        """Should filter errors by category."""
        await repo.create_error({
            "session_id": session_id,
            "category": ErrorCategory.USER_FIXABLE,
            "severity": ErrorSeverity.BLOCKING,
            "user_message": "User error"
        })
        await repo.create_error({
            "session_id": session_id,
            "category": ErrorCategory.TEMPORARY,
            "severity": ErrorSeverity.WARNING,
            "user_message": "Temp error"
        })

        user_errors = await repo.get_errors_by_session(session_id, category=ErrorCategory.USER_FIXABLE)

        assert len(user_errors) == 1
        assert user_errors[0].category == ErrorCategory.USER_FIXABLE

    @pytest.mark.asyncio
    async def test_has_blocking_errors(self, repo, session_id):
        """Should check for blocking errors."""
        # No errors yet
        assert await repo.has_blocking_errors(session_id) is False

        # Add non-blocking error
        await repo.create_error({
            "session_id": session_id,
            "category": ErrorCategory.TEMPORARY,
            "severity": ErrorSeverity.WARNING,
            "user_message": "Warning"
        })
        assert await repo.has_blocking_errors(session_id) is False

        # Add blocking error
        await repo.create_error({
            "session_id": session_id,
            "category": ErrorCategory.USER_FIXABLE,
            "severity": ErrorSeverity.BLOCKING,
            "user_message": "Blocking error"
        })
        assert await repo.has_blocking_errors(session_id) is True


@pytest.mark.phase1
@pytest.mark.repositories
class TestErrorRepositoryAuditLog:
    """Test audit log operations."""

    @pytest.fixture
    async def session_id(self, db_session, sample_session_data):
        session = Session(**sample_session_data)
        db_session.add(session)
        await db_session.flush()
        return session.id

    @pytest.fixture
    def repo(self, db_session):
        return SQLAlchemyErrorRepository(db_session)

    @pytest.mark.asyncio
    async def test_log_event(self, repo, session_id, sample_session_data):
        """Should log an audit event."""
        log = await repo.log_event(
            event_type="session_created",
            category=EventCategory.SESSION,
            description="Session was created",
            session_id=session_id,
            jira_user_id=sample_session_data["jira_user_id"]
        )

        assert log.id is not None
        assert log.event_type == "session_created"
        assert log.category == EventCategory.SESSION

    @pytest.mark.asyncio
    async def test_get_session_timeline(self, repo, session_id):
        """Should get chronological timeline for session."""
        await repo.log_event(
            event_type="event_1",
            category=EventCategory.SESSION,
            description="First event",
            session_id=session_id
        )
        await repo.log_event(
            event_type="event_2",
            category=EventCategory.UPLOAD,
            description="Second event",
            session_id=session_id
        )

        timeline = await repo.get_session_timeline(session_id)

        assert len(timeline) == 2
        # Should be in chronological order
        assert timeline[0].event_type == "event_1"
        assert timeline[1].event_type == "event_2"

    @pytest.mark.asyncio
    async def test_get_user_activity(self, repo, sample_session_data):
        """Should get recent activity for a user."""
        jira_user_id = sample_session_data["jira_user_id"]

        await repo.log_event(
            event_type="login",
            category=EventCategory.SESSION,
            description="User logged in",
            jira_user_id=jira_user_id
        )
        await repo.log_event(
            event_type="upload",
            category=EventCategory.UPLOAD,
            description="User uploaded file",
            jira_user_id=jira_user_id
        )

        activity = await repo.get_user_activity(jira_user_id)

        assert len(activity) == 2

    @pytest.mark.asyncio
    async def test_get_audit_events_filtered(self, repo, session_id):
        """Should filter audit events by criteria."""
        await repo.log_event(
            event_type="session_event",
            category=EventCategory.SESSION,
            description="Session event",
            session_id=session_id
        )
        await repo.log_event(
            event_type="upload_event",
            category=EventCategory.UPLOAD,
            description="Upload event",
            session_id=session_id
        )

        session_events = await repo.get_audit_events(session_id=session_id, category=EventCategory.SESSION)

        assert len(session_events) == 1
        assert session_events[0].category == EventCategory.SESSION
