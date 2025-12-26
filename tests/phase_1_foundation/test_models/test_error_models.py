"""Tests for SessionError and AuditLog models."""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from sqlalchemy import inspect

from app.models.error import SessionError, AuditLog
from app.schemas.base import ErrorCategory, ErrorSeverity, EventCategory, AuditLevel


class TestSessionErrorModel:
    """Test SessionError model field definitions."""

    def test_session_error_has_required_fields(self):
        """SessionError must have all 11 specified fields."""
        mapper = inspect(SessionError)
        columns = {c.key for c in mapper.columns}

        required_fields = {
            "id",
            "session_id",
            "error_category",
            "severity",
            "operation_stage",
            "related_file_id",
            "related_ticket_id",
            "user_message",
            "recovery_actions",
            "technical_details",
            "error_code",
            "created_at",
        }
        assert required_fields.issubset(columns)

    def test_id_is_primary_key(self):
        """SessionError uses id as primary key."""
        mapper = inspect(SessionError)
        pk_columns = [c.key for c in mapper.primary_key]

        assert pk_columns == ["id"]

    def test_is_blocking_when_blocking_severity(self):
        """is_blocking returns True when severity is blocking."""
        error = SessionError(
            id=uuid4(),
            session_id=uuid4(),
            error_category=ErrorCategory.USER_FIXABLE.value,
            severity=ErrorSeverity.BLOCKING.value,
            operation_stage="upload",
            user_message="Test error",
            recovery_actions={"actions": []},
            technical_details={},
        )
        assert error.is_blocking() is True

    def test_is_not_blocking_when_warning_severity(self):
        """is_blocking returns False when severity is warning."""
        error = SessionError(
            id=uuid4(),
            session_id=uuid4(),
            error_category=ErrorCategory.USER_FIXABLE.value,
            severity=ErrorSeverity.WARNING.value,
            operation_stage="upload",
            user_message="Test error",
            recovery_actions={"actions": []},
            technical_details={},
        )
        assert error.is_blocking() is False

    def test_get_recovery_action_list(self):
        """get_recovery_action_list extracts actions from JSON."""
        error = SessionError(
            id=uuid4(),
            session_id=uuid4(),
            error_category=ErrorCategory.USER_FIXABLE.value,
            severity=ErrorSeverity.WARNING.value,
            operation_stage="upload",
            user_message="Test error",
            recovery_actions={"actions": ["retry", "contact support"]},
            technical_details={},
        )
        actions = error.get_recovery_action_list()

        assert actions == ["retry", "contact support"]

    def test_get_recovery_action_list_empty(self):
        """get_recovery_action_list returns empty list when no actions."""
        error = SessionError(
            id=uuid4(),
            session_id=uuid4(),
            error_category=ErrorCategory.USER_FIXABLE.value,
            severity=ErrorSeverity.WARNING.value,
            operation_stage="upload",
            user_message="Test error",
            recovery_actions={},
            technical_details={},
        )
        actions = error.get_recovery_action_list()

        assert actions == []

    def test_is_user_fixable_property(self):
        """is_user_fixable returns True for user-fixable errors."""
        error = SessionError(
            id=uuid4(),
            session_id=uuid4(),
            error_category=ErrorCategory.USER_FIXABLE.value,
            severity=ErrorSeverity.WARNING.value,
            operation_stage="upload",
            user_message="Test error",
            recovery_actions={},
            technical_details={},
        )
        assert error.is_user_fixable is True

    def test_is_not_user_fixable_for_admin_required(self):
        """is_user_fixable returns False for admin-required errors."""
        error = SessionError(
            id=uuid4(),
            session_id=uuid4(),
            error_category=ErrorCategory.ADMIN_REQUIRED.value,
            severity=ErrorSeverity.WARNING.value,
            operation_stage="upload",
            user_message="Test error",
            recovery_actions={},
            technical_details={},
        )
        assert error.is_user_fixable is False

    def test_requires_admin_property(self):
        """requires_admin returns True for admin-required errors."""
        error = SessionError(
            id=uuid4(),
            session_id=uuid4(),
            error_category=ErrorCategory.ADMIN_REQUIRED.value,
            severity=ErrorSeverity.BLOCKING.value,
            operation_stage="upload",
            user_message="Test error",
            recovery_actions={},
            technical_details={},
        )
        assert error.requires_admin is True

    def test_does_not_require_admin_for_user_fixable(self):
        """requires_admin returns False for user-fixable errors."""
        error = SessionError(
            id=uuid4(),
            session_id=uuid4(),
            error_category=ErrorCategory.USER_FIXABLE.value,
            severity=ErrorSeverity.BLOCKING.value,
            operation_stage="upload",
            user_message="Test error",
            recovery_actions={},
            technical_details={},
        )
        assert error.requires_admin is False

    def test_age_minutes_calculation(self):
        """age_minutes calculates correct age."""
        error = SessionError(
            id=uuid4(),
            session_id=uuid4(),
            error_category=ErrorCategory.USER_FIXABLE.value,
            severity=ErrorSeverity.WARNING.value,
            operation_stage="upload",
            user_message="Test error",
            recovery_actions={},
            technical_details={},
            created_at=datetime.utcnow() - timedelta(minutes=30),
        )
        # Allow for test execution time
        assert 29 <= error.age_minutes <= 31


