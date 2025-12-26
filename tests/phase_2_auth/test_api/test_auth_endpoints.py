"""Tests for auth API endpoints."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.api.dependencies.auth import get_jira_service, get_optional_user
from app.api.dependencies.database import get_db


async def mock_get_db():
    """Mock database dependency."""
    mock_session = AsyncMock()
    # Mock execute to return empty results for queries
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_result
    yield mock_session


class TestLoginEndpoint:
    """Test GET /api/auth/login."""

    @pytest.fixture(autouse=True)
    def setup_mocks(self):
        """Setup mocks before each test."""
        # Use MagicMock for sync methods, AsyncMock for async methods
        mock_service = MagicMock()
        mock_service.get_authorization_url.return_value = (
            "https://auth.atlassian.com/authorize?client_id=test&code_challenge=abc123"
        )
        app.dependency_overrides[get_jira_service] = lambda: mock_service
        app.dependency_overrides[get_db] = mock_get_db
        yield
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_login_returns_redirect_url(self):
        """Should return OAuth authorization URL."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/auth/login")

        assert response.status_code == 200
        data = response.json()
        assert "redirect_url" in data
        assert "state" in data
        assert "atlassian.com" in data["redirect_url"]

    @pytest.mark.asyncio
    async def test_login_includes_pkce_challenge(self):
        """Should include PKCE code_challenge in redirect URL."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/auth/login")

        data = response.json()
        assert "code_challenge" in data["redirect_url"]


class TestCallbackEndpoint:
    """Test GET /api/auth/callback."""

    @pytest.fixture(autouse=True)
    def setup_mocks(self):
        """Setup mocks before each test."""
        app.dependency_overrides[get_db] = mock_get_db
        yield
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_callback_missing_code_returns_error(self):
        """Should return error when code is missing."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/auth/callback",
                params={"state": "valid-state"},  # Missing 'code'
            )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_callback_invalid_state_returns_error(self):
        """Should reject invalid CSRF state."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/auth/callback",
                params={"code": "auth-code", "state": "invalid-csrf-state"},
            )

        assert response.status_code == 400


class TestAuthStatusEndpoint:
    """Test GET /api/auth/status."""

    @pytest.fixture(autouse=True)
    def setup_mocks(self):
        """Setup mocks before each test."""
        app.dependency_overrides[get_db] = mock_get_db
        yield
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_status_unauthenticated(self):
        """Should return unauthenticated status when no token."""
        # Override to return None (unauthenticated)
        async def mock_optional_user():
            return None

        app.dependency_overrides[get_optional_user] = mock_optional_user

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/auth/status")

        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is False

    @pytest.mark.asyncio
    async def test_status_authenticated_with_user_info(self):
        """Should return user info when authenticated."""
        from app.schemas.auth import UserInfo

        mock_user = UserInfo(
            jira_user_id="user-123",
            display_name="Test User",
            email="test@example.com",
        )

        async def mock_optional_user():
            return (mock_user, "access-token")

        app.dependency_overrides[get_optional_user] = mock_optional_user

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/auth/status")

        assert response.status_code == 200
        data = response.json()
        assert data["authenticated"] is True
        assert data["user_info"]["display_name"] == "Test User"


class TestLogoutEndpoint:
    """Test POST /api/auth/logout."""

    @pytest.fixture(autouse=True)
    def setup_mocks(self):
        """Setup mocks before each test."""
        app.dependency_overrides[get_db] = mock_get_db
        yield
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_logout_requires_auth(self):
        """Should require authentication."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/auth/logout")

        assert response.status_code == 401
