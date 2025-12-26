"""Tests for application exceptions."""

import pytest

from app.core.exceptions import (
    BaseAppException,
    SessionError,
    SessionNotFoundError,
    SessionValidationError,
    InvalidStageTransitionError,
    TaskError,
    TaskAlreadyRunningError,
    TaskNotFoundError,
    RepositoryError,
    EntityNotFoundError,
    DuplicateEntityError,
    FileError,
    FileValidationError,
    FileTooLargeError,
    TicketError,
    TicketValidationError,
    CircularDependencyError,
    AuthError,
    TokenExpiredError,
    TokenRefreshError,
    ProcessingError,
    LLMServiceError,
    ExportError,
    ExportBlockedError,
    JiraApiError,
    AttachmentError,
    AttachmentValidationError,
    AttachmentUploadError,
)


class TestBaseAppException:
    """Test base exception."""

    def test_base_exception_defaults(self):
        """Test default values for base exception."""
        exc = BaseAppException("Test error")

        assert exc.message == "Test error"
        assert exc.category == "admin_required"
        assert exc.recovery_actions == []
        assert exc.technical_details == {}
        assert exc.error_code is None

    def test_base_exception_with_all_params(self):
        """Test base exception with all parameters."""
        exc = BaseAppException(
            message="Test error",
            category="user_fixable",
            recovery_actions=["Action 1", "Action 2"],
            technical_details={"key": "value"},
            error_code="TEST_ERROR",
        )

        assert exc.message == "Test error"
        assert exc.category == "user_fixable"
        assert exc.recovery_actions == ["Action 1", "Action 2"]
        assert exc.technical_details == {"key": "value"}
        assert exc.error_code == "TEST_ERROR"


class TestSessionErrors:
    """Test session-related exceptions."""

    def test_session_not_found_error(self):
        """Test SessionNotFoundError."""
        exc = SessionNotFoundError("session-123")

        assert "session-123" in exc.message
        assert exc.category == "user_fixable"
        assert exc.error_code == "SESSION_NOT_FOUND"
        assert len(exc.recovery_actions) > 0

    def test_invalid_stage_transition_error(self):
        """Test InvalidStageTransitionError."""
        exc = InvalidStageTransitionError("upload", "export")

        assert "upload" in exc.message
        assert "export" in exc.message
        assert exc.category == "user_fixable"
        assert exc.error_code == "INVALID_STAGE_TRANSITION"


class TestTaskErrors:
    """Test task-related exceptions."""

    def test_task_already_running_error(self):
        """Test TaskAlreadyRunningError."""
        exc = TaskAlreadyRunningError("csv_parsing")

        assert "csv_parsing" in exc.message
        assert exc.category == "user_fixable"
        assert exc.error_code == "TASK_ALREADY_RUNNING"


class TestRepositoryErrors:
    """Test repository-related exceptions."""

    def test_entity_not_found_error(self):
        """Test EntityNotFoundError."""
        exc = EntityNotFoundError("Ticket", "ticket-456")

        assert "Ticket" in exc.message
        assert "ticket-456" in exc.message
        assert exc.category == "user_fixable"
        assert exc.error_code == "ENTITY_NOT_FOUND"

    def test_duplicate_entity_error(self):
        """Test DuplicateEntityError."""
        exc = DuplicateEntityError("Session", "user_id")

        assert "Session" in exc.message
        assert "user_id" in exc.message
        assert exc.category == "user_fixable"
        assert exc.error_code == "DUPLICATE_ENTITY"


class TestFileErrors:
    """Test file-related exceptions."""

    def test_file_too_large_error(self):
        """Test FileTooLargeError."""
        exc = FileTooLargeError("large_file.csv", 10.0)

        assert "large_file.csv" in exc.message
        assert "10.0MB" in exc.message
        assert exc.category == "user_fixable"
        assert exc.error_code == "FILE_TOO_LARGE"


