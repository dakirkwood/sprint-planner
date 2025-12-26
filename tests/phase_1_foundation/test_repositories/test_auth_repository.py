"""Tests for SQLAlchemy auth repository."""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from app.repositories.sqlalchemy.auth_repository import SQLAlchemyAuthRepository
from app.models.auth import JiraAuthToken, JiraProjectContext


class TestAuthTokenMethods:
    """Test OAuth token methods."""

    @pytest.mark.asyncio
    async def test_store_tokens_new_user(self, db_session):
        """Store tokens for a new user."""
        repo = SQLAlchemyAuthRepository(db_session)

        await repo.store_tokens(
            jira_user_id="user-123",
            access_token="access_token_value",
            refresh_token="refresh_token_value",
            expires_in=3600,
            granted_scopes=["read:jira-work", "write:jira-work"],
        )

        token = await repo.get_tokens("user-123")
        assert token is not None
        assert token.jira_user_id == "user-123"
        assert token.granted_scopes == ["read:jira-work", "write:jira-work"]

    @pytest.mark.asyncio
    async def test_store_tokens_update_existing(self, db_session):
        """Store tokens updates existing record."""
        repo = SQLAlchemyAuthRepository(db_session)

        # Store initial tokens
        await repo.store_tokens(
            jira_user_id="user-456",
            access_token="old_access",
            refresh_token="old_refresh",
            expires_in=3600,
            granted_scopes=["read:jira-work"],
        )

        # Update with new tokens
        await repo.store_tokens(
            jira_user_id="user-456",
            access_token="new_access",
            refresh_token="new_refresh",
            expires_in=7200,
            granted_scopes=["read:jira-work", "write:jira-work"],
        )

        token = await repo.get_tokens("user-456")
        assert token.granted_scopes == ["read:jira-work", "write:jira-work"]

    @pytest.mark.asyncio
    async def test_get_tokens_not_found(self, db_session):
        """Get tokens for non-existent user."""
        repo = SQLAlchemyAuthRepository(db_session)

        result = await repo.get_tokens("non-existent")

        assert result is None

    @pytest.mark.asyncio
    async def test_refresh_tokens(self, db_session):
        """Refresh tokens for user."""
        repo = SQLAlchemyAuthRepository(db_session)

        # Store initial tokens
        await repo.store_tokens(
            jira_user_id="user-refresh",
            access_token="old_access",
            refresh_token="old_refresh",
            expires_in=3600,
            granted_scopes=["read:jira-work"],
        )

        # Refresh tokens
        await repo.refresh_tokens(
            jira_user_id="user-refresh",
            new_access_token="new_access",
            new_refresh_token="new_refresh",
            expires_in=7200,
        )

        token = await repo.get_tokens("user-refresh")
        assert token.last_refresh_at is not None

    @pytest.mark.asyncio
    async def test_delete_tokens(self, db_session):
        """Delete tokens for user."""
        repo = SQLAlchemyAuthRepository(db_session)

        await repo.store_tokens(
            jira_user_id="user-delete",
            access_token="access",
            refresh_token="refresh",
            expires_in=3600,
            granted_scopes=["read:jira-work"],
        )

        await repo.delete_tokens("user-delete")

        result = await repo.get_tokens("user-delete")
        assert result is None

    @pytest.mark.asyncio
    async def test_find_expiring_tokens(self, db_session):
        """Find tokens expiring soon."""
        repo = SQLAlchemyAuthRepository(db_session)

        # Create token expiring in 30 minutes
        token1 = JiraAuthToken(
            jira_user_id="user-expiring",
            encrypted_access_token="token",
            encrypted_refresh_token="refresh",
            token_expires_at=datetime.utcnow() + timedelta(minutes=30),
            granted_scopes=["read:jira-work"],
        )
        db_session.add(token1)

        # Create token not expiring soon
        token2 = JiraAuthToken(
            jira_user_id="user-not-expiring",
            encrypted_access_token="token",
            encrypted_refresh_token="refresh",
            token_expires_at=datetime.utcnow() + timedelta(hours=5),
            granted_scopes=["read:jira-work"],
        )
        db_session.add(token2)
        await db_session.flush()

        expiring = await repo.find_expiring_tokens(buffer_minutes=60)

        assert len(expiring) == 1
        assert expiring[0].jira_user_id == "user-expiring"

    @pytest.mark.asyncio
    async def test_token_needs_refresh(self, db_session):
        """Check if token needs refresh."""
        repo = SQLAlchemyAuthRepository(db_session)

        # Create token expiring in 3 minutes
        token = JiraAuthToken(
            jira_user_id="user-needs-refresh",
            encrypted_access_token="token",
            encrypted_refresh_token="refresh",
            token_expires_at=datetime.utcnow() + timedelta(minutes=3),
            granted_scopes=["read:jira-work"],
        )
        db_session.add(token)
        await db_session.flush()

        needs_refresh = await repo.token_needs_refresh("user-needs-refresh")

        assert needs_refresh is True

    @pytest.mark.asyncio
    async def test_token_does_not_need_refresh(self, db_session):
        """Token does not need refresh."""
        repo = SQLAlchemyAuthRepository(db_session)

        # Create token expiring in 1 hour
        token = JiraAuthToken(
            jira_user_id="user-fresh",
            encrypted_access_token="token",
            encrypted_refresh_token="refresh",
            token_expires_at=datetime.utcnow() + timedelta(hours=1),
            granted_scopes=["read:jira-work"],
        )
        db_session.add(token)
        await db_session.flush()

        needs_refresh = await repo.token_needs_refresh("user-fresh")

        assert needs_refresh is False

    @pytest.mark.asyncio
    async def test_cleanup_expired_tokens(self, db_session):
        """Cleanup expired tokens."""
        repo = SQLAlchemyAuthRepository(db_session)

        # Create old expired token
        old_token = JiraAuthToken(
            jira_user_id="user-old",
            encrypted_access_token="token",
            encrypted_refresh_token="refresh",
            token_expires_at=datetime.utcnow() - timedelta(days=60),
            granted_scopes=["read:jira-work"],
        )
        db_session.add(old_token)

        # Create recently expired token
        recent_token = JiraAuthToken(
            jira_user_id="user-recent",
            encrypted_access_token="token",
            encrypted_refresh_token="refresh",
            token_expires_at=datetime.utcnow() - timedelta(days=5),
            granted_scopes=["read:jira-work"],
        )
        db_session.add(recent_token)
        await db_session.flush()

        deleted = await repo.cleanup_expired_tokens(grace_period_days=30)

        assert deleted == 1


