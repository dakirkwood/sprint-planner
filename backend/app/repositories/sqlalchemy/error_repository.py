"""SQLAlchemy implementation of error repository."""

from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.error import SessionError, AuditLog
from app.repositories.interfaces.error_repository import ErrorRepositoryInterface
from app.schemas.base import (
    ErrorCategory,
    ErrorSeverity,
    EventCategory,
    AuditLevel,
)


class SQLAlchemyErrorRepository(ErrorRepositoryInterface):
    """SQLAlchemy implementation of error repository."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def create_error(self, error_data: dict) -> SessionError:
        """Create a new session error."""
        error = SessionError(
            session_id=error_data["session_id"],
            error_category=error_data["error_category"],
            severity=error_data.get("severity", ErrorSeverity.BLOCKING.value),
            operation_stage=error_data["operation_stage"],
            related_file_id=error_data.get("related_file_id"),
            related_ticket_id=error_data.get("related_ticket_id"),
            user_message=error_data["user_message"],
            recovery_actions=error_data.get("recovery_actions", {"actions": []}),
            technical_details=error_data.get("technical_details", {}),
            error_code=error_data.get("error_code"),
        )
        self.db.add(error)
        await self.db.flush()
        return error

    async def get_errors_by_session(
        self,
        session_id: UUID,
        category: Optional[ErrorCategory] = None,
    ) -> List[SessionError]:
        """Get errors for session, optionally filtered by category."""
        conditions = [SessionError.session_id == session_id]
        if category:
            conditions.append(SessionError.error_category == category.value)

        stmt = (
            select(SessionError)
            .where(and_(*conditions))
            .order_by(SessionError.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_error_by_id(self, error_id: UUID) -> Optional[SessionError]:
        """Get error by ID."""
        stmt = select(SessionError).where(SessionError.id == error_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def has_blocking_errors(self, session_id: UUID) -> bool:
        """Check if session has any blocking errors."""
        stmt = select(SessionError).where(
            SessionError.session_id == session_id,
            SessionError.severity == ErrorSeverity.BLOCKING.value,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def get_errors_by_category(
        self,
        session_id: UUID,
        category: ErrorCategory,
    ) -> List[SessionError]:
        """Get errors of specific category for session."""
        return await self.get_errors_by_session(session_id, category)

    async def store_errors_with_pattern_detection(
        self,
        session_id: UUID,
        errors: List[dict],
    ) -> List[SessionError]:
        """Store multiple errors and detect patterns."""
        created_errors = []

        for error_data in errors:
            error_data["session_id"] = session_id
            error = await self.create_error(error_data)
            created_errors.append(error)

        return created_errors

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
        # Determine audit level based on event_data presence
        audit_level = (
            AuditLevel.COMPREHENSIVE.value
            if event_data
            else AuditLevel.BASIC.value
        )

        log = AuditLog(
            session_id=session_id,
            jira_user_id=jira_user_id,
            event_type=event_type,
            event_category=category.value,
            audit_level=audit_level,
            description=description,
            entity_type=entity_type,
            entity_id=entity_id,
            event_data=event_data,
            request_id=request_id,
            execution_time_ms=execution_time_ms,
        )
        self.db.add(log)
        await self.db.flush()
        return log

    async def get_session_timeline(self, session_id: UUID) -> List[AuditLog]:
        """Get chronological audit trail for session."""
        stmt = (
            select(AuditLog)
            .where(AuditLog.session_id == session_id)
            .order_by(AuditLog.created_at)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_user_activity(
        self,
        jira_user_id: str,
        days: int = 30,
    ) -> List[AuditLog]:
        """Get user activity over time period."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        stmt = (
            select(AuditLog)
            .where(
                AuditLog.jira_user_id == jira_user_id,
                AuditLog.created_at > cutoff,
            )
            .order_by(AuditLog.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_audit_events(
        self,
        session_id: Optional[UUID] = None,
        category: Optional[EventCategory] = None,
        audit_level: Optional[AuditLevel] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[AuditLog]:
        """Get audit events with optional filtering."""
        conditions = []

        if session_id:
            conditions.append(AuditLog.session_id == session_id)
        if category:
            conditions.append(AuditLog.event_category == category.value)
        if audit_level:
            conditions.append(AuditLog.audit_level == audit_level.value)
        if start_date:
            conditions.append(AuditLog.created_at >= start_date)
        if end_date:
            conditions.append(AuditLog.created_at <= end_date)

        if conditions:
            stmt = (
                select(AuditLog)
                .where(and_(*conditions))
                .order_by(AuditLog.created_at.desc())
            )
        else:
            stmt = select(AuditLog).order_by(AuditLog.created_at.desc())

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def cleanup_session_errors(self, session_id: UUID) -> int:
        """Delete all errors for session."""
        stmt = delete(SessionError).where(SessionError.session_id == session_id)
        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.rowcount

    async def cleanup_audit_logs(self, retention_days: int = 90) -> int:
        """Delete audit logs older than retention period."""
        cutoff = datetime.utcnow() - timedelta(days=retention_days)
        stmt = delete(AuditLog).where(AuditLog.created_at < cutoff)
        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.rowcount
