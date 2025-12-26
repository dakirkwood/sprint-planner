"""Tests for JiraService OAuth and API operations."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.integrations.jira.client import JiraService
from app.integrations.jira.exceptions import JiraAuthError, JiraAPIError


class TestJiraServiceOAuth:
    """Test OAuth token exchange."""

    @pytest.fixture
    def service(self):
        return JiraService(
            client_id="test-client-id",
            client_secret="test-client-secret",
            redirect_uri="http://localhost/callback",
        )

    def test_get_authorization_url(self, service):
        """Should generate proper authorization URL with PKCE."""
        url = service.get_authorization_url(
            state="test-state",
            code_challenge="test-challenge",
        )

        assert "auth.atlassian.com/authorize" in url
        assert "client_id=test-client-id" in url
        assert "state=test-state" in url
        assert "code_challenge=test-challenge" in url
        assert "code_challenge_method=S256" in url
        assert "response_type=code" in url

    @pytest.mark.asyncio
    async def test_exchange_code_for_tokens_success(self, service):
        """Should exchange auth code for tokens."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new-access-token",
            "refresh_token": "new-refresh-token",
            "expires_in": 3600,
        }

        with patch.object(service, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_get_client.return_value = mock_client

            result = await service.exchange_code_for_tokens(
                code="auth-code",
                code_verifier="verifier",
            )

            assert result["access_token"] == "new-access-token"
            assert result["refresh_token"] == "new-refresh-token"
            assert result["expires_in"] == 3600

    @pytest.mark.asyncio
    async def test_exchange_code_invalid_code_raises_error(self, service):
        """Should raise JiraAuthError for invalid auth code."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.content = b'{"error": "invalid_grant"}'
        mock_response.json.return_value = {"error": "invalid_grant"}

        with patch.object(service, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_get_client.return_value = mock_client

            with pytest.raises(JiraAuthError):
                await service.exchange_code_for_tokens(
                    code="invalid-code",
                    code_verifier="verifier",
                )

    @pytest.mark.asyncio
    async def test_refresh_token_success(self, service):
        """Should refresh expired access token."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "refreshed-access-token",
            "refresh_token": "new-refresh-token",
            "expires_in": 3600,
        }

        with patch.object(service, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_get_client.return_value = mock_client

            result = await service.refresh_access_token(
                refresh_token="old-refresh-token"
            )

            assert result["access_token"] == "refreshed-access-token"


class TestJiraServiceUserInfo:
    """Test user info retrieval."""

    @pytest.fixture
    def service(self):
        return JiraService(
            client_id="test-client-id",
            client_secret="test-client-secret",
            redirect_uri="http://localhost/callback",
        )

    @pytest.mark.asyncio
    async def test_get_user_info_success(self, service):
        """Should retrieve user info from Jira."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "account_id": "user-123",
            "name": "Test User",
            "email": "test@example.com",
        }

        with patch.object(service, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_get_client.return_value = mock_client

            user_info = await service.get_user_info(access_token="valid-token")

            assert user_info.jira_user_id == "user-123"
            assert user_info.display_name == "Test User"
            assert user_info.email == "test@example.com"

    @pytest.mark.asyncio
    async def test_get_user_info_expired_token(self, service):
        """Should raise JiraAuthError for expired token."""
        mock_response = MagicMock()
        mock_response.status_code = 401

        with patch.object(service, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_get_client.return_value = mock_client

            with pytest.raises(JiraAuthError):
                await service.get_user_info(access_token="expired-token")


class TestJiraServiceProjectValidation:
    """Test project access validation."""

    @pytest.fixture
    def service(self):
        return JiraService(
            client_id="test-client-id",
            client_secret="test-client-secret",
            redirect_uri="http://localhost/callback",
        )

    @pytest.mark.asyncio
    async def test_validate_project_access_success(self, service):
        """Should return True when user has project access."""
        # Mock responses for resources, project, and permissions
        resources_response = MagicMock()
        resources_response.status_code = 200
        resources_response.json.return_value = [{"id": "cloud-123", "name": "Test"}]

        project_response = MagicMock()
        project_response.status_code = 200
        project_response.json.return_value = {
            "key": "TEST",
            "name": "Test Project",
        }

        permissions_response = MagicMock()
        permissions_response.status_code = 200
        permissions_response.json.return_value = {
            "permissions": {
                "CREATE_ISSUES": {"havePermission": True}
            }
        }

        with patch.object(service, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get.side_effect = [
                resources_response,
                project_response,
                permissions_response,
            ]
            mock_get_client.return_value = mock_client

            result = await service.validate_project_access(
                project_key="TEST",
                access_token="valid-token",
            )

            assert result is True

    @pytest.mark.asyncio
    async def test_validate_project_not_found(self, service):
        """Should return False for non-existent project."""
        resources_response = MagicMock()
        resources_response.status_code = 200
        resources_response.json.return_value = [{"id": "cloud-123", "name": "Test"}]

        project_response = MagicMock()
        project_response.status_code = 404

        with patch.object(service, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get.side_effect = [resources_response, project_response]
            mock_get_client.return_value = mock_client

            result = await service.validate_project_access(
                project_key="NOTEXIST",
                access_token="valid-token",
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_validate_project_no_permission(self, service):
        """Should return False when user lacks create permission."""
        resources_response = MagicMock()
        resources_response.status_code = 200
        resources_response.json.return_value = [{"id": "cloud-123", "name": "Test"}]

        project_response = MagicMock()
        project_response.status_code = 200
        project_response.json.return_value = {"key": "TEST", "name": "Test Project"}

        permissions_response = MagicMock()
        permissions_response.status_code = 200
        permissions_response.json.return_value = {
            "permissions": {
                "CREATE_ISSUES": {"havePermission": False}
            }
        }

        with patch.object(service, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get.side_effect = [
                resources_response,
                project_response,
                permissions_response,
            ]
            mock_get_client.return_value = mock_client

            result = await service.validate_project_access(
                project_key="TEST",
                access_token="valid-token",
            )

            assert result is False
