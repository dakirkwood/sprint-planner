"""Tests for SQLAlchemy error repository."""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from app.repositories.sqlalchemy.error_repository import SQLAlchemyErrorRepository
from app.models.error import SessionError, AuditLog
from app.schemas.base import ErrorCategory, ErrorSeverity, EventCategory, AuditLevel


class TestErrorCreation:
    """Test error creation methods."""

    @pytest.mark.asyncio
    async def test_create_error(self, db_session, sample_session, sample_error_data):
        """Create a session error."""
        repo = SQLAlchemyErrorRepository(db_session)
        sample_error_data["session_id"] = sample_session.id

        error = await repo.create_error(sample_error_data)

        assert error.id is not None
        assert error.error_category == ErrorCategory.USER_FIXABLE.value
        assert error.severity == ErrorSeverity.BLOCKING.value

    @pytest.mark.asyncio
    async def test_create_error_defaults(self, db_session, sample_session):
        """Create error with default values."""
        repo = SQLAlchemyErrorRepository(db_session)

        error = await repo.create_error({
            "session_id": sample_session.id,
            "error_category": ErrorCategory.TEMPORARY.value,
            "operation_stage": "processing",
            "user_message": "An error occurred",
        })

        assert error.severity == ErrorSeverity.BLOCKING.value
        assert error.recovery_actions == {"actions": []}


class TestErrorRetrieval:
    """Test error retrieval methods."""

    @pytest.mark.asyncio
    async def test_get_errors_by_session(self, db_session, sample_session):
        """Get all errors for a session."""
        repo = SQLAlchemyErrorRepository(db_session)

        await repo.create_error({
            "session_id": sample_session.id,
            "error_category": ErrorCategory.USER_FIXABLE.value,
            "operation_stage": "upload",
            "user_message": "Error 1",
        })
        await repo.create_error({
            "session_id": sample_session.id,
            "error_category": ErrorCategory.TEMPORARY.value,
            "operation_stage": "processing",
            "user_message": "Error 2",
        })

        errors = await repo.get_errors_by_session(sample_session.id)

        assert len(errors) == 2

    @pytest.mark.asyncio
    async def test_get_errors_by_session_filtered(self, db_session, sample_session):
        """Get errors filtered by category."""
        repo = SQLAlchemyErrorRepository(db_session)

        await repo.create_error({
            "session_id": sample_session.id,
            "error_category": ErrorCategory.USER_FIXABLE.value,
            "operation_stage": "upload",
            "user_message": "User error",
        })
        await repo.create_error({
            "session_id": sample_session.id,
            "error_category": ErrorCategory.TEMPORARY.value,
            "operation_stage": "processing",
            "user_message": "System error",
        })

        errors = await repo.get_errors_by_session(
            sample_session.id,
            category=ErrorCategory.USER_FIXABLE,
        )

        assert len(errors) == 1
        assert errors[0].user_message == "User error"

    @pytest.mark.asyncio
    async def test_get_error_by_id(self, db_session, sample_session):
        """Get error by ID."""
        repo = SQLAlchemyErrorRepository(db_session)

        error = await repo.create_error({
            "session_id": sample_session.id,
            "error_category": ErrorCategory.USER_FIXABLE.value,
            "operation_stage": "upload",
            "user_message": "Test error",
        })

        result = await repo.get_error_by_id(error.id)

        assert result is not None
        assert result.id == error.id

    @pytest.mark.asyncio
    async def test_get_error_by_id_not_found(self, db_session):
        """Get error by non-existent ID."""
        repo = SQLAlchemyErrorRepository(db_session)

        result = await repo.get_error_by_id(uuid4())

        assert result is None

    @pytest.mark.asyncio
    async def test_has_blocking_errors(self, db_session, sample_session):
        """Check for blocking errors."""
        repo = SQLAlchemyErrorRepository(db_session)

        await repo.create_error({
            "session_id": sample_session.id,
            "error_category": ErrorCategory.USER_FIXABLE.value,
            "severity": ErrorSeverity.BLOCKING.value,
            "operation_stage": "upload",
            "user_message": "Blocking error",
        })

        has_blocking = await repo.has_blocking_errors(sample_session.id)

        assert has_blocking is True

    @pytest.mark.asyncio
    async def test_has_no_blocking_errors(self, db_session, sample_session):
        """No blocking errors."""
        repo = SQLAlchemyErrorRepository(db_session)

        await repo.create_error({
            "session_id": sample_session.id,
            "error_category": ErrorCategory.USER_FIXABLE.value,
            "severity": ErrorSeverity.WARNING.value,
            "operation_stage": "upload",
            "user_message": "Warning only",
        })

        has_blocking = await repo.has_blocking_errors(sample_session.id)

        assert has_blocking is False


class TestErrorPatternDetection:
    """Test pattern detection for errors."""

    @pytest.mark.asyncio
    async def test_store_errors_with_pattern_detection(
        self, db_session, sample_session
    ):
        """Store multiple errors with pattern detection."""
        repo = SQLAlchemyErrorRepository(db_session)

        errors_data = [
            {
                "error_category": ErrorCategory.USER_FIXABLE.value,
                "operation_stage": "upload",
                "user_message": "Error 1",
            },
            {
                "error_category": ErrorCategory.USER_FIXABLE.value,
                "operation_stage": "upload",
                "user_message": "Error 2",
            },
        ]

        created = await repo.store_errors_with_pattern_detection(
            sample_session.id,
            errors_data,
        )

        assert len(created) == 2


class TestAuditLogMethods:
    """Test audit logging methods."""

    @pytest.mark.asyncio
    async def test_log_event_basic(self, db_session, sample_session):
        """Log a basic audit event."""
        repo = SQLAlchemyErrorRepository(db_session)

        log = await repo.log_event(
            event_type="session_created",
            category=EventCategory.SESSION,
            description="Session created",
            session_id=sample_session.id,
        )

        assert log.id is not None
        assert log.event_type == "session_created"
        assert log.audit_level == AuditLevel.BASIC.value

    @pytest.mark.asyncio
    async def test_log_event_comprehensive(self, db_session, sample_session):
        """Log a comprehensive audit event."""
        repo = SQLAlchemyErrorRepository(db_session)

        log = await repo.log_event(
            event_type="ticket_generated",
            category=EventCategory.PROCESSING,
            description="Ticket generated from CSV",
            session_id=sample_session.id,
            entity_type="ticket",
            entity_id="ticket-123",
            event_data={"source_files": ["bundles.csv"]},
            execution_time_ms=150,
        )

        assert log.audit_level == AuditLevel.COMPREHENSIVE.value
        assert log.event_data == {"source_files": ["bundles.csv"]}

    @pytest.mark.asyncio
    async def test_get_session_timeline(self, db_session, sample_session):
        """Get chronological audit trail for session."""
        repo = SQLAlchemyErrorRepository(db_session)

        await repo.log_event(
            event_type="session_created",
            category=EventCategory.SESSION,
            description="Session created",
            session_id=sample_session.id,
        )
        await repo.log_event(
            event_type="file_uploaded",
            category=EventCategory.UPLOAD,
            description="File uploaded",
            session_id=sample_session.id,
        )

        timeline = await repo.get_session_timeline(sample_session.id)

        assert len(timeline) == 2
        assert timeline[0].event_type == "session_created"

    @pytest.mark.asyncio
    async def test_get_user_activity(self, db_session):
        """Get user activity over time period."""
        repo = SQLAlchemyErrorRepository(db_session)

        await repo.log_event(
            event_type="login",
            category=EventCategory.SESSION,
            description="User logged in",
            jira_user_id="user-activity-test",
        )

        activity = await repo.get_user_activity("user-activity-test", days=30)

        assert len(activity) == 1

    @pytest.mark.asyncio
    async def test_get_audit_events_filtered(self, db_session, sample_session):
        """Get audit events with filtering."""
        repo = SQLAlchemyErrorRepository(db_session)

        await repo.log_event(
            event_type="session_created",
            category=EventCategory.SESSION,
            description="Session created",
            session_id=sample_session.id,
        )
        await repo.log_event(
            event_type="file_uploaded",
            category=EventCategory.UPLOAD,
            description="File uploaded",
            session_id=sample_session.id,
        )

        events = await repo.get_audit_events(
            session_id=sample_session.id,
            category=EventCategory.SESSION,
        )

        assert len(events) == 1
        assert events[0].event_type == "session_created"


class TestErrorCleanup:
    """Test cleanup methods."""

    @pytest.mark.asyncio
    async def test_cleanup_session_errors(self, db_session, sample_session):
        """Delete all errors for session."""
        repo = SQLAlchemyErrorRepository(db_session)

        await repo.create_error({
            "session_id": sample_session.id,
            "error_category": ErrorCategory.USER_FIXABLE.value,
            "operation_stage": "upload",
            "user_message": "Error 1",
        })
        await repo.create_error({
            "session_id": sample_session.id,
            "error_category": ErrorCategory.TEMPORARY.value,
            "operation_stage": "processing",
            "user_message": "Error 2",
        })

        deleted = await repo.cleanup_session_errors(sample_session.id)

        assert deleted == 2

        errors = await repo.get_errors_by_session(sample_session.id)
        assert len(errors) == 0

    @pytest.mark.asyncio
    async def test_cleanup_audit_logs(self, db_session):
        """Delete old audit logs."""
        repo = SQLAlchemyErrorRepository(db_session)

        # Create old audit log
        old_log = AuditLog(
            event_type="old_event",
            event_category=EventCategory.SESSION.value,
            description="Old event",
            created_at=datetime.utcnow() - timedelta(days=100),
        )
        db_session.add(old_log)

        # Create recent audit log
        recent_log = AuditLog(
            event_type="recent_event",
            event_category=EventCategory.SESSION.value,
            description="Recent event",
        )
        db_session.add(recent_log)
        await db_session.flush()

        deleted = await repo.cleanup_audit_logs(retention_days=90)

        assert deleted == 1
