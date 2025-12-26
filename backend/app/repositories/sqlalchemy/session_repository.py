"""SQLAlchemy implementation of session repository."""

from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID, uuid4

from sqlalchemy import select, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.session import Session, SessionTask, SessionValidation
from app.repositories.interfaces.session_repository import SessionRepositoryInterface
from app.schemas.base import (
    SessionStage,
    SessionStatus,
    TaskType,
    TaskStatus,
    AdfValidationStatus,
)


class SQLAlchemySessionRepository(SessionRepositoryInterface):
    """SQLAlchemy implementation of session repository."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def create_session(self, session_data: dict) -> Session:
        """Create a new session."""
        session = Session(
            jira_user_id=session_data["jira_user_id"],
            jira_display_name=session_data.get("jira_display_name"),
            site_name=session_data.get("site_name"),
            site_description=session_data.get("site_description"),
            jira_project_key=session_data.get("jira_project_key"),
            llm_provider_choice=session_data.get("llm_provider_choice"),
            current_stage=session_data.get("current_stage", SessionStage.UPLOAD.value),
            status=session_data.get("status", SessionStatus.ACTIVE.value),
        )
        self.db.add(session)
        await self.db.flush()
        return session

    async def get_session_by_id(self, session_id: UUID) -> Optional[Session]:
        """Get session by ID with eager-loaded relationships."""
        stmt = (
            select(Session)
            .options(
                selectinload(Session.session_task),
                selectinload(Session.session_validation),
                selectinload(Session.uploaded_files),
            )
            .where(Session.id == session_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_session(
        self,
        session_id: UUID,
        updates: dict,
    ) -> Optional[Session]:
        """Update session fields."""
        session = await self.get_session_by_id(session_id)
        if not session:
            return None

        for key, value in updates.items():
            if hasattr(session, key):
                setattr(session, key, value)

        await self.db.flush()
        return session

    async def find_incomplete_sessions_by_user(
        self,
        jira_user_id: str,
    ) -> List[Session]:
        """Find all non-completed sessions for a user."""
        stmt = (
            select(Session)
            .where(
                and_(
                    Session.jira_user_id == jira_user_id,
                    Session.status != SessionStatus.COMPLETED.value,
                )
            )
            .order_by(Session.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def transition_stage(
        self,
        session_id: UUID,
        new_stage: SessionStage,
    ) -> None:
        """Transition session to new stage."""
        session = await self.get_session_by_id(session_id)
        if not session:
            return

        session.current_stage = new_stage.value

        # Mark as completed if transitioning to completed stage
        if new_stage == SessionStage.COMPLETED:
            session.status = SessionStatus.COMPLETED.value
            session.completed_at = datetime.utcnow()

        await self.db.flush()

    async def can_transition_to_stage(
        self,
        session_id: UUID,
        target_stage: SessionStage,
    ) -> bool:
        """Check if session can transition to target stage."""
        session = await self.get_session_by_id(session_id)
        if not session:
            return False
        return session.can_transition_to(target_stage)

    async def start_task(
        self,
        session_id: UUID,
        task_type: TaskType,
        task_id: UUID,
    ) -> None:
        """Start a task for the session."""
        session = await self.get_session_by_id(session_id)
        if not session:
            return

        # Create or update SessionTask
        if session.session_task:
            session.session_task.mark_started(task_id)
            session.session_task.task_type = task_type.value
        else:
            session_task = SessionTask(
                session_id=session_id,
                task_type=task_type.value,
                task_id=task_id,
                status=TaskStatus.RUNNING.value,
            )
            self.db.add(session_task)

        await self.db.flush()

    async def complete_task(self, session_id: UUID) -> None:
        """Mark task as completed."""
        task = await self.get_active_task(session_id)
        if task:
            task.mark_completed()
            await self.db.flush()

    async def fail_task(self, session_id: UUID, error_context: dict) -> None:
        """Mark task as failed with error context."""
        task = await self.get_active_task(session_id)
        if task:
            task.mark_failed(error_context)
            await self.db.flush()

    async def get_active_task(self, session_id: UUID) -> Optional[SessionTask]:
        """Get the active task for a session."""
        stmt = select(SessionTask).where(SessionTask.session_id == session_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_validation(self, session_id: UUID) -> Optional[SessionValidation]:
        """Get session validation by session_id."""
        stmt = select(SessionValidation).where(SessionValidation.session_id == session_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def start_validation(self, session_id: UUID) -> None:
        """Start ADF validation for session."""
        validation = await self._get_validation(session_id)

        if validation:
            validation.mark_validation_started()
        else:
            validation = SessionValidation(
                session_id=session_id,
                validation_status=AdfValidationStatus.PROCESSING.value,
            )
            self.db.add(validation)

        await self.db.flush()

    async def complete_validation(
        self,
        session_id: UUID,
        passed: bool,
        results: dict,
    ) -> None:
        """Complete ADF validation with results."""
        validation = await self._get_validation(session_id)
        if validation:
            validation.mark_validation_completed(passed, results)
            await self.db.flush()

    async def invalidate_validation(self, session_id: UUID) -> None:
        """Invalidate previous validation due to ticket edits."""
        validation = await self._get_validation(session_id)
        if validation:
            validation.invalidate_validation()
            await self.db.flush()

    async def is_export_ready(self, session_id: UUID) -> bool:
        """Check if session is ready for export."""
        validation = await self._get_validation(session_id)
        if not validation:
            return False
        return validation.is_export_ready

    async def cleanup_expired_sessions(self, retention_days: int = 7) -> int:
        """Delete sessions older than retention period."""
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

        stmt = delete(Session).where(
            and_(
                Session.created_at < cutoff_date,
                Session.status != SessionStatus.COMPLETED.value,
            )
        )
        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.rowcount
