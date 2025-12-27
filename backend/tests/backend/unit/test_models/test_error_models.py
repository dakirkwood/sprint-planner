# tests/backend/unit/test_models/test_error_models.py
"""
Tests for SessionError and AuditLog models.
"""
import pytest
from sqlalchemy import inspect

from app.models.error import SessionError, AuditLog
from app.models.session import Session
from app.schemas.base import (
    ErrorCategory,
    ErrorSeverity,
    EventCategory,
    AuditLevel
)


@pytest.mark.phase1
@pytest.mark.models
class TestSessionErrorModel:
    """Test SessionError model field definitions."""

    def test_session_error_has_required_fields(self):
        """SessionError must have all specified fields."""
        mapper = inspect(SessionError)
        columns = {c.key for c in mapper.columns}

        required_fields = {
            'id', 'session_id', 'category', 'severity', 'error_code',
            'user_message', 'technical_details', 'recovery_actions',
            'workflow_stage', 'entity_type', 'entity_id',
            'created_at', 'updated_at'
        }
        assert required_fields.issubset(columns)

    def test_session_error_has_session_relationship(self):
        """SessionError should have relationship to Session."""
        mapper = inspect(SessionError)
        relationships = {r.key for r in mapper.relationships}

        assert 'session' in relationships

    @pytest.mark.asyncio
    async def test_session_error_creation(self, db_session, sample_session_data):
        """Should create SessionError with all fields."""
        session = Session(**sample_session_data)
        db_session.add(session)
        await db_session.flush()

        error = SessionError(
            session_id=session.id,
            category=ErrorCategory.USER_FIXABLE,
            severity=ErrorSeverity.BLOCKING,
            user_message="Test error message",
            error_code="TEST_ERROR"
        )
        db_session.add(error)
        await db_session.flush()

        assert error.id is not None
        assert error.category == ErrorCategory.USER_FIXABLE
        assert error.severity == ErrorSeverity.BLOCKING

    @pytest.mark.asyncio
    async def test_session_error_to_dict(self, db_session, sample_session_data):
        """to_dict should serialize all expected fields."""
        session = Session(**sample_session_data)
        db_session.add(session)
        await db_session.flush()

        error = SessionError(
            session_id=session.id,
            category=ErrorCategory.TEMPORARY,
            severity=ErrorSeverity.WARNING,
            user_message="Test warning",
            recovery_actions=["Try again later"]
        )
        db_session.add(error)
        await db_session.flush()

        error_dict = error.to_dict()

        assert "id" in error_dict
        assert error_dict["category"] == "temporary"
        assert error_dict["severity"] == "warning"
        assert error_dict["recovery_actions"] == ["Try again later"]

    def test_error_category_enum_values(self):
        """ErrorCategory enum must have expected values."""
        expected = {'user_fixable', 'admin_required', 'temporary'}
        actual = {e.value for e in ErrorCategory}

        assert expected == actual

    def test_error_severity_enum_values(self):
        """ErrorSeverity enum must have expected values."""
        expected = {'blocking', 'warning', 'info'}
        actual = {e.value for e in ErrorSeverity}

        assert expected == actual


@pytest.mark.phase1
@pytest.mark.models
class TestAuditLogModel:
    """Test AuditLog model field definitions."""

    def test_audit_log_has_required_fields(self):
        """AuditLog must have all specified fields."""
        mapper = inspect(AuditLog)
        columns = {c.key for c in mapper.columns}

        required_fields = {
            'id', 'event_type', 'category', 'audit_level', 'description',
            'event_data', 'session_id', 'jira_user_id', 'entity_type',
            'entity_id', 'request_id', 'execution_time_ms', 'created_at'
        }
        assert required_fields.issubset(columns)

    @pytest.mark.asyncio
    async def test_audit_log_creation(self, db_session, sample_session_data):
        """Should create AuditLog with all fields."""
        session = Session(**sample_session_data)
        db_session.add(session)
        await db_session.flush()

        log = AuditLog(
            event_type="session_created",
            category=EventCategory.SESSION,
            description="Session was created",
            session_id=session.id,
            jira_user_id=sample_session_data["jira_user_id"]
        )
        db_session.add(log)
        await db_session.flush()

        assert log.id is not None
        assert log.category == EventCategory.SESSION
        assert log.audit_level == AuditLevel.BASIC

    @pytest.mark.asyncio
    async def test_audit_log_to_dict(self, db_session, sample_session_data):
        """to_dict should serialize all expected fields."""
        session = Session(**sample_session_data)
        db_session.add(session)
        await db_session.flush()

        log = AuditLog(
            event_type="test_event",
            category=EventCategory.SYSTEM,
            audit_level=AuditLevel.COMPREHENSIVE,
            description="Test event description",
            execution_time_ms=150
        )
        db_session.add(log)
        await db_session.flush()

        log_dict = log.to_dict()

        assert "id" in log_dict
        assert log_dict["event_type"] == "test_event"
        assert log_dict["category"] == "system"
        assert log_dict["audit_level"] == "comprehensive"
        assert log_dict["execution_time_ms"] == 150

    def test_event_category_enum_values(self):
        """EventCategory enum must have expected values."""
        expected = {'session', 'upload', 'processing', 'review', 'jira_export', 'system'}
        actual = {e.value for e in EventCategory}

        assert expected == actual

    def test_audit_level_enum_values(self):
        """AuditLevel enum must have expected values."""
        expected = {'basic', 'comprehensive'}
        actual = {e.value for e in AuditLevel}

        assert expected == actual
