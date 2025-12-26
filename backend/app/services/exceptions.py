"""Service layer exceptions with 'who can fix it' categorization."""

from typing import List, Optional


class ServiceError(Exception):
    """Base exception for service layer errors."""

    def __init__(
        self,
        message: str,
        category: str = "system",
        recovery_actions: Optional[List[str]] = None,
        error_code: Optional[str] = None,
    ):
        """Initialize service error.

        Args:
            message: Human-readable error message
            category: Error category (user_fixable, admin_required, temporary)
            recovery_actions: List of suggested recovery actions
            error_code: Machine-readable error code
        """
        self.message = message
        self.category = category
        self.recovery_actions = recovery_actions or []
        self.error_code = error_code
        super().__init__(message)


class SessionError(ServiceError):
    """Raised when session operations fail."""

    pass


class AuthenticationError(ServiceError):
    """Raised when authentication fails."""

    def __init__(
        self,
        message: str,
        recovery_actions: Optional[List[str]] = None,
    ):
        super().__init__(
            message=message,
            category="user_fixable",
            recovery_actions=recovery_actions or ["Please log in again"],
            error_code="AUTH_FAILED",
        )


class AuthorizationError(ServiceError):
    """Raised when user lacks required permissions."""

    def __init__(
        self,
        message: str,
        recovery_actions: Optional[List[str]] = None,
    ):
        super().__init__(
            message=message,
            category="user_fixable",
            recovery_actions=recovery_actions or [
                "Check your Jira permissions",
                "Contact project administrator",
            ],
            error_code="PERMISSION_DENIED",
        )


class ValidationError(ServiceError):
    """Raised when input validation fails."""

    def __init__(
        self,
        message: str,
        recovery_actions: Optional[List[str]] = None,
    ):
        super().__init__(
            message=message,
            category="user_fixable",
            recovery_actions=recovery_actions or ["Check your input and try again"],
            error_code="VALIDATION_ERROR",
        )


class ResourceNotFoundError(ServiceError):
    """Raised when a requested resource is not found."""

    def __init__(
        self,
        resource_type: str,
        resource_id: str,
    ):
        super().__init__(
            message=f"{resource_type} not found: {resource_id}",
            category="user_fixable",
            recovery_actions=["Check the ID and try again"],
            error_code="NOT_FOUND",
        )


class ExternalServiceError(ServiceError):
    """Raised when an external service (Jira, LLM) fails."""

    def __init__(
        self,
        service_name: str,
        message: str,
    ):
        super().__init__(
            message=f"{service_name} error: {message}",
            category="temporary",
            recovery_actions=[
                "Wait a moment and try again",
                f"Check {service_name} status",
            ],
            error_code="EXTERNAL_SERVICE_ERROR",
        )
