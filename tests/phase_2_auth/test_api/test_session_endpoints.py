"""Tests for session API endpoints."""

import pytest
from uuid import uuid4
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.api.dependencies.auth import get_current_user
from app.api.dependencies.services import get_session_service
from app.schemas.auth import (
    UserInfo,
    SessionResponse,
    SessionRecoveryResponse,
    CurrentSessionInfo,
    ProjectContextData,
    ProjectPermissions,
)
from app.schemas.base import SessionStage
from app.services.exceptions import SessionError, ResourceNotFoundError


@pytest.fixture
def mock_user():
    """Create a mock authenticated user."""
    return UserInfo(
        jira_user_id="user-123",
        display_name="Test User",
        email="test@example.com",
    )


@pytest.fixture
def mock_session_service():
    """Create a mock session service."""
    return AsyncMock()


class TestCreateSessionEndpoint:
    """Test POST /api/sessions."""

    @pytest.mark.asyncio
    async def test_create_session_requires_auth(self):
        """Should require authentication."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/sessions",
                json={
                    "site_name": "Test",
                    "jira_project_key": "TEST",
                },
            )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_session_success(self, mock_user, mock_session_service):
        """Should create session and return response."""
        session_id = uuid4()
        mock_session_service.create_session.return_value = SessionResponse(
            session_id=session_id,
            site_name="University Site",
            current_stage=SessionStage.UPLOAD,
            user_info=mock_user,
            project_context=ProjectContextData(
                project_key="UWEC",
                project_name="UW Eau Claire",
                permissions=ProjectPermissions(
                    can_create_tickets=True,
                    can_assign_tickets=True,
                ),
                available_sprints=[],
                team_members=[],
                cached_at=datetime.utcnow(),
            ),
        )

        async def mock_get_current_user():
            return (mock_user, "access-token")

        app.dependency_overrides[get_current_user] = mock_get_current_user
        app.dependency_overrides[get_session_service] = lambda: mock_session_service

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/sessions",
                json={
                    "site_name": "University Site",
                    "site_description": "Main campus",
                    "llm_provider_choice": "openai",
                    "jira_project_key": "UWEC",
                },
            )

        assert response.status_code == 201
        data = response.json()
        assert "session_id" in data
        assert data["site_name"] == "University Site"

        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_create_session_validates_request(self, mock_user):
        """Should validate request body."""
        async def mock_get_current_user():
            return (mock_user, "access-token")

        app.dependency_overrides[get_current_user] = mock_get_current_user

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/sessions",
                json={
                    "site_name": "",  # Empty - should fail
                    "jira_project_key": "TEST",
                },
            )

        assert response.status_code == 422

        app.dependency_overrides.clear()


class TestRecoverSessionEndpoint:
    """Test POST /api/sessions/{session_id}/recover."""

    @pytest.mark.asyncio
    async def test_recover_session_success(self, mock_user, mock_session_service):
        """Should recover existing session."""
        session_id = uuid4()
        mock_session_service.recover_session.return_value = SessionRecoveryResponse(
            session_id=session_id,
            restored_session=CurrentSessionInfo(
                session_id=session_id,
                stage=SessionStage.REVIEW,
                site_name="Test Site",
                created_at=datetime.utcnow(),
            ),
            tokens_applied=True,
            ready_to_continue=True,
        )

        async def mock_get_current_user():
            return (mock_user, "access-token")

        app.dependency_overrides[get_current_user] = mock_get_current_user
        app.dependency_overrides[get_session_service] = lambda: mock_session_service

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(f"/api/sessions/{session_id}/recover")

        assert response.status_code == 200
        data = response.json()
        assert data["ready_to_continue"] is True

        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_recover_session_not_found(self, mock_user, mock_session_service):
        """Should return 404 for non-existent session."""
        session_id = uuid4()
        mock_session_service.recover_session.side_effect = ResourceNotFoundError(
            "Session", str(session_id)
        )

        async def mock_get_current_user():
            return (mock_user, "access-token")

        app.dependency_overrides[get_current_user] = mock_get_current_user
        app.dependency_overrides[get_session_service] = lambda: mock_session_service

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(f"/api/sessions/{session_id}/recover")

        assert response.status_code == 404

        app.dependency_overrides.clear()


class TestGetIncompleteSessionsEndpoint:
    """Test GET /api/sessions/incomplete."""

    @pytest.mark.asyncio
    async def test_get_incomplete_sessions(self, mock_user, mock_session_service):
        """Should return list of incomplete sessions."""
        from app.schemas.auth import IncompleteSessionInfo

        mock_session_service.get_incomplete_sessions.return_value = [
            IncompleteSessionInfo(
                session_id=uuid4(),
                site_name="Site 1",
                stage=SessionStage.UPLOAD,
                created_at=datetime.utcnow(),
                tickets_generated=0,
                last_activity=datetime.utcnow(),
            ),
            IncompleteSessionInfo(
                session_id=uuid4(),
                site_name="Site 2",
                stage=SessionStage.REVIEW,
                created_at=datetime.utcnow(),
                tickets_generated=5,
                last_activity=datetime.utcnow(),
            ),
        ]

        async def mock_get_current_user():
            return (mock_user, "access-token")

        app.dependency_overrides[get_current_user] = mock_get_current_user
        app.dependency_overrides[get_session_service] = lambda: mock_session_service

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/sessions/incomplete")

        assert response.status_code == 200
        data = response.json()
        assert len(data["incomplete_sessions"]) == 2

        app.dependency_overrides.clear()
