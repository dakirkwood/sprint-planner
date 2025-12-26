"""Base exception classes following the 'who can fix it' pattern."""

from typing import List, Optional, Dict, Any


class BaseAppException(Exception):
    """Base exception for all application errors."""

    def __init__(
        self,
        message: str,
        category: str = "admin_required",
        recovery_actions: Optional[List[str]] = None,
        technical_details: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None,
    ):
        self.message = message
        self.category = category
        self.recovery_actions = recovery_actions or []
        self.technical_details = technical_details or {}
        self.error_code = error_code
        super().__init__(message)


# Session Errors
class SessionError(BaseAppException):
    """Errors related to session operations."""
    pass


class SessionNotFoundError(SessionError):
    """Session not found."""

    def __init__(self, session_id: str):
        super().__init__(
            message=f"Session '{session_id}' not found",
            category="user_fixable",
            recovery_actions=["Start a new session", "Check if the session ID is correct"],
            error_code="SESSION_NOT_FOUND",
        )


class SessionValidationError(SessionError):
    """Session validation failed."""
    pass


class InvalidStageTransitionError(SessionError):
    """Invalid stage transition attempted."""

    def __init__(self, current_stage: str, target_stage: str):
        super().__init__(
            message=f"Cannot transition from '{current_stage}' to '{target_stage}'",
            category="user_fixable",
            recovery_actions=[f"Complete the {current_stage} stage first"],
            error_code="INVALID_STAGE_TRANSITION",
        )


# Task Errors
class TaskError(BaseAppException):
    """Errors related to background tasks."""
    pass


class TaskAlreadyRunningError(TaskError):
    """A task is already running for this session."""

    def __init__(self, task_type: str):
        super().__init__(
            message=f"A {task_type} task is already running",
            category="user_fixable",
            recovery_actions=["Wait for the current task to complete"],
            error_code="TASK_ALREADY_RUNNING",
        )


class TaskNotFoundError(TaskError):
    """Task not found."""
    pass


# Repository Errors
class RepositoryError(BaseAppException):
    """Errors from repository operations."""
    pass


class EntityNotFoundError(RepositoryError):
    """Entity not found in database."""

    def __init__(self, entity_type: str, entity_id: str):
        super().__init__(
            message=f"{entity_type} '{entity_id}' not found",
            category="user_fixable",
            recovery_actions=["Verify the ID is correct", "The item may have been deleted"],
            error_code="ENTITY_NOT_FOUND",
        )


class DuplicateEntityError(RepositoryError):
    """Duplicate entity detected."""

    def __init__(self, entity_type: str, constraint: str):
        super().__init__(
            message=f"A {entity_type} with this {constraint} already exists",
            category="user_fixable",
            recovery_actions=["Use a different value", "Update the existing item instead"],
            error_code="DUPLICATE_ENTITY",
        )


# File Errors
class FileError(BaseAppException):
    """Errors related to file operations."""
    pass


class FileValidationError(FileError):
    """File validation failed."""
    pass


class FileTooLargeError(FileError):
    """File exceeds size limit."""

    def __init__(self, filename: str, max_size_mb: float):
        super().__init__(
            message=f"File '{filename}' exceeds the {max_size_mb}MB limit",
            category="user_fixable",
            recovery_actions=[f"Upload a file smaller than {max_size_mb}MB"],
            error_code="FILE_TOO_LARGE",
        )


# Ticket Errors
class TicketError(BaseAppException):
    """Errors related to ticket operations."""
    pass


class TicketValidationError(TicketError):
    """Ticket validation failed."""
    pass


class CircularDependencyError(TicketError):
    """Circular dependency detected."""

    def __init__(self, ticket_id: str, depends_on_id: str):
        super().__init__(
            message=f"Adding dependency would create a circular reference",
            category="user_fixable",
            recovery_actions=["Remove one of the existing dependencies first"],
            error_code="CIRCULAR_DEPENDENCY",
        )


# Auth Errors
class AuthError(BaseAppException):
    """Errors related to authentication."""
    pass


class TokenExpiredError(AuthError):
    """OAuth token has expired."""

    def __init__(self):
        super().__init__(
            message="Your Jira authentication has expired",
            category="user_fixable",
            recovery_actions=["Re-authenticate with Jira"],
            error_code="TOKEN_EXPIRED",
        )


class TokenRefreshError(AuthError):
    """Token refresh failed."""
    pass


# Processing Errors
class ProcessingError(BaseAppException):
    """Errors during ticket generation."""
    pass


class LLMServiceError(ProcessingError):
    """LLM service error."""

    def __init__(self, message: str, provider: str):
        super().__init__(
            message=message,
            category="temporary",
            recovery_actions=["Try again in a few minutes", "Check LLM service status"],
            technical_details={"provider": provider},
            error_code="LLM_SERVICE_ERROR",
        )


# Export Errors
class ExportError(BaseAppException):
    """Errors during Jira export."""
    pass


class ExportBlockedError(ExportError):
    """Export is blocked due to validation requirements."""

    def __init__(self, reason: str):
        super().__init__(
            message=f"Export blocked: {reason}",
            category="user_fixable",
            recovery_actions=["Complete ADF validation first", "Mark tickets as ready"],
            error_code="EXPORT_BLOCKED",
        )


class JiraApiError(ExportError):
    """Jira API error."""

    def __init__(self, message: str, status_code: int):
        super().__init__(
            message=message,
            category="temporary" if status_code >= 500 else "admin_required",
            recovery_actions=["Try again", "Check Jira connection settings"],
            technical_details={"status_code": status_code},
            error_code="JIRA_API_ERROR",
        )


# Attachment Errors
class AttachmentError(BaseAppException):
    """Errors related to attachments."""
    pass


class AttachmentValidationError(AttachmentError):
    """Attachment validation failed."""
    pass


class AttachmentUploadError(AttachmentError):
    """Attachment upload to Jira failed."""
    pass
