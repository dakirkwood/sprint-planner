"""Tests for Session, SessionTask, and SessionValidation models."""

import pytest
from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import inspect

from app.models.session import Session, SessionTask, SessionValidation, STAGE_ORDER
from app.schemas.base import (
    SessionStage,
    SessionStatus,
    TaskType,
    TaskStatus,
    AdfValidationStatus,
)


class TestSessionModel:
    """Test Session model field definitions and relationships."""

    def test_session_has_required_fields(self):
        """Session model must have all specified fields."""
        mapper = inspect(Session)
        columns = {c.key for c in mapper.columns}

        required_fields = {
            "id",
            "jira_user_id",
            "jira_display_name",
            "site_name",
            "site_description",
            "llm_provider_choice",
            "jira_project_key",
            "current_stage",
            "status",
            "total_tickets_generated",
            "created_at",
            "updated_at",
            "completed_at",
        }
        assert required_fields.issubset(columns)

    @pytest.mark.asyncio
    async def test_session_default_stage_is_upload(self, db_session, sample_session_data):
        """New sessions should default to UPLOAD stage."""
        session = Session(**sample_session_data)
        db_session.add(session)
        await db_session.flush()

        assert session.current_stage == SessionStage.UPLOAD.value

    @pytest.mark.asyncio
    async def test_session_default_status_is_active(self, db_session, sample_session_data):
        """New sessions should default to ACTIVE status."""
        session = Session(**sample_session_data)
        db_session.add(session)
        await db_session.flush()

        assert session.status == SessionStatus.ACTIVE.value

    @pytest.mark.asyncio
    async def test_session_generates_uuid_on_create(self, db_session, sample_session_data):
        """Session should auto-generate UUID primary key."""
        session = Session(**sample_session_data)
        db_session.add(session)
        await db_session.flush()

        assert session.id is not None
        assert isinstance(session.id, UUID)

    @pytest.mark.asyncio
    async def test_session_sets_timestamps_on_create(self, db_session, sample_session_data):
        """Session should set created_at and updated_at on creation."""
        session = Session(**sample_session_data)
        db_session.add(session)
        await db_session.flush()

        assert session.created_at is not None
        assert session.updated_at is not None
        assert isinstance(session.created_at, datetime)

    def test_session_has_relationship_to_session_task(self):
        """Session should have 1:1 relationship with SessionTask."""
        mapper = inspect(Session)
        relationships = {r.key for r in mapper.relationships}

        assert "session_task" in relationships

    def test_session_has_relationship_to_session_validation(self):
        """Session should have 1:1 relationship with SessionValidation."""
        mapper = inspect(Session)
        relationships = {r.key for r in mapper.relationships}

        assert "session_validation" in relationships

    def test_session_has_relationship_to_tickets(self):
        """Session should have 1:Many relationship with Tickets."""
        mapper = inspect(Session)
        relationships = {r.key for r in mapper.relationships}

        assert "tickets" in relationships

    def test_session_has_relationship_to_uploaded_files(self):
        """Session should have 1:Many relationship with UploadedFiles."""
        mapper = inspect(Session)
        relationships = {r.key for r in mapper.relationships}

        assert "uploaded_files" in relationships

    def test_can_transition_to_valid_next_stage(self):
        """Session can transition to the next sequential stage."""
        session = Session(jira_user_id="test", current_stage=SessionStage.UPLOAD.value)
        assert session.can_transition_to(SessionStage.PROCESSING) is True

    def test_cannot_skip_stages(self):
        """Session cannot skip stages."""
        session = Session(jira_user_id="test", current_stage=SessionStage.UPLOAD.value)
        assert session.can_transition_to(SessionStage.JIRA_EXPORT) is False

    def test_can_stay_at_same_stage(self):
        """Session can stay at the same stage."""
        session = Session(jira_user_id="test", current_stage=SessionStage.UPLOAD.value)
        assert session.can_transition_to(SessionStage.UPLOAD) is True

    def test_is_recoverable_when_active(self):
        """Active sessions are recoverable."""
        session = Session(
            jira_user_id="test",
            current_stage=SessionStage.UPLOAD.value,
            status=SessionStatus.ACTIVE.value,
        )
        assert session.is_recoverable is True

    def test_is_not_recoverable_when_completed(self):
        """Completed sessions are not recoverable."""
        session = Session(
            jira_user_id="test",
            current_stage=SessionStage.COMPLETED.value,
            status=SessionStatus.COMPLETED.value,
        )
        assert session.is_recoverable is False

    def test_stage_display_name(self):
        """Stage display name returns human-readable value."""
        session = Session(jira_user_id="test", current_stage=SessionStage.UPLOAD.value)
        assert session.stage_display_name == "File Upload"


class TestSessionTaskModel:
    """Test SessionTask model for background task tracking."""

    def test_session_task_has_required_fields(self):
        """SessionTask must have all specified fields."""
        mapper = inspect(SessionTask)
        columns = {c.key for c in mapper.columns}

        required_fields = {
            "id",
            "session_id",
            "task_id",
            "task_type",
            "status",
            "started_at",
            "completed_at",
            "failed_at",
            "retry_count",
            "failure_context",
        }
        assert required_fields.issubset(columns)

    def test_task_type_enum_values(self):
        """TaskType enum must have expected values."""
        expected = {"processing", "export", "adf_validation"}
        actual = {e.value for e in TaskType}

        assert expected == actual

    def test_task_status_enum_values(self):
        """TaskStatus enum must have expected values."""
        expected = {"running", "completed", "failed", "cancelled"}
        actual = {e.value for e in TaskStatus}

        assert expected == actual

    @pytest.mark.asyncio
    async def test_session_task_defaults(self, db_session, sample_session):
        """SessionTask should have correct defaults."""
        task = SessionTask(
            session_id=sample_session.id,
            task_type=TaskType.PROCESSING.value,
            task_id=uuid4(),
        )
        db_session.add(task)
        await db_session.flush()

        assert task.status == TaskStatus.RUNNING.value
        assert task.retry_count == 0

    def test_can_retry_when_failed_and_under_limit(self):
        """Task can be retried when failed and under retry limit."""
        task = SessionTask(
            session_id=uuid4(),
            task_type=TaskType.PROCESSING.value,
            task_id=uuid4(),
            status=TaskStatus.FAILED.value,
            retry_count=2,
        )
        assert task.can_retry() is True

    def test_cannot_retry_when_at_limit(self):
        """Task cannot be retried when at retry limit."""
        task = SessionTask(
            session_id=uuid4(),
            task_type=TaskType.PROCESSING.value,
            task_id=uuid4(),
            status=TaskStatus.FAILED.value,
            retry_count=3,
        )
        assert task.can_retry() is False

    def test_cannot_retry_when_running(self):
        """Task cannot be retried when running."""
        task = SessionTask(
            session_id=uuid4(),
            task_type=TaskType.PROCESSING.value,
            task_id=uuid4(),
            status=TaskStatus.RUNNING.value,
            retry_count=0,
        )
        assert task.can_retry() is False

    def test_mark_completed_sets_status_and_timestamp(self):
        """mark_completed sets status and timestamp."""
        task = SessionTask(
            session_id=uuid4(),
            task_type=TaskType.PROCESSING.value,
            task_id=uuid4(),
            status=TaskStatus.RUNNING.value,
        )
        task.mark_completed()

        assert task.status == TaskStatus.COMPLETED.value
        assert task.completed_at is not None

    def test_mark_failed_stores_error_context(self):
        """mark_failed stores error context and increments retry count."""
        task = SessionTask(
            session_id=uuid4(),
            task_type=TaskType.PROCESSING.value,
            task_id=uuid4(),
            status=TaskStatus.RUNNING.value,
            retry_count=0,
        )
        error_context = {"error": "LLM timeout", "failed_at_entity": 15}
        task.mark_failed(error_context)

        assert task.status == TaskStatus.FAILED.value
        assert task.failure_context == error_context
        assert task.retry_count == 1
        assert task.failed_at is not None


class TestSessionValidationModel:
    """Test SessionValidation model for ADF validation tracking."""

    def test_session_validation_has_required_fields(self):
        """SessionValidation must have all specified fields."""
        mapper = inspect(SessionValidation)
        columns = {c.key for c in mapper.columns}

        required_fields = {
            "session_id",
            "validation_status",
            "validation_passed",
            "last_validated_at",
            "last_invalidated_at",
            "validation_results",
        }
        assert required_fields.issubset(columns)

    def test_session_id_is_primary_key(self):
        """SessionValidation uses session_id as primary key."""
        mapper = inspect(SessionValidation)
        pk_columns = [c.key for c in mapper.primary_key]

        assert pk_columns == ["session_id"]

    def test_adf_validation_status_enum_values(self):
        """AdfValidationStatus enum must have expected values."""
        expected = {"pending", "processing", "completed", "failed"}
        actual = {e.value for e in AdfValidationStatus}

        assert expected == actual

    @pytest.mark.asyncio
    async def test_validation_passed_defaults_to_false(self, db_session, sample_session):
        """validation_passed should default to False."""
        validation = SessionValidation(session_id=sample_session.id)
        db_session.add(validation)
        await db_session.flush()

        assert validation.validation_passed is False

    def test_is_export_ready_when_passed(self):
        """is_export_ready is True when validation passed."""
        validation = SessionValidation(
            session_id=uuid4(),
            validation_status=AdfValidationStatus.COMPLETED.value,
            validation_passed=True,
        )
        assert validation.is_export_ready is True

    def test_is_not_export_ready_when_not_passed(self):
        """is_export_ready is False when validation not passed."""
        validation = SessionValidation(
            session_id=uuid4(),
            validation_status=AdfValidationStatus.COMPLETED.value,
            validation_passed=False,
        )
        assert validation.is_export_ready is False

    def test_is_not_export_ready_when_pending(self):
        """is_export_ready is False when validation is pending."""
        validation = SessionValidation(
            session_id=uuid4(),
            validation_status=AdfValidationStatus.PENDING.value,
            validation_passed=False,
        )
        assert validation.is_export_ready is False

    def test_mark_validation_completed_sets_passed_true(self):
        """mark_validation_completed sets passed flag correctly."""
        validation = SessionValidation(
            session_id=uuid4(),
            validation_status=AdfValidationStatus.PROCESSING.value,
        )
        validation.mark_validation_completed(passed=True, results={"count": 50})

        assert validation.validation_status == AdfValidationStatus.COMPLETED.value
        assert validation.validation_passed is True
        assert validation.last_validated_at is not None
        assert validation.validation_results == {"count": 50}

    def test_invalidate_validation_clears_passed(self):
        """invalidate_validation sets passed to False."""
        validation = SessionValidation(
            session_id=uuid4(),
            validation_status=AdfValidationStatus.COMPLETED.value,
            validation_passed=True,
            last_validated_at=datetime.utcnow(),
        )
        validation.invalidate_validation()

        assert validation.validation_passed is False
        assert validation.last_invalidated_at is not None
