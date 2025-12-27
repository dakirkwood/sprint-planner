# tests/backend/unit/test_repositories/test_auth_repository.py
"""
Tests for AuthRepository operations.
"""
import pytest
from datetime import datetime
from uuid import uuid4

from app.models.session import Session
from app.repositories.sqlalchemy.auth_repository import SQLAlchemyAuthRepository


@pytest.mark.phase1
@pytest.mark.repositories
class TestAuthRepositoryTokenManagement:
    """Test token management operations."""

    @pytest.fixture
    def repo(self, db_session):
        return SQLAlchemyAuthRepository(db_session)

    @pytest.mark.asyncio
    async def test_store_tokens(self, repo):
        """Should store tokens for a user."""
        await repo.store_tokens(
            jira_user_id="test-user",
            access_token="access_token_123",
            refresh_token="refresh_token_456",
            expires_in=3600,
            granted_scopes=["read:jira-work", "write:jira-work"]
        )

        token = await repo.get_tokens("test-user")

        assert token is not None
        assert token.jira_user_id == "test-user"
        assert token.granted_scopes == ["read:jira-work", "write:jira-work"]

    @pytest.mark.asyncio
    async def test_get_tokens_not_found(self, repo):
        """Should return None for non-existent user."""
        result = await repo.get_tokens("non-existent")

        assert result is None

    @pytest.mark.asyncio
    async def test_refresh_tokens(self, repo):
        """Should update tokens after refresh."""
        await repo.store_tokens(
            jira_user_id="test-user",
            access_token="old_access",
            refresh_token="old_refresh",
            expires_in=3600,
            granted_scopes=["read:jira-work"]
        )

        await repo.refresh_tokens(
            jira_user_id="test-user",
            new_access_token="new_access",
            new_refresh_token="new_refresh",
            expires_in=7200
        )

        token = await repo.get_tokens("test-user")
        assert token.access_token_encrypted == b"new_access"

    @pytest.mark.asyncio
    async def test_delete_tokens(self, repo):
        """Should delete tokens for a user."""
        await repo.store_tokens(
            jira_user_id="test-user",
            access_token="access",
            refresh_token="refresh",
            expires_in=3600,
            granted_scopes=[]
        )

        await repo.delete_tokens("test-user")

        assert await repo.get_tokens("test-user") is None

    @pytest.mark.asyncio
    async def test_token_needs_refresh(self, repo):
        """Should check if token needs refresh."""
        # Token that expires in 3 minutes (needs refresh with 5 min buffer)
        await repo.store_tokens(
            jira_user_id="test-user",
            access_token="access",
            refresh_token="refresh",
            expires_in=180,  # 3 minutes
            granted_scopes=[]
        )

        needs_refresh = await repo.token_needs_refresh("test-user", buffer_minutes=5)
        assert needs_refresh is True


@pytest.mark.phase1
@pytest.mark.repositories
class TestAuthRepositoryProjectContext:
    """Test project context management operations."""

    @pytest.fixture
    async def session_id(self, db_session, sample_session_data):
        session = Session(**sample_session_data)
        db_session.add(session)
        await db_session.flush()
        return session.id

    @pytest.fixture
    def repo(self, db_session):
        return SQLAlchemyAuthRepository(db_session)

    @pytest.mark.asyncio
    async def test_cache_project_context(self, repo, session_id):
        """Should cache project context for a session."""
        project_data = {
            "project_key": "TEST",
            "project_name": "Test Project",
            "active_sprints": [{"name": "Sprint 1", "id": "1"}],
            "team_members": [{"accountId": "user-1", "displayName": "User One"}]
        }

        context = await repo.cache_project_context(session_id, project_data)

        assert context is not None
        assert context.project_key == "TEST"
        assert len(context.active_sprints) == 1

    @pytest.mark.asyncio
    async def test_get_project_context(self, repo, session_id):
        """Should retrieve cached project context."""
        await repo.cache_project_context(session_id, {
            "project_key": "TEST",
            "project_name": "Test Project"
        })

        context = await repo.get_project_context(session_id)

        assert context is not None
        assert context.project_key == "TEST"

    @pytest.mark.asyncio
    async def test_validate_sprint_name(self, repo, session_id):
        """Should validate sprint name against cache."""
        await repo.cache_project_context(session_id, {
            "project_key": "TEST",
            "project_name": "Test Project",
            "active_sprints": [{"name": "Sprint 1"}, {"name": "Sprint 2"}]
        })

        assert await repo.validate_sprint_name(session_id, "Sprint 1") is True
        assert await repo.validate_sprint_name(session_id, "Sprint 3") is False

    @pytest.mark.asyncio
    async def test_validate_assignee_id(self, repo, session_id):
        """Should validate assignee against cache."""
        await repo.cache_project_context(session_id, {
            "project_key": "TEST",
            "project_name": "Test Project",
            "team_members": [{"accountId": "user-1"}, {"accountId": "user-2"}]
        })

        assert await repo.validate_assignee_id(session_id, "user-1") is True
        assert await repo.validate_assignee_id(session_id, "user-3") is False

    @pytest.mark.asyncio
    async def test_get_active_sprints(self, repo, session_id):
        """Should get active sprints from cache."""
        await repo.cache_project_context(session_id, {
            "project_key": "TEST",
            "project_name": "Test Project",
            "active_sprints": [{"name": "Sprint 1", "id": "1"}]
        })

        sprints = await repo.get_active_sprints(session_id)

        assert len(sprints) == 1
        assert sprints[0]["name"] == "Sprint 1"
