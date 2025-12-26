"""Tests for auth repository Phase 2 operations."""

import pytest
import pytest_asyncio
from datetime import datetime
from uuid import uuid4

from app.repositories.sqlalchemy.auth_repository import SQLAlchemyAuthRepository
from app.core.security import decrypt_token


class TestAuthRepositoryTokenOperations:
    """Test token storage and retrieval."""

    @pytest_asyncio.fixture
    async def repo(self, db_session):
        """Create auth repository."""
        return SQLAlchemyAuthRepository(db_session)

    @pytest.mark.asyncio
    async def test_store_tokens_encrypts_tokens(self, repo, db_session):
        """Should store encrypted tokens."""
        await repo.store_tokens(
            jira_user_id="user-123",
            access_token="plain-access-token",
            refresh_token="plain-refresh-token",
            expires_in=3600,
            granted_scopes=["read:jira-work", "write:jira-work"],
        )

        # Retrieve and verify
        token_record = await repo.get_tokens("user-123")

        assert token_record is not None
        # Tokens should be encrypted (not plain text)
        assert token_record.encrypted_access_token != "plain-access-token"
        assert token_record.encrypted_refresh_token != "plain-refresh-token"
        # But should decrypt correctly
        assert token_record.decrypt_access_token() == "plain-access-token"
        assert token_record.decrypt_refresh_token() == "plain-refresh-token"

    @pytest.mark.asyncio
    async def test_store_tokens_updates_existing(self, repo):
        """Should update existing token record."""
        # Store initial tokens
        await repo.store_tokens(
            jira_user_id="user-123",
            access_token="access-token-1",
            refresh_token="refresh-token-1",
            expires_in=3600,
            granted_scopes=["read:jira-work"],
        )

        # Store new tokens for same user
        await repo.store_tokens(
            jira_user_id="user-123",
            access_token="access-token-2",
            refresh_token="refresh-token-2",
            expires_in=7200,
            granted_scopes=["read:jira-work", "write:jira-work"],
        )

        # Should have updated tokens
        token_record = await repo.get_tokens("user-123")
        assert token_record.decrypt_access_token() == "access-token-2"

    @pytest.mark.asyncio
    async def test_get_tokens_returns_none_for_unknown_user(self, repo):
        """Should return None for non-existent user."""
        token_record = await repo.get_tokens("unknown-user")
        assert token_record is None

    @pytest.mark.asyncio
    async def test_delete_tokens(self, repo):
        """Should delete tokens for user."""
        # Store tokens
        await repo.store_tokens(
            jira_user_id="user-123",
            access_token="access-token",
            refresh_token="refresh-token",
            expires_in=3600,
            granted_scopes=["read:jira-work"],
        )

        # Delete tokens
        await repo.delete_tokens("user-123")

        # Should be gone
        token_record = await repo.get_tokens("user-123")
        assert token_record is None

    @pytest.mark.asyncio
    async def test_token_needs_refresh(self, repo):
        """Should check if token needs refresh."""
        # Store token with short expiry
        await repo.store_tokens(
            jira_user_id="user-123",
            access_token="access-token",
            refresh_token="refresh-token",
            expires_in=60,  # 1 minute - within 5 min buffer
            granted_scopes=["read:jira-work"],
        )

        needs_refresh = await repo.token_needs_refresh("user-123")
        assert needs_refresh is True

    @pytest.mark.asyncio
    async def test_refresh_tokens(self, repo):
        """Should update tokens after refresh."""
        # Store initial tokens
        await repo.store_tokens(
            jira_user_id="user-123",
            access_token="old-access",
            refresh_token="old-refresh",
            expires_in=3600,
            granted_scopes=["read:jira-work"],
        )

        # Refresh tokens
        await repo.refresh_tokens(
            jira_user_id="user-123",
            new_access_token="new-access",
            new_refresh_token="new-refresh",
            expires_in=3600,
        )

        # Verify updated
        token_record = await repo.get_tokens("user-123")
        assert token_record.decrypt_access_token() == "new-access"
        assert token_record.decrypt_refresh_token() == "new-refresh"


class TestAuthRepositoryProjectContext:
    """Test project context caching."""

    @pytest_asyncio.fixture
    async def repo(self, db_session):
        """Create auth repository."""
        return SQLAlchemyAuthRepository(db_session)

    @pytest.mark.asyncio
    async def test_cache_project_context(self, repo, sample_session):
        """Should cache project context for session."""
        context = await repo.cache_project_context(
            session_id=sample_session.id,
            project_data={
                "project_key": "TEST",
                "project_name": "Test Project",
                "can_create_tickets": True,
                "can_assign_tickets": True,
                "available_sprints": [{"name": "Sprint 1", "state": "active"}],
                "team_members": [{"account_id": "user-1", "display_name": "User One"}],
            },
        )

        assert context is not None
        assert context.project_key == "TEST"
        assert context.project_name == "Test Project"

    @pytest.mark.asyncio
    async def test_get_project_context(self, repo, sample_session):
        """Should retrieve cached project context."""
        # Cache context
        await repo.cache_project_context(
            session_id=sample_session.id,
            project_data={
                "project_key": "TEST",
                "project_name": "Test Project",
                "can_create_tickets": True,
                "can_assign_tickets": False,
                "available_sprints": [],
                "team_members": [],
            },
        )

        # Retrieve
        context = await repo.get_project_context(sample_session.id)

        assert context is not None
        assert context.project_key == "TEST"
        assert context.can_create_tickets is True
        assert context.can_assign_tickets is False

    @pytest.mark.asyncio
    async def test_get_project_context_returns_none_for_unknown(self, repo):
        """Should return None for unknown session."""
        context = await repo.get_project_context(uuid4())
        assert context is None

    @pytest.mark.asyncio
    async def test_validate_sprint_name(self, repo, sample_session):
        """Should validate sprint name against cached data."""
        await repo.cache_project_context(
            session_id=sample_session.id,
            project_data={
                "project_key": "TEST",
                "project_name": "Test",
                "available_sprints": [
                    {"name": "Sprint 1", "state": "active"},
                    {"name": "Sprint 2", "state": "future"},
                ],
                "team_members": [],
            },
        )

        assert await repo.validate_sprint_name(sample_session.id, "Sprint 1") is True
        assert await repo.validate_sprint_name(sample_session.id, "Sprint 3") is False

    @pytest.mark.asyncio
    async def test_validate_assignee_id(self, repo, sample_session):
        """Should validate assignee ID against cached data."""
        await repo.cache_project_context(
            session_id=sample_session.id,
            project_data={
                "project_key": "TEST",
                "project_name": "Test",
                "available_sprints": [],
                "team_members": [
                    {"account_id": "user-1", "display_name": "User One", "active": True},
                    {"account_id": "user-2", "display_name": "User Two", "active": True},
                ],
            },
        )

        assert await repo.validate_assignee_id(sample_session.id, "user-1") is True
        assert await repo.validate_assignee_id(sample_session.id, "user-3") is False