class TestAuditLogModel:
    """Test AuditLog model field definitions."""

    def test_audit_log_has_required_fields(self):
        """AuditLog must have all 14 specified fields."""
        mapper = inspect(AuditLog)
        columns = {c.key for c in mapper.columns}

        required_fields = {
            "id",
            "session_id",
            "jira_user_id",
            "event_type",
            "event_category",
            "audit_level",
            "description",
            "entity_type",
            "entity_id",
            "event_data",
            "request_id",
            "execution_time_ms",
            "ip_address",
            "user_agent",
            "created_at",
        }
        assert required_fields.issubset(columns)

    def test_id_is_primary_key(self):
        """AuditLog uses id as primary key."""
        mapper = inspect(AuditLog)
        pk_columns = [c.key for c in mapper.primary_key]

        assert pk_columns == ["id"]

    def test_is_comprehensive_when_comprehensive_level(self):
        """is_comprehensive returns True for comprehensive audit level."""
        log = AuditLog(
            id=uuid4(),
            event_type="session_created",
            event_category=EventCategory.SESSION.value,
            audit_level=AuditLevel.COMPREHENSIVE.value,
            description="Test log entry",
        )
        assert log.is_comprehensive is True

    def test_is_not_comprehensive_when_basic_level(self):
        """is_comprehensive returns False for basic audit level."""
        log = AuditLog(
            id=uuid4(),
            event_type="session_created",
            event_category=EventCategory.SESSION.value,
            audit_level=AuditLevel.BASIC.value,
            description="Test log entry",
        )
        assert log.is_comprehensive is False

    def test_age_days_calculation(self):
        """age_days calculates correct age."""
        log = AuditLog(
            id=uuid4(),
            event_type="session_created",
            event_category=EventCategory.SESSION.value,
            audit_level=AuditLevel.BASIC.value,
            description="Test log entry",
            created_at=datetime.utcnow() - timedelta(days=7),
        )
        # Allow for test execution time
        assert 6.9 <= log.age_days <= 7.1

    def test_has_performance_data_when_execution_time_present(self):
        """has_performance_data returns True when execution_time_ms is set."""
        log = AuditLog(
            id=uuid4(),
            event_type="session_created",
            event_category=EventCategory.SESSION.value,
            audit_level=AuditLevel.BASIC.value,
            description="Test log entry",
            execution_time_ms=150,
        )
        assert log.has_performance_data is True

    def test_has_no_performance_data_when_execution_time_absent(self):
        """has_performance_data returns False when execution_time_ms is None."""
        log = AuditLog(
            id=uuid4(),
            event_type="session_created",
            event_category=EventCategory.SESSION.value,
            audit_level=AuditLevel.BASIC.value,
            description="Test log entry",
        )
        assert log.has_performance_data is False

    def test_optional_fields_can_be_none(self):
        """Optional fields can be None."""
        log = AuditLog(
            id=uuid4(),
            event_type="session_created",
            event_category=EventCategory.SESSION.value,
            audit_level=AuditLevel.BASIC.value,
            description="Test log entry",
        )
        assert log.session_id is None
        assert log.jira_user_id is None
        assert log.entity_type is None
        assert log.entity_id is None
        assert log.event_data is None
        assert log.request_id is None
        assert log.execution_time_ms is None
        assert log.ip_address is None
        assert log.user_agent is None
