"""Tests for Pydantic schemas and enums."""

import pytest

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


class TestSessionStageEnum:
    """Test SessionStage enum."""

    def test_session_stage_values(self):
        """Test all session stage values."""
        assert SessionStage.SITE_INFO_COLLECTION.value == "site_info_collection"
        assert SessionStage.UPLOAD.value == "upload"
        assert SessionStage.PROCESSING.value == "processing"
        assert SessionStage.REVIEW.value == "review"
        assert SessionStage.JIRA_EXPORT.value == "jira_export"
        assert SessionStage.COMPLETED.value == "completed"

    def test_session_stage_count(self):
        """Test correct number of stages."""
        assert len(SessionStage) == 6


class TestSessionStatusEnum:
    """Test SessionStatus enum."""

    def test_session_status_values(self):
        """Test all session status values."""
        assert SessionStatus.ACTIVE.value == "active"
        assert SessionStatus.EXPORTING.value == "exporting"
        assert SessionStatus.FAILED.value == "failed"
        assert SessionStatus.COMPLETED.value == "completed"

    def test_session_status_count(self):
        """Test correct number of statuses."""
        assert len(SessionStatus) == 4


class TestTaskTypeEnum:
    """Test TaskType enum."""

    def test_task_type_values(self):
        """Test all task type values."""
        assert TaskType.PROCESSING.value == "processing"
        assert TaskType.EXPORT.value == "export"
        assert TaskType.ADF_VALIDATION.value == "adf_validation"

    def test_task_type_count(self):
        """Test correct number of task types."""
        assert len(TaskType) == 3


class TestTaskStatusEnum:
    """Test TaskStatus enum."""

    def test_task_status_values(self):
        """Test all task status values."""
        assert TaskStatus.RUNNING.value == "running"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.CANCELLED.value == "cancelled"

    def test_task_status_count(self):
        """Test correct number of task statuses."""
        assert len(TaskStatus) == 4


class TestFileValidationStatusEnum:
    """Test FileValidationStatus enum."""

    def test_file_validation_status_values(self):
        """Test all file validation status values."""
        assert FileValidationStatus.PENDING.value == "pending"
        assert FileValidationStatus.VALID.value == "valid"
        assert FileValidationStatus.INVALID.value == "invalid"

    def test_file_validation_status_count(self):
        """Test correct number of file validation statuses."""
        assert len(FileValidationStatus) == 3


class TestAdfValidationStatusEnum:
    """Test AdfValidationStatus enum."""

    def test_adf_validation_status_values(self):
        """Test all ADF validation status values."""
        assert AdfValidationStatus.PENDING.value == "pending"
        assert AdfValidationStatus.PROCESSING.value == "processing"
        assert AdfValidationStatus.COMPLETED.value == "completed"
        assert AdfValidationStatus.FAILED.value == "failed"

    def test_adf_validation_status_count(self):
        """Test correct number of ADF validation statuses."""
        assert len(AdfValidationStatus) == 4


class TestJiraUploadStatusEnum:
    """Test JiraUploadStatus enum."""

    def test_jira_upload_status_values(self):
        """Test all Jira upload status values."""
        assert JiraUploadStatus.PENDING.value == "pending"
        assert JiraUploadStatus.UPLOADED.value == "uploaded"
        assert JiraUploadStatus.FAILED.value == "failed"

    def test_jira_upload_status_count(self):
        """Test correct number of Jira upload statuses."""
        assert len(JiraUploadStatus) == 3


class TestErrorCategoryEnum:
    """Test ErrorCategory enum."""

    def test_error_category_values(self):
        """Test all error category values."""
        assert ErrorCategory.USER_FIXABLE.value == "user_fixable"
        assert ErrorCategory.ADMIN_REQUIRED.value == "admin_required"
        assert ErrorCategory.TEMPORARY.value == "temporary"

    def test_error_category_count(self):
        """Test correct number of error categories."""
        assert len(ErrorCategory) == 3


class TestErrorSeverityEnum:
    """Test ErrorSeverity enum."""

    def test_error_severity_values(self):
        """Test all error severity values."""
        assert ErrorSeverity.BLOCKING.value == "blocking"
        assert ErrorSeverity.WARNING.value == "warning"
        assert ErrorSeverity.INFO.value == "info"

    def test_error_severity_count(self):
        """Test correct number of error severities."""
        assert len(ErrorSeverity) == 3


class TestEventCategoryEnum:
    """Test EventCategory enum."""

    def test_event_category_values(self):
        """Test all event category values."""
        assert EventCategory.SESSION.value == "session"
        assert EventCategory.UPLOAD.value == "upload"
        assert EventCategory.PROCESSING.value == "processing"
        assert EventCategory.REVIEW.value == "review"
        assert EventCategory.JIRA_EXPORT.value == "jira_export"
        assert EventCategory.SYSTEM.value == "system"

    def test_event_category_count(self):
        """Test correct number of event categories."""
        assert len(EventCategory) == 6


class TestAuditLevelEnum:
    """Test AuditLevel enum."""

    def test_audit_level_values(self):
        """Test all audit level values."""
        assert AuditLevel.BASIC.value == "basic"
        assert AuditLevel.COMPREHENSIVE.value == "comprehensive"

    def test_audit_level_count(self):
        """Test correct number of audit levels."""
        assert len(AuditLevel) == 2


class TestEnumUsability:
    """Test that enums can be used in expected ways."""

    def test_enum_string_comparison(self):
        """Test enum value string comparison."""
        assert SessionStage.UPLOAD.value == "upload"
        assert str(SessionStage.UPLOAD.value) == "upload"

    def test_enum_membership(self):
        """Test enum membership checking."""
        assert "upload" in [s.value for s in SessionStage]
        assert "invalid" not in [s.value for s in SessionStage]

    def test_enum_from_value(self):
        """Test creating enum from value."""
        stage = SessionStage("upload")
        assert stage == SessionStage.UPLOAD

    def test_enum_iteration(self):
        """Test iterating over enum values."""
        stages = list(SessionStage)
        assert len(stages) == 6
        assert SessionStage.UPLOAD in stages