class TestProjectContextMethods:
    """Test project context caching methods."""

    @pytest.mark.asyncio
    async def test_cache_project_context(
        self, db_session, sample_session, sample_project_context_data
    ):
        """Cache project context for session."""
        repo = SQLAlchemyAuthRepository(db_session)

        context = await repo.cache_project_context(
            sample_session.id,
            sample_project_context_data,
        )

        assert context.session_id == sample_session.id
        assert context.project_key == "TEST"
        assert context.can_create_tickets is True

    @pytest.mark.asyncio
    async def test_cache_project_context_update_existing(
        self, db_session, sample_session, sample_project_context_data
    ):
        """Update existing project context."""
        repo = SQLAlchemyAuthRepository(db_session)

        # Cache initial context
        await repo.cache_project_context(
            sample_session.id,
            sample_project_context_data,
        )

        # Update with new data
        updated_data = {**sample_project_context_data, "project_name": "Updated Name"}
        await repo.cache_project_context(sample_session.id, updated_data)

        context = await repo.get_project_context(sample_session.id)
        assert context.project_name == "Updated Name"

    @pytest.mark.asyncio
    async def test_get_project_context(
        self, db_session, sample_session, sample_project_context_data
    ):
        """Get project context for session."""
        repo = SQLAlchemyAuthRepository(db_session)

        await repo.cache_project_context(
            sample_session.id,
            sample_project_context_data,
        )

        result = await repo.get_project_context(sample_session.id)

        assert result is not None
        assert result.project_key == "TEST"

    @pytest.mark.asyncio
    async def test_get_project_context_not_found(self, db_session):
        """Get project context for non-existent session."""
        repo = SQLAlchemyAuthRepository(db_session)

        result = await repo.get_project_context(uuid4())

        assert result is None

    @pytest.mark.asyncio
    async def test_is_project_context_stale(
        self, db_session, sample_session, sample_project_context_data
    ):
        """Check if project context is stale."""
        repo = SQLAlchemyAuthRepository(db_session)

        # Create stale context
        context = JiraProjectContext(
            session_id=sample_session.id,
            project_key="TEST",
            project_name="Test",
            available_sprints=[],
            team_members=[],
            cached_at=datetime.utcnow() - timedelta(hours=30),
        )
        db_session.add(context)
        await db_session.flush()

        is_stale = await repo.is_project_context_stale(sample_session.id, max_age_hours=24)

        assert is_stale is True

    @pytest.mark.asyncio
    async def test_is_project_context_not_stale(
        self, db_session, sample_session, sample_project_context_data
    ):
        """Project context is not stale."""
        repo = SQLAlchemyAuthRepository(db_session)

        await repo.cache_project_context(
            sample_session.id,
            sample_project_context_data,
        )

        is_stale = await repo.is_project_context_stale(sample_session.id, max_age_hours=24)

        assert is_stale is False

    @pytest.mark.asyncio
    async def test_validate_sprint_name(
        self, db_session, sample_session, sample_project_context_data
    ):
        """Validate sprint name."""
        repo = SQLAlchemyAuthRepository(db_session)

        await repo.cache_project_context(
            sample_session.id,
            sample_project_context_data,
        )

        valid = await repo.validate_sprint_name(sample_session.id, "Sprint 1")
        invalid = await repo.validate_sprint_name(sample_session.id, "Sprint 99")

        assert valid is True
        assert invalid is False

    @pytest.mark.asyncio
    async def test_validate_assignee_id(
        self, db_session, sample_session, sample_project_context_data
    ):
        """Validate assignee ID."""
        repo = SQLAlchemyAuthRepository(db_session)

        await repo.cache_project_context(
            sample_session.id,
            sample_project_context_data,
        )

        valid = await repo.validate_assignee_id(sample_session.id, "user-1")
        invalid = await repo.validate_assignee_id(sample_session.id, "user-999")

        assert valid is True
        assert invalid is False

    @pytest.mark.asyncio
    async def test_get_active_sprints(
        self, db_session, sample_session, sample_project_context_data
    ):
        """Get active sprints from cached data."""
        repo = SQLAlchemyAuthRepository(db_session)

        await repo.cache_project_context(
            sample_session.id,
            sample_project_context_data,
        )

        sprints = await repo.get_active_sprints(sample_session.id)

        assert len(sprints) == 1
        assert sprints[0]["name"] == "Sprint 1"

    @pytest.mark.asyncio
    async def test_get_team_members(
        self, db_session, sample_session, sample_project_context_data
    ):
        """Get team members from cached data."""
        repo = SQLAlchemyAuthRepository(db_session)

        await repo.cache_project_context(
            sample_session.id,
            sample_project_context_data,
        )

        members = await repo.get_team_members(sample_session.id)

        assert len(members) == 2
