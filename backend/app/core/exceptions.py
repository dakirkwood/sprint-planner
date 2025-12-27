# app/core/exceptions.py
"""
Base exception classes for the application.
Follows the 'who can fix it' error categorization pattern.
"""
from typing import Optional, List
from enum import Enum


class ErrorCategory(str, Enum):
    """Error categorization based on 'who can fix it' strategy."""
    USER_FIXABLE = "user_fixable"
    ADMIN_REQUIRED = "admin_required"
    TEMPORARY = "temporary"


class ErrorSeverity(str, Enum):
    """Error severity levels for UI treatment."""
    BLOCKING = "blocking"
    WARNING = "warning"
    INFO = "info"


class ApplicationError(Exception):
    """
    Base exception for all application errors.

    Attributes:
        message: Human-readable error message
        category: Who can fix this error
        severity: How severe is this error
        recovery_actions: List of suggested recovery steps
        technical_details: Additional debug information
        error_code: Application-specific error code
    """

    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.ADMIN_REQUIRED,
        severity: ErrorSeverity = ErrorSeverity.BLOCKING,
        recovery_actions: Optional[List[str]] = None,
        technical_details: Optional[dict] = None,
        error_code: Optional[str] = None
    ):
        super().__init__(message)
        self.message = message
        self.category = category
        self.severity = severity
        self.recovery_actions = recovery_actions or []
        self.technical_details = technical_details
        self.error_code = error_code

    def to_dict(self) -> dict:
        """Convert exception to dictionary for API response."""
        return {
            "error_category": self.category.value,
            "user_message": self.message,
            "recovery_actions": self.recovery_actions,
            "error_code": self.error_code,
        }


class ValidationError(ApplicationError):
    """Error for validation failures."""

    def __init__(
        self,
        message: str,
        recovery_actions: Optional[List[str]] = None,
        technical_details: Optional[dict] = None
    ):
        super().__init__(
            message=message,
            category=ErrorCategory.USER_FIXABLE,
            severity=ErrorSeverity.BLOCKING,
            recovery_actions=recovery_actions or ["Please correct the invalid data and try again"],
            technical_details=technical_details,
            error_code="VALIDATION_ERROR"
        )


class NotFoundError(ApplicationError):
    """Error for resource not found."""

    def __init__(
        self,
        resource_type: str,
        resource_id: str,
        technical_details: Optional[dict] = None
    ):
        super().__init__(
            message=f"{resource_type} not found: {resource_id}",
            category=ErrorCategory.USER_FIXABLE,
            severity=ErrorSeverity.BLOCKING,
            recovery_actions=["Check the ID and try again", "The resource may have been deleted"],
            technical_details=technical_details,
            error_code="NOT_FOUND"
        )


class DatabaseError(ApplicationError):
    """Error for database operations."""

    def __init__(
        self,
        message: str,
        technical_details: Optional[dict] = None
    ):
        super().__init__(
            message=message,
            category=ErrorCategory.ADMIN_REQUIRED,
            severity=ErrorSeverity.BLOCKING,
            recovery_actions=["Please try again later", "Contact support if the issue persists"],
            technical_details=technical_details,
            error_code="DATABASE_ERROR"
        )


class ExternalServiceError(ApplicationError):
    """Error for external service failures (Jira, LLM, etc.)."""

    def __init__(
        self,
        service_name: str,
        message: str,
        is_temporary: bool = True,
        technical_details: Optional[dict] = None
    ):
        category = ErrorCategory.TEMPORARY if is_temporary else ErrorCategory.ADMIN_REQUIRED

        recovery_actions = ["Please try again in a few moments"]
        if not is_temporary:
            recovery_actions = ["Contact support for assistance"]

        super().__init__(
            message=f"{service_name} error: {message}",
            category=category,
            severity=ErrorSeverity.BLOCKING,
            recovery_actions=recovery_actions,
            technical_details=technical_details,
            error_code="EXTERNAL_SERVICE_ERROR"
        )


class SessionValidationError(ApplicationError):
    """Error for session state validation failures."""

    def __init__(
        self,
        message: str,
        recovery_actions: Optional[List[str]] = None,
        technical_details: Optional[dict] = None
    ):
        super().__init__(
            message=message,
            category=ErrorCategory.USER_FIXABLE,
            severity=ErrorSeverity.BLOCKING,
            recovery_actions=recovery_actions or ["Complete previous steps before continuing"],
            technical_details=technical_details,
            error_code="SESSION_VALIDATION_ERROR"
        )


class TicketValidationError(ApplicationError):
    """Error for ticket validation failures."""

    def __init__(
        self,
        message: str,
        recovery_actions: Optional[List[str]] = None,
        technical_details: Optional[dict] = None
    ):
        super().__init__(
            message=message,
            category=ErrorCategory.USER_FIXABLE,
            severity=ErrorSeverity.BLOCKING,
            recovery_actions=recovery_actions or ["Review and correct ticket data"],
            technical_details=technical_details,
            error_code="TICKET_VALIDATION_ERROR"
        )
