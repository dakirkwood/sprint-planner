# tests/backend/unit/test_models/test_auth_models.py
"""
Tests for JiraAuthToken and JiraProjectContext models.
"""
import pytest
from datetime import datetime, timedelta
from sqlalchemy import inspect

from app.models.auth import JiraAuthToken, JiraProjectContext
from app.models.session import Session


@pytest.mark.phase1
@pytest.mark.models
class TestJiraAuthTokenModel:
    """Test JiraAuthToken model field definitions."""

    def test_jira_auth_token_has_required_fields(self):
        """JiraAuthToken must have all specified fields."""
        mapper = inspect(JiraAuthToken)
        columns = {c.key for c in mapper.columns}

        required_fields = {
            'jira_user_id', 'access_token_encrypted', 'refresh_token_encrypted',
            'expires_at', 'granted_scopes', 'created_at', 'updated_at'
        }
        assert required_fields.issubset(columns)

    def test_jira_auth_token_primary_key(self):
        """JiraAuthToken should use jira_user_id as primary key."""
        mapper = inspect(JiraAuthToken)
        pk_columns = [c.key for c in mapper.primary_key]

        assert pk_columns == ['jira_user_id']

    @pytest.mark.asyncio
    async def test_jira_auth_token_is_expired(self, db_session, sample_auth_token_data):
        """is_expired should return correct value based on expires_at."""
        # Create token that expires in the future
        token = JiraAuthToken(
            **sample_auth_token_data,
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
        db_session.add(token)
        await db_session.flush()

        assert token.is_expired() is False

        # Update to expired
        token.expires_at = datetime.utcnow() - timedelta(hours=1)
        assert token.is_expired() is True

    @pytest.mark.asyncio
    async def test_jira_auth_token_needs_refresh(self, db_session, sample_auth_token_data):
        """needs_refresh should return True when close to expiry."""
        # Token that expires in 3 minutes
        token = JiraAuthToken(
            **sample_auth_token_data,
            expires_at=datetime.utcnow() + timedelta(minutes=3)
        )
        db_session.add(token)
        await db_session.flush()

        # Default buffer is 5 minutes, so should need refresh
        assert token.needs_refresh() is True

        # Token that expires in 10 minutes
        token.expires_at = datetime.utcnow() + timedelta(minutes=10)
        assert token.needs_refresh() is False

    @pytest.mark.asyncio
    async def test_jira_auth_token_to_dict(self, db_session, sample_auth_token_data):
        """to_dict should not expose actual tokens."""
        token = JiraAuthToken(
            **sample_auth_token_data,
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
        db_session.add(token)
        await db_session.flush()

        token_dict = token.to_dict()

        assert "jira_user_id" in token_dict
        assert "access_token_encrypted" not in token_dict
        assert "refresh_token_encrypted" not in token_dict
        assert "is_expired" in token_dict


@pytest.mark.phase1
@pytest.mark.models
class TestJiraProjectContextModel:
    """Test JiraProjectContext model field definitions."""

    def test_jira_project_context_has_required_fields(self):
        """JiraProjectContext must have all specified fields."""
        mapper = inspect(JiraProjectContext)
        columns = {c.key for c in mapper.columns}

        required_fields = {
            'id', 'session_id', 'project_key', 'project_name',
            'active_sprints', 'team_members', 'issue_types', 'fetched_at',
            'created_at', 'updated_at'
        }
        assert required_fields.issubset(columns)

    @pytest.mark.asyncio
    async def test_jira_project_context_is_stale(self, db_session, sample_session_data):
        """is_stale should return correct value based on fetched_at."""
        session = Session(**sample_session_data)
        db_session.add(session)
        await db_session.flush()

        context = JiraProjectContext(
            session_id=session.id,
            project_key="TEST",
            project_name="Test Project",
            fetched_at=datetime.utcnow()
        )
        db_session.add(context)
        await db_session.flush()

        # Fresh context should not be stale
        assert context.is_stale() is False

        # 25 hours old should be stale (default max_age_hours=24)
        context.fetched_at = datetime.utcnow() - timedelta(hours=25)
        assert context.is_stale() is True

    @pytest.mark.asyncio
    async def test_jira_project_context_validate_sprint(self, db_session, sample_session_data):
        """validate_sprint should check against cached sprints."""
        session = Session(**sample_session_data)
        db_session.add(session)
        await db_session.flush()

        context = JiraProjectContext(
            session_id=session.id,
            project_key="TEST",
            project_name="Test Project",
            fetched_at=datetime.utcnow(),
            active_sprints=[
                {"name": "Sprint 1", "id": "1"},
                {"name": "Sprint 2", "id": "2"}
            ]
        )
        db_session.add(context)
        await db_session.flush()

        assert context.validate_sprint("Sprint 1") is True
        assert context.validate_sprint("Sprint 3") is False

    @pytest.mark.asyncio
    async def test_jira_project_context_validate_assignee(self, db_session, sample_session_data):
        """validate_assignee should check against cached team members."""
        session = Session(**sample_session_data)
        db_session.add(session)
        await db_session.flush()

        context = JiraProjectContext(
            session_id=session.id,
            project_key="TEST",
            project_name="Test Project",
            fetched_at=datetime.utcnow(),
            team_members=[
                {"accountId": "user-1", "displayName": "User One"},
                {"accountId": "user-2", "displayName": "User Two"}
            ]
        )
        db_session.add(context)
        await db_session.flush()

        assert context.validate_assignee("user-1") is True
        assert context.validate_assignee("user-3") is False
