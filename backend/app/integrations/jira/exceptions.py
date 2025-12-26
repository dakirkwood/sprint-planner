"""Jira integration exceptions."""


class JiraError(Exception):
    """Base exception for Jira integration errors."""

    def __init__(self, message: str, status_code: int = None):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class JiraAuthError(JiraError):
    """Raised when authentication with Jira fails."""

    pass


class JiraAPIError(JiraError):
    """Raised when Jira API request fails."""

    pass


class JiraProjectNotFoundError(JiraError):
    """Raised when specified Jira project is not found."""

    pass


class JiraPermissionError(JiraError):
    """Raised when user lacks required permissions."""

    pass
