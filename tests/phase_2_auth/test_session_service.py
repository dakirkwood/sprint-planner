"""Tests for SessionService."""

import pytest
from datetime import datetime
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

from app.services.session_service import SessionService
from app.services.exceptions import SessionError, ResourceNotFoundError
from app.schemas.auth import (
    SessionCreateRequest,
    UserInfo,
    ProjectContextData,
    ProjectPermissions,
)
from app.schemas.base import SessionStage


@pytest.fixture
def mock_jira_service():
    """Mock JiraService for unit tests."""
    service = AsyncMock()
    service.validate_project_access.return_value = True
    service.get_project_metadata.return_value = ProjectContextData(
        project_key="TEST",
        project_name="Test Project",
        permissions=ProjectPermissions(can_create_tickets=True, can_assign_tickets=True),
        available_sprints=[],
        team_members=[],
        cached_at=datetime.utcnow(),
    )
    return service


@pytest.fixture
def mock_auth_repository():
    """Mock AuthRepository for unit tests."""
    repo = AsyncMock()
    repo.cache_project_context.return_value = None
    repo.get_project_context.return_value = None
    return repo


@pytest.fixture
def mock_session_repository():
    """Mock SessionRepository for unit tests."""
    repo = AsyncMock()
    session_mock = MagicMock()
    session_mock.id = uuid4()
    session_mock.site_name = "Test Site"
    session_mock.current_stage = SessionStage.UPLOAD.value
    session_mock.jira_user_id = "user-123"
    session_mock.created_at = datetime.utcnow()
    session_mock.updated_at = datetime.utcnow()
    session_mock.total_tickets_generated = 0
    session_mock.is_recoverable = True

    repo.create_session.return_value = session_mock
    repo.get_session_by_id.return_value = session_mock
    return repo


@pytest.fixture
def sample_create_session_request():
    """Valid session creation request."""
    return SessionCreateRequest(
        site_name="University of Wisconsin",
        site_description="Main campus Drupal site",
        llm_provider_choice="openai",
        jira_project_key="UWEC",
    )


@pytest.fixture
def sample_user_info():
    """Sample user info."""
    return UserInfo(
        jira_user_id="user-123",
        display_name="Test User",
        email="test@example.com",
    )


class TestSessionServiceCreation:
    """Test session creation flow."""

    @pytest.fixture
    def service(self, mock_session_repository, mock_auth_repository, mock_jira_service):
        return SessionService(
            session_repo=mock_session_repository,
            auth_repo=mock_auth_repository,
            jira_service=mock_jira_service,
        )

    @pytest.mark.asyncio
    async def test_create_session_validates_project_access(
        self, service, mock_jira_service, sample_create_session_request, sample_user_info
    ):
        """Should validate Jira project access before creating session."""
        await service.create_session(
            request=sample_create_session_request,
            user_id="user-123",
            access_token="valid-token",
            user_info=sample_user_info,
        )

        mock_jira_service.validate_project_access.assert_called_once_with(
            project_key="UWEC",
            access_token="valid-token",
        )

    @pytest.mark.asyncio
    async def test_create_session_caches_project_context(
        self, service, mock_auth_repository, mock_jira_service,
        sample_create_session_request, sample_user_info
    ):
        """Should cache project metadata for dropdowns."""
        await service.create_session(
            request=sample_create_session_request,
            user_id="user-123",
            access_token="valid-token",
            user_info=sample_user_info,
        )

        mock_jira_service.get_project_metadata.assert_called_once()
        mock_auth_repository.cache_project_context.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_session_returns_session_response(
        self, service, sample_create_session_request, sample_user_info
    ):
        """Should return SessionResponse with all required fields."""
        response = await service.create_session(
            request=sample_create_session_request,
            user_id="user-123",
            access_token="valid-token",
            user_info=sample_user_info,
        )

        assert response.session_id is not None
        assert response.site_name == sample_create_session_request.site_name
        assert response.current_stage == SessionStage.UPLOAD
        assert response.user_info is not None
        assert response.project_context is not None

    @pytest.mark.asyncio
    async def test_create_session_fails_without_project_access(
        self, service, mock_jira_service, sample_create_session_request, sample_user_info
    ):
        """Should raise error if user lacks project access."""
        mock_jira_service.validate_project_access.return_value = False

        with pytest.raises(SessionError) as exc_info:
            await service.create_session(
                request=sample_create_session_request,
                user_id="user-123",
                access_token="valid-token",
                user_info=sample_user_info,
            )

        assert exc_info.value.category == "user_fixable"
        assert "access" in exc_info.value.message.lower()


class TestSessionServiceRecovery:
    """Test session recovery flow."""

    @pytest.fixture
    def service(self, mock_session_repository, mock_auth_repository, mock_jira_service):
        return SessionService(
            session_repo=mock_session_repository,
            auth_repo=mock_auth_repository,
            jira_service=mock_jira_service,
        )

    @pytest.mark.asyncio
    async def test_recover_session_returns_session_state(
        self, service, mock_session_repository
    ):
        """Should return current session state for recovery."""
        session_id = uuid4()
        mock_session = MagicMock()
        mock_session.id = session_id
        mock_session.site_name = "Recovered Site"
        mock_session.current_stage = SessionStage.REVIEW.value
        mock_session.jira_user_id = "user-123"
        mock_session.created_at = datetime.utcnow()
        mock_session.is_recoverable = True

        mock_session_repository.get_session_by_id.return_value = mock_session

        response = await service.recover_session(session_id, user_id="user-123")

        assert response.session_id == session_id
        assert response.ready_to_continue is True

    @pytest.mark.asyncio
    async def test_recover_session_validates_ownership(
        self, service, mock_session_repository
    ):
        """Should reject recovery if user doesn't own session."""
        session_id = uuid4()
        mock_session = MagicMock()
        mock_session.id = session_id
        mock_session.jira_user_id = "different-user"

        mock_session_repository.get_session_by_id.return_value = mock_session

        with pytest.raises(SessionError) as exc_info:
            await service.recover_session(session_id, user_id="user-123")

        assert exc_info.value.category == "user_fixable"

    @pytest.mark.asyncio
    async def test_recover_session_not_found(self, service, mock_session_repository):
        """Should raise error for non-existent session."""
        mock_session_repository.get_session_by_id.return_value = None

        with pytest.raises(ResourceNotFoundError) as exc_info:
            await service.recover_session(uuid4(), user_id="user-123")

        assert "not found" in exc_info.value.message.lower()


class TestSessionServiceIncompleteSessionQuery:
    """Test querying incomplete sessions for user."""

    @pytest.fixture
    def service(self, mock_session_repository, mock_auth_repository, mock_jira_service):
        return SessionService(
            session_repo=mock_session_repository,
            auth_repo=mock_auth_repository,
            jira_service=mock_jira_service,
        )

    @pytest.mark.asyncio
    async def test_get_incomplete_sessions(self, service, mock_session_repository):
        """Should return list of user's incomplete sessions."""
        session1 = MagicMock()
        session1.id = uuid4()
        session1.site_name = "Site 1"
        session1.current_stage = SessionStage.UPLOAD.value
        session1.created_at = datetime.utcnow()
        session1.updated_at = datetime.utcnow()
        session1.total_tickets_generated = 0

        session2 = MagicMock()
        session2.id = uuid4()
        session2.site_name = "Site 2"
        session2.current_stage = SessionStage.REVIEW.value
        session2.created_at = datetime.utcnow()
        session2.updated_at = datetime.utcnow()
        session2.total_tickets_generated = 5

        mock_session_repository.find_incomplete_sessions_by_user.return_value = [
            session1,
            session2,
        ]

        sessions = await service.get_incomplete_sessions(user_id="user-123")

        assert len(sessions) == 2
        mock_session_repository.find_incomplete_sessions_by_user.assert_called_with(
            "user-123"
        )
