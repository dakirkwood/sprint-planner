"""Auth repository interface."""

from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from app.models.auth import JiraAuthToken, JiraProjectContext


class AuthRepositoryInterface(ABC):
    """Interface for auth repository operations."""

    # Token Management
    @abstractmethod
    async def store_tokens(
        self,
        jira_user_id: str,
        access_token: str,
        refresh_token: str,
        expires_in: int,
        granted_scopes: List[str],
    ) -> None:
        """Store OAuth tokens for a user."""
        pass

    @abstractmethod
    async def get_tokens(self, jira_user_id: str) -> Optional[JiraAuthToken]:
        """Get tokens for a user."""
        pass

    @abstractmethod
    async def refresh_tokens(
        self,
        jira_user_id: str,
        new_access_token: str,
        new_refresh_token: str,
        expires_in: int,
    ) -> None:
        """Update tokens after refresh."""
        pass

    @abstractmethod
    async def delete_tokens(self, jira_user_id: str) -> None:
        """Delete tokens for a user."""
        pass

    @abstractmethod
    async def find_expiring_tokens(
        self,
        buffer_minutes: int = 60,
    ) -> List[JiraAuthToken]:
        """Find tokens that will expire soon."""
        pass

    @abstractmethod
    async def token_needs_refresh(
        self,
        jira_user_id: str,
        buffer_minutes: int = 5,
    ) -> bool:
        """Check if token needs refresh."""
        pass

    # Project Context Management
    @abstractmethod
    async def cache_project_context(
        self,
        session_id: UUID,
        project_data: dict,
    ) -> JiraProjectContext:
        """Cache project context for session."""
        pass

    @abstractmethod
    async def get_project_context(
        self,
        session_id: UUID,
    ) -> Optional[JiraProjectContext]:
        """Get cached project context for session."""
        pass

    @abstractmethod
    async def is_project_context_stale(
        self,
        session_id: UUID,
        max_age_hours: int = 24,
    ) -> bool:
        """Check if project context cache is stale."""
        pass

    @abstractmethod
    async def refresh_project_context(
        self,
        session_id: UUID,
        fresh_data: dict,
    ) -> JiraProjectContext:
        """Replace project context with fresh data."""
        pass

    # Validation Support
    @abstractmethod
    async def validate_sprint_name(
        self,
        session_id: UUID,
        sprint_name: str,
    ) -> bool:
        """Validate sprint name against cached data."""
        pass

    @abstractmethod
    async def validate_assignee_id(
        self,
        session_id: UUID,
        account_id: str,
    ) -> bool:
        """Validate assignee ID against cached data."""
        pass

    @abstractmethod
    async def get_active_sprints(self, session_id: UUID) -> List[dict]:
        """Get active sprints from cached data."""
        pass

    @abstractmethod
    async def get_team_members(self, session_id: UUID) -> List[dict]:
        """Get team members from cached data."""
        pass

    # Cleanup
    @abstractmethod
    async def cleanup_expired_tokens(self, grace_period_days: int = 30) -> int:
        """Delete tokens expired beyond grace period. Returns count deleted."""
        pass
