"""Tests for SQLAlchemy session repository."""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from app.repositories.sqlalchemy.session_repository import SQLAlchemySessionRepository
from app.models.session import Session, SessionTask, SessionValidation
from app.schemas.base import SessionStage, SessionStatus, TaskType, TaskStatus


class TestSessionRepositoryCreate:
    """Test session creation methods."""

    @pytest.mark.asyncio
    async def test_create_session_minimal(self, db_session):
        """Create session with minimal required fields."""
        repo = SQLAlchemySessionRepository(db_session)

        session = await repo.create_session({
            "jira_user_id": "test-user-1",
        })

        assert session.id is not None
        assert session.jira_user_id == "test-user-1"
        assert session.current_stage == SessionStage.UPLOAD.value
        assert session.status == SessionStatus.ACTIVE.value

    @pytest.mark.asyncio
    async def test_create_session_full_data(self, db_session, sample_session_data):
        """Create session with all fields."""
        repo = SQLAlchemySessionRepository(db_session)

        session = await repo.create_session(sample_session_data)

        assert session.jira_user_id == sample_session_data["jira_user_id"]
        assert session.jira_display_name == sample_session_data["jira_display_name"]
        assert session.site_name == sample_session_data["site_name"]
        assert session.jira_project_key == sample_session_data["jira_project_key"]


class TestSessionRepositoryRead:
    """Test session retrieval methods."""

    @pytest.mark.asyncio
    async def test_get_session_by_id(self, db_session, sample_session):
        """Get session by ID."""
        repo = SQLAlchemySessionRepository(db_session)

        result = await repo.get_session_by_id(sample_session.id)

        assert result is not None
        assert result.id == sample_session.id

    @pytest.mark.asyncio
    async def test_get_session_by_id_not_found(self, db_session):
        """Get session by non-existent ID."""
        repo = SQLAlchemySessionRepository(db_session)

        result = await repo.get_session_by_id(uuid4())

        assert result is None

    @pytest.mark.asyncio
    async def test_find_incomplete_sessions_by_user(self, db_session):
        """Find incomplete sessions for a user."""
        repo = SQLAlchemySessionRepository(db_session)

        # Create multiple sessions for same user
        session1 = await repo.create_session({"jira_user_id": "user-a"})
        session2 = await repo.create_session({"jira_user_id": "user-a"})
        await repo.create_session({"jira_user_id": "user-b"})

        # Mark one as completed
        session1.status = SessionStatus.COMPLETED.value
        await db_session.flush()

        results = await repo.find_incomplete_sessions_by_user("user-a")

        assert len(results) == 1
        assert results[0].id == session2.id


class TestSessionRepositoryUpdate:
    """Test session update methods."""

    @pytest.mark.asyncio
    async def test_update_session(self, db_session, sample_session):
        """Update session fields."""
        repo = SQLAlchemySessionRepository(db_session)

        result = await repo.update_session(
            sample_session.id,
            {"site_name": "Updated Name", "jira_project_key": "UPDATED"},
        )

        assert result is not None
        assert result.site_name == "Updated Name"
        assert result.jira_project_key == "UPDATED"

    @pytest.mark.asyncio
    async def test_update_session_not_found(self, db_session):
        """Update non-existent session."""
        repo = SQLAlchemySessionRepository(db_session)

        result = await repo.update_session(uuid4(), {"site_name": "New Name"})

        assert result is None


class TestSessionStageTransitions:
    """Test session stage transition methods."""

    @pytest.mark.asyncio
    async def test_transition_stage(self, db_session, sample_session):
        """Transition session to new stage."""
        repo = SQLAlchemySessionRepository(db_session)

        # Use actual enum values from base.py
        await repo.transition_stage(sample_session.id, SessionStage.PROCESSING)

        session = await repo.get_session_by_id(sample_session.id)
        assert session.current_stage == SessionStage.PROCESSING.value

    @pytest.mark.asyncio
    async def test_transition_to_completed_sets_status(self, db_session, sample_session):
        """Transitioning to completed stage sets completed status."""
        repo = SQLAlchemySessionRepository(db_session)

        # Progress through stages using actual enum values
        await repo.transition_stage(sample_session.id, SessionStage.PROCESSING)
        await repo.transition_stage(sample_session.id, SessionStage.REVIEW)
        await repo.transition_stage(sample_session.id, SessionStage.JIRA_EXPORT)
        await repo.transition_stage(sample_session.id, SessionStage.COMPLETED)

        session = await repo.get_session_by_id(sample_session.id)
        assert session.status == SessionStatus.COMPLETED.value
        assert session.completed_at is not None

    @pytest.mark.asyncio
    async def test_can_transition_to_stage(self, db_session, sample_session):
        """Check if session can transition to stage."""
        repo = SQLAlchemySessionRepository(db_session)

        # From UPLOAD, can go to PROCESSING
        assert await repo.can_transition_to_stage(sample_session.id, SessionStage.PROCESSING)

        # Cannot skip to COMPLETED
        assert not await repo.can_transition_to_stage(sample_session.id, SessionStage.COMPLETED)


class TestSessionTaskMethods:
    """Test task-related methods."""

    @pytest.mark.asyncio
    async def test_start_task(self, db_session, sample_session):
        """Start a task for session."""
        repo = SQLAlchemySessionRepository(db_session)
        task_id = uuid4()

        # Use actual TaskType enum
        await repo.start_task(sample_session.id, TaskType.PROCESSING, task_id)

        task = await repo.get_active_task(sample_session.id)
        assert task is not None
        assert task.task_type == TaskType.PROCESSING.value
        assert task.task_id == task_id
        assert task.status == TaskStatus.RUNNING.value

    @pytest.mark.asyncio
    async def test_complete_task(self, db_session, sample_session):
        """Complete a running task."""
        repo = SQLAlchemySessionRepository(db_session)
        task_id = uuid4()

        await repo.start_task(sample_session.id, TaskType.PROCESSING, task_id)
        await repo.complete_task(sample_session.id)

        task = await repo.get_active_task(sample_session.id)
        assert task.status == TaskStatus.COMPLETED.value
        assert task.completed_at is not None

    @pytest.mark.asyncio
    async def test_fail_task(self, db_session, sample_session):
        """Fail a running task."""
        repo = SQLAlchemySessionRepository(db_session)
        task_id = uuid4()
        error_context = {"error": "Test error", "code": "TEST_ERR"}

        await repo.start_task(sample_session.id, TaskType.PROCESSING, task_id)
        await repo.fail_task(sample_session.id, error_context)

        task = await repo.get_active_task(sample_session.id)
        assert task.status == TaskStatus.FAILED.value
        assert task.failed_at is not None
        assert task.failure_context == error_context


class TestSessionValidationMethods:
    """Test validation-related methods."""

    @pytest.mark.asyncio
    async def test_start_validation(self, db_session, sample_session):
        """Start validation for session."""
        repo = SQLAlchemySessionRepository(db_session)

        await repo.start_validation(sample_session.id)

        session = await repo.get_session_by_id(sample_session.id)
        assert session.session_validation is not None
        assert session.session_validation.validation_status == "processing"

    @pytest.mark.asyncio
    async def test_complete_validation_passed(self, db_session, sample_session):
        """Complete validation with passed result."""
        repo = SQLAlchemySessionRepository(db_session)
        results = {"valid_tickets": 10, "issues": []}

        await repo.start_validation(sample_session.id)
        await repo.complete_validation(sample_session.id, passed=True, results=results)

        session = await repo.get_session_by_id(sample_session.id)
        assert session.session_validation.validation_passed is True
        assert session.session_validation.validation_results == results

    @pytest.mark.asyncio
    async def test_invalidate_validation(self, db_session, sample_session):
        """Invalidate validation after ticket edits."""
        repo = SQLAlchemySessionRepository(db_session)

        await repo.start_validation(sample_session.id)
        await repo.complete_validation(sample_session.id, passed=True, results={})
        await repo.invalidate_validation(sample_session.id)

        session = await repo.get_session_by_id(sample_session.id)
        assert session.session_validation.validation_passed is False

    @pytest.mark.asyncio
    async def test_is_export_ready(self, db_session, sample_session):
        """Check export readiness."""
        repo = SQLAlchemySessionRepository(db_session)

        # Not ready before validation
        assert await repo.is_export_ready(sample_session.id) is False

        # Complete validation
        await repo.start_validation(sample_session.id)
        await repo.complete_validation(sample_session.id, passed=True, results={})

        assert await repo.is_export_ready(sample_session.id) is True


class TestSessionCleanup:
    """Test cleanup methods."""

    @pytest.mark.asyncio
    async def test_cleanup_expired_sessions(self, db_session):
        """Cleanup expired sessions."""
        repo = SQLAlchemySessionRepository(db_session)

        # Create an old session
        old_session = Session(
            jira_user_id="old-user",
            created_at=datetime.utcnow() - timedelta(days=10),
        )
        db_session.add(old_session)
        await db_session.flush()

        # Create a recent session
        recent_session = await repo.create_session({"jira_user_id": "new-user"})

        deleted = await repo.cleanup_expired_sessions(retention_days=7)

        assert deleted == 1

        # Recent session should still exist
        result = await repo.get_session_by_id(recent_session.id)
        assert result is not None
