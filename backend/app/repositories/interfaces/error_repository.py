"""Error repository interface."""

from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from app.models.error import SessionError, AuditLog
from app.schemas.base import ErrorCategory, EventCategory, AuditLevel


class ErrorRepositoryInterface(ABC):
    """Interface for error repository operations."""

    # Session Error Operations
    @abstractmethod
    async def create_error(self, error_data: dict) -> SessionError:
        """Create a new session error."""
        pass

    @abstractmethod
    async def get_errors_by_session(
        self,
        session_id: UUID,
        category: Optional[ErrorCategory] = None,
    ) -> List[SessionError]:
        """Get errors for session, optionally filtered by category."""
        pass

    @abstractmethod
    async def get_error_by_id(self, error_id: UUID) -> Optional[SessionError]:
        """Get error by ID."""
        pass

    @abstractmethod
    async def has_blocking_errors(self, session_id: UUID) -> bool:
        """Check if session has any blocking errors."""
        pass

    @abstractmethod
    async def get_errors_by_category(
        self,
        session_id: UUID,
        category: ErrorCategory,
    ) -> List[SessionError]:
        """Get errors of specific category for session."""
        pass

    @abstractmethod
    async def store_errors_with_pattern_detection(
        self,
        session_id: UUID,
        errors: List[dict],
    ) -> List[SessionError]:
        """Store multiple errors and detect patterns."""
        pass

    # Audit Log Operations
    @abstractmethod
    async def log_event(
        self,
        event_type: str,
        category: EventCategory,
        description: str,
        session_id: Optional[UUID] = None,
        jira_user_id: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        event_data: Optional[dict] = None,
        request_id: Optional[str] = None,
        execution_time_ms: Optional[int] = None,
    ) -> AuditLog:
        """Log an audit event."""
        pass

    @abstractmethod
    async def get_session_timeline(self, session_id: UUID) -> List[AuditLog]:
        """Get chronological audit trail for session."""
        pass

    @abstractmethod
    async def get_user_activity(
        self,
        jira_user_id: str,
        days: int = 30,
    ) -> List[AuditLog]:
        """Get user activity over time period."""
        pass

    @abstractmethod
    async def get_audit_events(
        self,
        session_id: Optional[UUID] = None,
        category: Optional[EventCategory] = None,
        audit_level: Optional[AuditLevel] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[AuditLog]:
        """Get audit events with optional filtering."""
        pass

    # Cleanup Operations
    @abstractmethod
    async def cleanup_session_errors(self, session_id: UUID) -> int:
        """Delete all errors for session. Returns count deleted."""
        pass

    @abstractmethod
    async def cleanup_audit_logs(self, retention_days: int = 90) -> int:
        """Delete audit logs older than retention period. Returns count deleted."""
        pass
