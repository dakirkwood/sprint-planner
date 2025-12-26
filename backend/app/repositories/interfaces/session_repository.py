"""Session repository interface."""

from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from app.models.session import Session, SessionTask, SessionValidation
from app.schemas.base import SessionStage, TaskType


class SessionRepositoryInterface(ABC):
    """Interface for session repository operations."""

    # Session CRUD
    @abstractmethod
    async def create_session(self, session_data: dict) -> Session:
        """Create a new session."""
        pass

    @abstractmethod
    async def get_session_by_id(self, session_id: UUID) -> Optional[Session]:
        """Get session by ID."""
        pass

    @abstractmethod
    async def update_session(self, session_id: UUID, updates: dict) -> Optional[Session]:
        """Update session fields."""
        pass

    @abstractmethod
    async def find_incomplete_sessions_by_user(self, jira_user_id: str) -> List[Session]:
        """Find all non-completed sessions for a user."""
        pass

    # Stage Transitions
    @abstractmethod
    async def transition_stage(self, session_id: UUID, new_stage: SessionStage) -> None:
        """Transition session to new stage."""
        pass

    @abstractmethod
    async def can_transition_to_stage(
        self,
        session_id: UUID,
        target_stage: SessionStage,
    ) -> bool:
        """Check if session can transition to target stage."""
        pass

    # Session Task Operations
    @abstractmethod
    async def start_task(
        self,
        session_id: UUID,
        task_type: TaskType,
        task_id: UUID,
    ) -> None:
        """Start a task for the session."""
        pass

    @abstractmethod
    async def complete_task(self, session_id: UUID) -> None:
        """Mark task as completed."""
        pass

    @abstractmethod
    async def fail_task(self, session_id: UUID, error_context: dict) -> None:
        """Mark task as failed with error context."""
        pass

    @abstractmethod
    async def get_active_task(self, session_id: UUID) -> Optional[SessionTask]:
        """Get the active task for a session."""
        pass

    # Session Validation Operations
    @abstractmethod
    async def start_validation(self, session_id: UUID) -> None:
        """Start ADF validation for session."""
        pass

    @abstractmethod
    async def complete_validation(
        self,
        session_id: UUID,
        passed: bool,
        results: dict,
    ) -> None:
        """Complete ADF validation with results."""
        pass

    @abstractmethod
    async def invalidate_validation(self, session_id: UUID) -> None:
        """Invalidate previous validation due to ticket edits."""
        pass

    @abstractmethod
    async def is_export_ready(self, session_id: UUID) -> bool:
        """Check if session is ready for export."""
        pass

    # Cleanup
    @abstractmethod
    async def cleanup_expired_sessions(self, retention_days: int = 7) -> int:
        """Delete sessions older than retention period. Returns count deleted."""
        pass
