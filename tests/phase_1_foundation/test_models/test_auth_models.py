"""Tests for JiraAuthToken and JiraProjectContext models."""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from sqlalchemy import inspect

from app.models.auth import JiraAuthToken, JiraProjectContext


class TestJiraAuthTokenModel:
    """Test JiraAuthToken model field definitions."""

    def test_auth_token_has_required_fields(self):
        """JiraAuthToken must have all 7 specified fields."""
        mapper = inspect(JiraAuthToken)
        columns = {c.key for c in mapper.columns}

        required_fields = {
            "jira_user_id",
            "encrypted_access_token",
            "encrypted_refresh_token",
            "token_expires_at",
            "granted_scopes",
            "last_refresh_at",
            "created_at",
        }
        assert required_fields.issubset(columns)

    def test_jira_user_id_is_primary_key(self):
        """JiraAuthToken uses jira_user_id as primary key."""
        mapper = inspect(JiraAuthToken)
        pk_columns = [c.key for c in mapper.primary_key]

        assert pk_columns == ["jira_user_id"]

    def test_is_expired_when_past_expiration(self):
        """is_expired returns True when token is expired."""
        token = JiraAuthToken(
            jira_user_id="test-user",
            encrypted_access_token="token",
            encrypted_refresh_token="refresh",
            token_expires_at=datetime.utcnow() - timedelta(hours=1),
            granted_scopes=["read:jira-work"],
        )
        assert token.is_expired() is True

    def test_is_not_expired_when_before_expiration(self):
        """is_expired returns False when token is not expired."""
        token = JiraAuthToken(
            jira_user_id="test-user",
            encrypted_access_token="token",
            encrypted_refresh_token="refresh",
            token_expires_at=datetime.utcnow() + timedelta(hours=1),
            granted_scopes=["read:jira-work"],
        )
        assert token.is_expired() is False

    def test_needs_refresh_within_buffer(self):
        """needs_refresh returns True when within buffer time."""
        token = JiraAuthToken(
            jira_user_id="test-user",
            encrypted_access_token="token",
            encrypted_refresh_token="refresh",
            token_expires_at=datetime.utcnow() + timedelta(minutes=3),
            granted_scopes=["read:jira-work"],
        )
        # Default buffer is 5 minutes
        assert token.needs_refresh() is True

    def test_does_not_need_refresh_outside_buffer(self):
        """needs_refresh returns False when outside buffer time."""
        token = JiraAuthToken(
            jira_user_id="test-user",
            encrypted_access_token="token",
            encrypted_refresh_token="refresh",
            token_expires_at=datetime.utcnow() + timedelta(hours=1),
            granted_scopes=["read:jira-work"],
        )
        assert token.needs_refresh() is False

    def test_expires_in_minutes_when_valid(self):
        """expires_in_minutes returns correct value."""
        token = JiraAuthToken(
            jira_user_id="test-user",
            encrypted_access_token="token",
            encrypted_refresh_token="refresh",
            token_expires_at=datetime.utcnow() + timedelta(minutes=30),
            granted_scopes=["read:jira-work"],
        )
        # Should be approximately 30 (allow for test execution time)
        assert 29 <= token.expires_in_minutes <= 31

    def test_expires_in_minutes_none_when_expired(self):
        """expires_in_minutes returns None when expired."""
        token = JiraAuthToken(
            jira_user_id="test-user",
            encrypted_access_token="token",
            encrypted_refresh_token="refresh",
            token_expires_at=datetime.utcnow() - timedelta(hours=1),
            granted_scopes=["read:jira-work"],
        )
        assert token.expires_in_minutes is None


