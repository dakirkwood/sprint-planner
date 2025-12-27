# app/repositories/sqlalchemy/error_repository.py
"""
SQLAlchemy implementation of ErrorRepositoryInterface.
"""
from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.error import SessionError, AuditLog
from app.repositories.interfaces.error_repository import ErrorRepositoryInterface
from app.schemas.base import ErrorCategory, ErrorSeverity, EventCategory, AuditLevel


class SQLAlchemyErrorRepository(ErrorRepositoryInterface):
    """
    SQLAlchemy implementation for error repository operations.
    """

    def __init__(self, session: AsyncSession):
        self._session = session

    # ==========================================================================
    # Session Error Operations
    # ==========================================================================

    async def create_error(self, error_data: dict) -> SessionError:
        """Create a new session error record."""
        error = SessionError(**error_data)
        self._session.add(error)
        await self._session.flush()
        return error

    async def get_errors_by_session(
        self,
        session_id: UUID,
        category: Optional[ErrorCategory] = None
    ) -> List[SessionError]:
        """Get errors for a session, optionally filtered by category."""
        conditions = [SessionError.session_id == session_id]
        if category:
            conditions.append(SessionError.category == category)

        stmt = (
            select(SessionError)
            .where(and_(*conditions))
            .order_by(SessionError.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_error_by_id(self, error_id: UUID) -> Optional[SessionError]:
        """Get error by ID."""
        stmt = select(SessionError).where(SessionError.id == error_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def has_blocking_errors(self, session_id: UUID) -> bool:
        """Check if session has any blocking errors."""
        stmt = (
            select(SessionError)
            .where(SessionError.session_id == session_id)
            .where(SessionError.severity == ErrorSeverity.BLOCKING)
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def get_errors_by_category(
        self,
        session_id: UUID,
        category: ErrorCategory
    ) -> List[SessionError]:
        """Get errors of specific category for session."""
        return await self.get_errors_by_session(session_id, category)

    async def store_errors_with_pattern_detection(
        self,
        session_id: UUID,
        errors: List[dict]
    ) -> List[SessionError]:
        """Store multiple errors with pattern detection for grouping."""
        # Simple implementation - store all errors
        # Pattern detection could be enhanced later
        created_errors = []
        for error_data in errors:
            error_data["session_id"] = session_id
            error = SessionError(**error_data)
            self._session.add(error)
            created_errors.append(error)

        await self._session.flush()
        return created_errors

    # ==========================================================================
    # Audit Log Operations
    # ==========================================================================

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
        execution_time_ms: Optional[int] = None
    ) -> AuditLog:
        """Log an audit event."""
        log_entry = AuditLog(
            event_type=event_type,
            category=category,
            description=description,
            session_id=session_id,
            jira_user_id=jira_user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            event_data=event_data,
            request_id=request_id,
            execution_time_ms=execution_time_ms,
            created_at=datetime.utcnow()
        )
        self._session.add(log_entry)
        await self._session.flush()
        return log_entry

    async def get_session_timeline(self, session_id: UUID) -> List[AuditLog]:
        """Get chronological audit timeline for session."""
        stmt = (
            select(AuditLog)
            .where(AuditLog.session_id == session_id)
            .order_by(AuditLog.created_at)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_user_activity(self, jira_user_id: str, days: int = 30) -> List[AuditLog]:
        """Get recent activity for a user."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        stmt = (
            select(AuditLog)
            .where(AuditLog.jira_user_id == jira_user_id)
            .where(AuditLog.created_at > cutoff)
            .order_by(AuditLog.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_audit_events(
        self,
        session_id: Optional[UUID] = None,
        category: Optional[EventCategory] = None,
        audit_level: Optional[AuditLevel] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[AuditLog]:
        """Query audit events with filters."""
        conditions = []

        if session_id:
            conditions.append(AuditLog.session_id == session_id)
        if category:
            conditions.append(AuditLog.category == category)
        if audit_level:
            conditions.append(AuditLog.audit_level == audit_level)
        if start_date:
            conditions.append(AuditLog.created_at >= start_date)
        if end_date:
            conditions.append(AuditLog.created_at <= end_date)

        stmt = select(AuditLog)
        if conditions:
            stmt = stmt.where(and_(*conditions))
        stmt = stmt.order_by(AuditLog.created_at.desc())

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    # ==========================================================================
    # Cleanup Operations
    # ==========================================================================

    async def cleanup_session_errors(self, session_id: UUID) -> int:
        """Delete all errors for a session. Returns count deleted."""
        stmt = delete(SessionError).where(SessionError.session_id == session_id)
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount

    async def cleanup_audit_logs(self, retention_days: int = 90) -> int:
        """Delete audit logs older than retention period. Returns count deleted."""
        cutoff = datetime.utcnow() - timedelta(days=retention_days)
        stmt = delete(AuditLog).where(AuditLog.created_at < cutoff)
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount
