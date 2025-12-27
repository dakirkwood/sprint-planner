# tests/backend/unit/test_models/test_session_models.py
"""
Tests for Session, SessionTask, and SessionValidation models.
"""
import pytest
from datetime import datetime
from uuid import uuid4
from sqlalchemy import inspect

from app.models.session import Session, SessionTask, SessionValidation
from app.schemas.base import (
    SessionStage,
    SessionStatus,
    TaskType,
    TaskStatus,
    AdfValidationStatus
)


@pytest.mark.phase1
@pytest.mark.models
class TestSessionModel:
    """Test Session model field definitions and relationships."""

    def test_session_has_required_fields(self):
        """Session model must have all specified fields."""
        mapper = inspect(Session)
        columns = {c.key for c in mapper.columns}

        required_fields = {
            'id', 'jira_user_id', 'site_name', 'site_description',
            'llm_provider_choice', 'jira_project_key', 'current_stage',
            'status', 'created_at', 'updated_at'
        }
        assert required_fields.issubset(columns)

    @pytest.mark.asyncio
    async def test_session_default_stage_is_upload(self, db_session, sample_session_data):
        """New sessions should default to UPLOAD stage."""
        session = Session(**sample_session_data)
        db_session.add(session)
        await db_session.flush()

        assert session.current_stage == SessionStage.UPLOAD

    @pytest.mark.asyncio
    async def test_session_default_status_is_active(self, db_session, sample_session_data):
        """New sessions should default to ACTIVE status."""
        session = Session(**sample_session_data)
        db_session.add(session)
        await db_session.flush()

        assert session.status == SessionStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_session_generates_uuid_on_create(self, db_session, sample_session_data):
        """Session should auto-generate UUID primary key."""
        session = Session(**sample_session_data)
        db_session.add(session)
        await db_session.flush()

        assert session.id is not None

    @pytest.mark.asyncio
    async def test_session_sets_timestamps_on_create(self, db_session, sample_session_data):
        """Session should set created_at and updated_at on creation."""
        session = Session(**sample_session_data)
        db_session.add(session)
        await db_session.flush()

        assert session.created_at is not None
        assert session.updated_at is not None

    def test_session_has_relationship_to_session_task(self):
        """Session should have 1:1 relationship with SessionTask."""
        mapper = inspect(Session)
        relationships = {r.key for r in mapper.relationships}

        assert 'session_task' in relationships

    def test_session_has_relationship_to_session_validation(self):
        """Session should have 1:1 relationship with SessionValidation."""
        mapper = inspect(Session)
        relationships = {r.key for r in mapper.relationships}

        assert 'session_validation' in relationships

    def test_session_has_relationship_to_tickets(self):
        """Session should have 1:Many relationship with Tickets."""
        mapper = inspect(Session)
        relationships = {r.key for r in mapper.relationships}

        assert 'tickets' in relationships

    @pytest.mark.asyncio
    async def test_session_can_transition_to_valid_stage(self, db_session, sample_session_data):
        """Should allow valid stage transitions."""
        session = Session(**sample_session_data)
        db_session.add(session)
        await db_session.flush()

        # UPLOAD -> PROCESSING is valid
        assert session.can_transition_to(SessionStage.PROCESSING) is True

    @pytest.mark.asyncio
    async def test_session_cannot_skip_stages(self, db_session, sample_session_data):
        """Should not allow skipping stages."""
        session = Session(**sample_session_data)
        db_session.add(session)
        await db_session.flush()

        # UPLOAD -> JIRA_EXPORT is not valid (skips PROCESSING and REVIEW)
        assert session.can_transition_to(SessionStage.JIRA_EXPORT) is False

    @pytest.mark.asyncio
    async def test_session_stage_display_name(self, db_session, sample_session_data):
        """Should return human-readable stage names."""
        session = Session(**sample_session_data)
        db_session.add(session)
        await db_session.flush()
        assert session.stage_display_name == "File Upload"

    @pytest.mark.asyncio
    async def test_session_to_dict(self, db_session, sample_session_data):
        """Should serialize to dictionary."""
        session = Session(**sample_session_data)
        db_session.add(session)
        await db_session.flush()
        session_dict = session.to_dict()

        assert "id" in session_dict
        assert session_dict["site_name"] == sample_session_data["site_name"]
        assert session_dict["current_stage"] == SessionStage.UPLOAD.value


@pytest.mark.phase1
@pytest.mark.models
class TestSessionTaskModel:
    """Test SessionTask model for background task tracking."""

    def test_session_task_has_required_fields(self):
        """SessionTask must have all specified fields."""
        mapper = inspect(SessionTask)
        columns = {c.key for c in mapper.columns}

        required_fields = {
            'session_id', 'task_id', 'task_type', 'status',
            'started_at', 'completed_at', 'retry_count', 'failure_context'
        }
        assert required_fields.issubset(columns)

    def test_session_task_uses_session_id_as_primary_key(self):
        """SessionTask should use session_id as primary key (1:1)."""
        mapper = inspect(SessionTask)
        pk_columns = [c.key for c in mapper.primary_key]

        assert pk_columns == ['session_id']

    def test_task_type_enum_values(self):
        """TaskType enum must have expected values."""
        expected = {'processing', 'export', 'adf_validation'}
        actual = {e.value for e in TaskType}

        assert expected == actual

    def test_task_status_enum_values(self):
        """TaskStatus enum must have expected values."""
        expected = {'running', 'completed', 'failed', 'cancelled'}
        actual = {e.value for e in TaskStatus}

        assert expected == actual


@pytest.mark.phase1
@pytest.mark.models
class TestSessionValidationModel:
    """Test SessionValidation model for ADF validation tracking."""

    def test_session_validation_has_required_fields(self):
        """SessionValidation must have all specified fields."""
        mapper = inspect(SessionValidation)
        columns = {c.key for c in mapper.columns}

        required_fields = {
            'session_id', 'validation_status', 'validation_passed',
            'last_validated_at', 'last_invalidated_at', 'validation_results'
        }
        assert required_fields.issubset(columns)

    @pytest.mark.asyncio
    async def test_validation_passed_defaults_to_false(self, db_session, sample_session_data):
        """validation_passed should default to False."""
        session = Session(**sample_session_data)
        db_session.add(session)
        await db_session.flush()

        validation = SessionValidation(session_id=session.id)
        db_session.add(validation)
        await db_session.flush()

        assert validation.validation_passed is False

    def test_adf_validation_status_enum_values(self):
        """AdfValidationStatus enum must have expected values."""
        expected = {'pending', 'processing', 'completed', 'failed'}
        actual = {e.value for e in AdfValidationStatus}

        assert expected == actual