class TestTicketErrors:
    """Test ticket-related exceptions."""

    def test_circular_dependency_error(self):
        """Test CircularDependencyError."""
        exc = CircularDependencyError("ticket-1", "ticket-2")

        assert "circular" in exc.message.lower()
        assert exc.category == "user_fixable"
        assert exc.error_code == "CIRCULAR_DEPENDENCY"


class TestAuthErrors:
    """Test authentication-related exceptions."""

    def test_token_expired_error(self):
        """Test TokenExpiredError."""
        exc = TokenExpiredError()

        assert "expired" in exc.message.lower()
        assert exc.category == "user_fixable"
        assert exc.error_code == "TOKEN_EXPIRED"


class TestProcessingErrors:
    """Test processing-related exceptions."""

    def test_llm_service_error(self):
        """Test LLMServiceError."""
        exc = LLMServiceError("Service unavailable", "openai")

        assert exc.message == "Service unavailable"
        assert exc.category == "temporary"
        assert exc.error_code == "LLM_SERVICE_ERROR"
        assert exc.technical_details["provider"] == "openai"


class TestExportErrors:
    """Test export-related exceptions."""

    def test_export_blocked_error(self):
        """Test ExportBlockedError."""
        exc = ExportBlockedError("Validation incomplete")

        assert "Validation incomplete" in exc.message
        assert exc.category == "user_fixable"
        assert exc.error_code == "EXPORT_BLOCKED"

    def test_jira_api_error_server_error(self):
        """Test JiraApiError with server error."""
        exc = JiraApiError("Internal server error", 500)

        assert exc.category == "temporary"
        assert exc.error_code == "JIRA_API_ERROR"
        assert exc.technical_details["status_code"] == 500

    def test_jira_api_error_client_error(self):
        """Test JiraApiError with client error."""
        exc = JiraApiError("Bad request", 400)

        assert exc.category == "admin_required"
        assert exc.error_code == "JIRA_API_ERROR"


class TestExceptionHierarchy:
    """Test exception class hierarchy."""

    def test_session_errors_inherit_from_base(self):
        """Session errors inherit from BaseAppException."""
        assert issubclass(SessionError, BaseAppException)
        assert issubclass(SessionNotFoundError, SessionError)
        assert issubclass(InvalidStageTransitionError, SessionError)

    def test_task_errors_inherit_from_base(self):
        """Task errors inherit from BaseAppException."""
        assert issubclass(TaskError, BaseAppException)
        assert issubclass(TaskAlreadyRunningError, TaskError)

    def test_repository_errors_inherit_from_base(self):
        """Repository errors inherit from BaseAppException."""
        assert issubclass(RepositoryError, BaseAppException)
        assert issubclass(EntityNotFoundError, RepositoryError)
        assert issubclass(DuplicateEntityError, RepositoryError)

    def test_file_errors_inherit_from_base(self):
        """File errors inherit from BaseAppException."""
        assert issubclass(FileError, BaseAppException)
        assert issubclass(FileValidationError, FileError)
        assert issubclass(FileTooLargeError, FileError)

    def test_ticket_errors_inherit_from_base(self):
        """Ticket errors inherit from BaseAppException."""
        assert issubclass(TicketError, BaseAppException)
        assert issubclass(TicketValidationError, TicketError)
        assert issubclass(CircularDependencyError, TicketError)

    def test_auth_errors_inherit_from_base(self):
        """Auth errors inherit from BaseAppException."""
        assert issubclass(AuthError, BaseAppException)
        assert issubclass(TokenExpiredError, AuthError)
        assert issubclass(TokenRefreshError, AuthError)

    def test_export_errors_inherit_from_base(self):
        """Export errors inherit from BaseAppException."""
        assert issubclass(ExportError, BaseAppException)
        assert issubclass(ExportBlockedError, ExportError)
        assert issubclass(JiraApiError, ExportError)

    def test_attachment_errors_inherit_from_base(self):
        """Attachment errors inherit from BaseAppException."""
        assert issubclass(AttachmentError, BaseAppException)
        assert issubclass(AttachmentValidationError, AttachmentError)
        assert issubclass(AttachmentUploadError, AttachmentError)