class TestJiraProjectContextModel:
    """Test JiraProjectContext model field definitions."""

    def test_project_context_has_required_fields(self):
        """JiraProjectContext must have all 8 specified fields."""
        mapper = inspect(JiraProjectContext)
        columns = {c.key for c in mapper.columns}

        required_fields = {
            "session_id",
            "project_key",
            "project_name",
            "can_create_tickets",
            "can_assign_tickets",
            "available_sprints",
            "team_members",
            "cached_at",
        }
        assert required_fields.issubset(columns)

    def test_session_id_is_primary_key(self):
        """JiraProjectContext uses session_id as primary key."""
        mapper = inspect(JiraProjectContext)
        pk_columns = [c.key for c in mapper.primary_key]

        assert pk_columns == ["session_id"]

    def test_is_stale_when_old(self):
        """is_stale returns True when cache is old."""
        context = JiraProjectContext(
            session_id=uuid4(),
            project_key="TEST",
            project_name="Test Project",
            available_sprints=[],
            team_members=[],
            cached_at=datetime.utcnow() - timedelta(hours=25),
        )
        assert context.is_stale(max_age_hours=24) is True

    def test_is_not_stale_when_fresh(self):
        """is_stale returns False when cache is fresh."""
        context = JiraProjectContext(
            session_id=uuid4(),
            project_key="TEST",
            project_name="Test Project",
            available_sprints=[],
            team_members=[],
            cached_at=datetime.utcnow(),
        )
        assert context.is_stale(max_age_hours=24) is False

    def test_get_active_sprints(self):
        """get_active_sprints filters by state."""
        context = JiraProjectContext(
            session_id=uuid4(),
            project_key="TEST",
            project_name="Test Project",
            available_sprints=[
                {"name": "Sprint 1", "state": "active"},
                {"name": "Sprint 2", "state": "future"},
                {"name": "Sprint 3", "state": "active"},
            ],
            team_members=[],
            cached_at=datetime.utcnow(),
        )
        active = context.get_active_sprints()

        assert len(active) == 2
        assert all(s["state"] == "active" for s in active)

    def test_get_team_member_by_id_found(self):
        """get_team_member_by_id returns member when found."""
        context = JiraProjectContext(
            session_id=uuid4(),
            project_key="TEST",
            project_name="Test Project",
            available_sprints=[],
            team_members=[
                {"account_id": "user-1", "display_name": "John Doe"},
                {"account_id": "user-2", "display_name": "Jane Smith"},
            ],
            cached_at=datetime.utcnow(),
        )
        member = context.get_team_member_by_id("user-1")

        assert member is not None
        assert member["display_name"] == "John Doe"

    def test_get_team_member_by_id_not_found(self):
        """get_team_member_by_id returns None when not found."""
        context = JiraProjectContext(
            session_id=uuid4(),
            project_key="TEST",
            project_name="Test Project",
            available_sprints=[],
            team_members=[],
            cached_at=datetime.utcnow(),
        )
        member = context.get_team_member_by_id("user-999")

        assert member is None

    def test_validate_sprint_name_valid(self):
        """validate_sprint_name returns True for valid sprint."""
        context = JiraProjectContext(
            session_id=uuid4(),
            project_key="TEST",
            project_name="Test Project",
            available_sprints=[
                {"name": "Sprint 1", "state": "active"},
            ],
            team_members=[],
            cached_at=datetime.utcnow(),
        )
        assert context.validate_sprint_name("Sprint 1") is True

    def test_validate_sprint_name_invalid(self):
        """validate_sprint_name returns False for invalid sprint."""
        context = JiraProjectContext(
            session_id=uuid4(),
            project_key="TEST",
            project_name="Test Project",
            available_sprints=[
                {"name": "Sprint 1", "state": "active"},
            ],
            team_members=[],
            cached_at=datetime.utcnow(),
        )
        assert context.validate_sprint_name("Sprint 99") is False

    def test_validate_assignee_id_valid(self):
        """validate_assignee_id returns True for valid assignee."""
        context = JiraProjectContext(
            session_id=uuid4(),
            project_key="TEST",
            project_name="Test Project",
            available_sprints=[],
            team_members=[{"account_id": "user-1", "display_name": "John Doe"}],
            cached_at=datetime.utcnow(),
        )
        assert context.validate_assignee_id("user-1") is True

    def test_validate_assignee_id_invalid(self):
        """validate_assignee_id returns False for invalid assignee."""
        context = JiraProjectContext(
            session_id=uuid4(),
            project_key="TEST",
            project_name="Test Project",
            available_sprints=[],
            team_members=[],
            cached_at=datetime.utcnow(),
        )
        assert context.validate_assignee_id("user-999") is False

    def test_has_active_sprints(self):
        """has_active_sprints returns True when active sprints exist."""
        context = JiraProjectContext(
            session_id=uuid4(),
            project_key="TEST",
            project_name="Test Project",
            available_sprints=[{"name": "Sprint 1", "state": "active"}],
            team_members=[],
            cached_at=datetime.utcnow(),
        )
        assert context.has_active_sprints is True

    def test_has_no_active_sprints(self):
        """has_active_sprints returns False when no active sprints."""
        context = JiraProjectContext(
            session_id=uuid4(),
            project_key="TEST",
            project_name="Test Project",
            available_sprints=[{"name": "Sprint 1", "state": "future"}],
            team_members=[],
            cached_at=datetime.utcnow(),
        )
        assert context.has_active_sprints is False

    def test_active_team_member_count(self):
        """active_team_member_count returns correct count."""
        context = JiraProjectContext(
            session_id=uuid4(),
            project_key="TEST",
            project_name="Test Project",
            available_sprints=[],
            team_members=[
                {"account_id": "user-1", "active": True},
                {"account_id": "user-2", "active": False},
                {"account_id": "user-3", "active": True},
            ],
            cached_at=datetime.utcnow(),
        )
        assert context.active_team_member_count == 2
