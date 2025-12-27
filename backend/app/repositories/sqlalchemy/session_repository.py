# app/repositories/sqlalchemy/session_repository.py
"""
SQLAlchemy implementation of SessionRepositoryInterface.
"""
from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.session import Session, SessionTask, SessionValidation
from app.repositories.interfaces.session_repository import SessionRepositoryInterface
from app.schemas.base import (
    SessionStage,
    SessionStatus,
    TaskType,
    TaskStatus,
    AdfValidationStatus
)


class SQLAlchemySessionRepository(SessionRepositoryInterface):
    """
    SQLAlchemy implementation for session repository operations.
    """

    def __init__(self, session: AsyncSession):
        self._session = session

    # ==========================================================================
    # Session CRUD Operations
    # ==========================================================================

    async def create_session(self, session_data: dict) -> Session:
        """Create a new session."""
        session = Session(**session_data)
        self._session.add(session)
        await self._session.flush()
        return session

    async def get_session_by_id(self, session_id: UUID) -> Optional[Session]:
        """Get session by ID, including related task and validation."""
        stmt = (
            select(Session)
            .options(
                selectinload(Session.session_task),
                selectinload(Session.session_validation)
            )
            .where(Session.id == session_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_session(self, session_id: UUID, updates: dict) -> Session:
        """Update session fields."""
        session = await self.get_session_by_id(session_id)
        if session is None:
            raise ValueError(f"Session not found: {session_id}")

        for key, value in updates.items():
            if hasattr(session, key):
                setattr(session, key, value)

        await self._session.flush()
        return session

    async def find_incomplete_sessions_by_user(self, jira_user_id: str) -> List[Session]:
        """Find all non-completed sessions for a user."""
        stmt = (
            select(Session)
            .where(Session.jira_user_id == jira_user_id)
            .where(Session.status != SessionStatus.COMPLETED)
            .order_by(Session.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    # ==========================================================================
    # Stage Transitions
    # ==========================================================================

    async def transition_stage(self, session_id: UUID, new_stage: SessionStage) -> None:
        """Transition session to a new stage."""
        session = await self.get_session_by_id(session_id)
        if session is None:
            raise ValueError(f"Session not found: {session_id}")

        if not session.can_transition_to(new_stage):
            raise ValueError(
                f"Cannot transition from {session.current_stage} to {new_stage}"
            )

        session.current_stage = new_stage

        # Handle completion
        if new_stage == SessionStage.COMPLETED:
            session.status = SessionStatus.COMPLETED
            session.completed_at = datetime.utcnow()

        await self._session.flush()

    async def can_transition_to_stage(self, session_id: UUID, target_stage: SessionStage) -> bool:
        """Check if session can transition to target stage."""
        session = await self.get_session_by_id(session_id)
        if session is None:
            return False
        return session.can_transition_to(target_stage)

    # ==========================================================================
    # Session Task Operations
    # ==========================================================================

    async def start_task(self, session_id: UUID, task_type: TaskType, task_id: UUID) -> None:
        """Start a background task for the session."""
        # Check if task already exists
        stmt = select(SessionTask).where(SessionTask.session_id == session_id)
        result = await self._session.execute(stmt)
        existing_task = result.scalar_one_or_none()

        if existing_task:
            # Update existing task
            existing_task.task_id = task_id
            existing_task.task_type = task_type
            existing_task.status = TaskStatus.RUNNING
            existing_task.started_at = datetime.utcnow()
            existing_task.completed_at = None
            existing_task.failure_context = None
        else:
            # Create new task
            new_task = SessionTask(
                session_id=session_id,
                task_id=task_id,
                task_type=task_type,
                status=TaskStatus.RUNNING,
                started_at=datetime.utcnow()
            )
            self._session.add(new_task)

        await self._session.flush()

    async def complete_task(self, session_id: UUID) -> None:
        """Mark the current task as completed."""
        stmt = select(SessionTask).where(SessionTask.session_id == session_id)
        result = await self._session.execute(stmt)
        task = result.scalar_one_or_none()

        if task:
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.utcnow()
            await self._session.flush()

    async def fail_task(self, session_id: UUID, error_context: dict) -> None:
        """Mark the current task as failed with error context."""
        stmt = select(SessionTask).where(SessionTask.session_id == session_id)
        result = await self._session.execute(stmt)
        task = result.scalar_one_or_none()

        if task:
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.utcnow()
            task.failure_context = error_context
            task.retry_count += 1
            await self._session.flush()

    async def get_active_task(self, session_id: UUID) -> Optional[SessionTask]:
        """Get the active task for a session."""
        stmt = select(SessionTask).where(SessionTask.session_id == session_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    # ==========================================================================
    # Session Validation Operations
    # ==========================================================================

    async def start_validation(self, session_id: UUID) -> None:
        """Start ADF validation for the session."""
        stmt = select(SessionValidation).where(SessionValidation.session_id == session_id)
        result = await self._session.execute(stmt)
        existing_validation = result.scalar_one_or_none()

        if existing_validation:
            existing_validation.validation_status = AdfValidationStatus.PROCESSING
        else:
            new_validation = SessionValidation(
                session_id=session_id,
                validation_status=AdfValidationStatus.PROCESSING
            )
            self._session.add(new_validation)

        await self._session.flush()

    async def complete_validation(self, session_id: UUID, passed: bool, results: dict) -> None:
        """Complete validation with results."""
        stmt = select(SessionValidation).where(SessionValidation.session_id == session_id)
        result = await self._session.execute(stmt)
        validation = result.scalar_one_or_none()

        if validation:
            validation.validation_status = AdfValidationStatus.COMPLETED
            validation.validation_passed = passed
            validation.validation_results = results
            validation.last_validated_at = datetime.utcnow()
            await self._session.flush()

    async def invalidate_validation(self, session_id: UUID) -> None:
        """Invalidate previous validation (e.g., after ticket edit)."""
        stmt = select(SessionValidation).where(SessionValidation.session_id == session_id)
        result = await self._session.execute(stmt)
        validation = result.scalar_one_or_none()

        if validation:
            validation.validation_passed = False
            validation.last_invalidated_at = datetime.utcnow()
            await self._session.flush()

    async def is_export_ready(self, session_id: UUID) -> bool:
        """Check if session is ready for Jira export."""
        stmt = select(SessionValidation).where(SessionValidation.session_id == session_id)
        result = await self._session.execute(stmt)
        validation = result.scalar_one_or_none()

        if not validation:
            return False

        # Must be validated and not invalidated after last validation
        if not validation.validation_passed:
            return False

        if validation.last_invalidated_at and validation.last_validated_at:
            return validation.last_validated_at > validation.last_invalidated_at

        return validation.validation_passed

    # ==========================================================================
    # Cleanup Operations
    # ==========================================================================

    async def cleanup_expired_sessions(self, retention_days: int = 7) -> int:
        """Delete sessions older than retention period. Returns count deleted."""
        cutoff = datetime.utcnow() - timedelta(days=retention_days)
        stmt = (
            delete(Session)
            .where(Session.created_at < cutoff)
            .where(Session.status == SessionStatus.COMPLETED)
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount
