# tests/backend/unit/test_repositories/test_session_repository.py
"""
Tests for SessionRepository operations.
"""
import pytest
from uuid import uuid4

from app.repositories.sqlalchemy.session_repository import SQLAlchemySessionRepository
from app.schemas.base import SessionStage, TaskType, TaskStatus


@pytest.mark.phase1
@pytest.mark.repositories
class TestSessionRepositoryCRUD:
    """Test basic CRUD operations."""

    @pytest.fixture
    def repo(self, db_session):
        return SQLAlchemySessionRepository(db_session)

    @pytest.mark.asyncio
    async def test_create_session(self, repo, sample_session_data):
        """Should create a session and return it with ID."""
        session = await repo.create_session(sample_session_data)

        assert session.id is not None
        assert session.site_name == sample_session_data['site_name']
        assert session.current_stage == SessionStage.UPLOAD

    @pytest.mark.asyncio
    async def test_get_session_by_id(self, repo, sample_session_data):
        """Should retrieve session by ID."""
        created = await repo.create_session(sample_session_data)

        retrieved = await repo.get_session_by_id(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.site_name == created.site_name

    @pytest.mark.asyncio
    async def test_get_session_by_id_not_found(self, repo):
        """Should return None for non-existent session."""
        result = await repo.get_session_by_id(uuid4())

        assert result is None

    @pytest.mark.asyncio
    async def test_update_session(self, repo, sample_session_data):
        """Should update session fields."""
        session = await repo.create_session(sample_session_data)

        updated = await repo.update_session(session.id, {'site_name': 'Updated Name'})

        assert updated.site_name == 'Updated Name'

    @pytest.mark.asyncio
    async def test_find_incomplete_sessions_by_user(self, repo, sample_session_data):
        """Should find all non-completed sessions for a user."""
        await repo.create_session(sample_session_data)
        await repo.create_session({**sample_session_data, 'site_name': 'Site 2'})

        sessions = await repo.find_incomplete_sessions_by_user(sample_session_data['jira_user_id'])

        assert len(sessions) == 2


@pytest.mark.phase1
@pytest.mark.repositories
class TestSessionRepositoryStageTransitions:
    """Test stage transition operations."""

    @pytest.fixture
    def repo(self, db_session):
        return SQLAlchemySessionRepository(db_session)

    @pytest.mark.asyncio
    async def test_transition_stage(self, repo, sample_session_data):
        """Should transition session to new stage."""
        session = await repo.create_session(sample_session_data)

        await repo.transition_stage(session.id, SessionStage.PROCESSING)

        updated = await repo.get_session_by_id(session.id)
        assert updated.current_stage == SessionStage.PROCESSING

    @pytest.mark.asyncio
    async def test_can_transition_to_valid_stage(self, repo, sample_session_data):
        """Should allow valid stage transitions."""
        session = await repo.create_session(sample_session_data)

        # UPLOAD -> PROCESSING is valid
        can_transition = await repo.can_transition_to_stage(session.id, SessionStage.PROCESSING)

        assert can_transition is True

    @pytest.mark.asyncio
    async def test_cannot_skip_stages(self, repo, sample_session_data):
        """Should not allow skipping stages."""
        session = await repo.create_session(sample_session_data)

        # UPLOAD -> JIRA_EXPORT is not valid (skips PROCESSING and REVIEW)
        can_transition = await repo.can_transition_to_stage(session.id, SessionStage.JIRA_EXPORT)

        assert can_transition is False


@pytest.mark.phase1
@pytest.mark.repositories
class TestSessionRepositoryTaskOperations:
    """Test SessionTask aggregate operations."""

    @pytest.fixture
    def repo(self, db_session):
        return SQLAlchemySessionRepository(db_session)

    @pytest.mark.asyncio
    async def test_start_task_creates_task_record(self, repo, sample_session_data):
        """Should create SessionTask when starting a task."""
        session = await repo.create_session(sample_session_data)
        task_id = uuid4()

        await repo.start_task(session.id, TaskType.PROCESSING, task_id)

        task = await repo.get_active_task(session.id)
        assert task is not None
        assert task.task_id == task_id
        assert task.task_type == TaskType.PROCESSING
        assert task.status == TaskStatus.RUNNING

    @pytest.mark.asyncio
    async def test_complete_task_updates_status(self, repo, sample_session_data):
        """Should mark task as completed."""
        session = await repo.create_session(sample_session_data)
        await repo.start_task(session.id, TaskType.PROCESSING, uuid4())

        await repo.complete_task(session.id)

        task = await repo.get_active_task(session.id)
        assert task.status == TaskStatus.COMPLETED
        assert task.completed_at is not None

    @pytest.mark.asyncio
    async def test_fail_task_stores_error_context(self, repo, sample_session_data):
        """Should store failure context when task fails."""
        session = await repo.create_session(sample_session_data)
        await repo.start_task(session.id, TaskType.PROCESSING, uuid4())

        error_context = {'error': 'LLM timeout', 'failed_at_entity': 15}
        await repo.fail_task(session.id, error_context)

        task = await repo.get_active_task(session.id)
        assert task.status == TaskStatus.FAILED
        assert task.failure_context == error_context


@pytest.mark.phase1
@pytest.mark.repositories
class TestSessionRepositoryValidationOperations:
    """Test SessionValidation aggregate operations."""

    @pytest.fixture
    def repo(self, db_session):
        return SQLAlchemySessionRepository(db_session)

    @pytest.mark.asyncio
    async def test_start_validation(self, repo, sample_session_data):
        """Should create/update validation record."""
        session = await repo.create_session(sample_session_data)

        await repo.start_validation(session.id)

        # Validation record should exist and be in processing state
        updated = await repo.get_session_by_id(session.id)
        assert updated.session_validation is not None
        assert updated.session_validation.validation_status.value == 'processing'

    @pytest.mark.asyncio
    async def test_complete_validation_passed(self, repo, sample_session_data):
        """Should mark validation as passed."""
        session = await repo.create_session(sample_session_data)
        await repo.start_validation(session.id)

        results = {'passed': 50, 'failed': 0}
        await repo.complete_validation(session.id, passed=True, results=results)

        updated = await repo.get_session_by_id(session.id)
        assert updated.session_validation.validation_passed is True
        assert updated.session_validation.last_validated_at is not None

    @pytest.mark.asyncio
    async def test_invalidate_validation(self, repo, sample_session_data):
        """Should invalidate previous validation."""
        session = await repo.create_session(sample_session_data)
        await repo.start_validation(session.id)
        await repo.complete_validation(session.id, passed=True, results={})

        await repo.invalidate_validation(session.id)

        updated = await repo.get_session_by_id(session.id)
        assert updated.session_validation.validation_passed is False
        assert updated.session_validation.last_invalidated_at is not None

    @pytest.mark.asyncio
    async def test_is_export_ready_requires_passed_validation(self, repo, sample_session_data):
        """Export ready only when validation passed and not invalidated."""
        session = await repo.create_session(sample_session_data)

        # No validation yet
        assert await repo.is_export_ready(session.id) is False

        # Validation passed
        await repo.start_validation(session.id)
        await repo.complete_validation(session.id, passed=True, results={})
        assert await repo.is_export_ready(session.id) is True

        # Validation invalidated
        await repo.invalidate_validation(session.id)
        assert await repo.is_export_ready(session.id) is False
