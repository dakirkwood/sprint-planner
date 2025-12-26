"""Jira API client for OAuth and project operations."""

from datetime import datetime
from typing import Dict, List, Optional

import httpx

from app.integrations.jira.exceptions import (
    JiraAuthError,
    JiraAPIError,
    JiraProjectNotFoundError,
)
from app.schemas.auth import (
    ProjectContextData,
    ProjectPermissions,
    SprintOption,
    TeamMemberOption,
    UserInfo,
)


class JiraService:
    """Jira API client for OAuth and project operations."""

    ATLASSIAN_AUTH_URL = "https://auth.atlassian.com"
    ATLASSIAN_API_URL = "https://api.atlassian.com"

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        base_url: str = None,
    ):
        """Initialize Jira service.

        Args:
            client_id: OAuth client ID
            client_secret: OAuth client secret
            redirect_uri: OAuth redirect URI
            base_url: Optional custom base URL (for testing)
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.base_url = base_url or self.ATLASSIAN_API_URL
        self._http_client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()

    def get_authorization_url(self, state: str, code_challenge: str) -> str:
        """Generate OAuth authorization URL with PKCE.

        Args:
            state: CSRF state token
            code_challenge: PKCE code challenge

        Returns:
            Complete authorization URL
        """
        scopes = [
            "read:jira-work",
            "read:jira-user",
            "write:jira-work",
            "offline_access",
        ]
        params = {
            "audience": "api.atlassian.com",
            "client_id": self.client_id,
            "scope": " ".join(scopes),
            "redirect_uri": self.redirect_uri,
            "state": state,
            "response_type": "code",
            "prompt": "consent",
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{self.ATLASSIAN_AUTH_URL}/authorize?{query}"

    async def exchange_code_for_tokens(
        self,
        code: str,
        code_verifier: str,
    ) -> Dict[str, str]:
        """Exchange authorization code for tokens.

        Args:
            code: Authorization code from callback
            code_verifier: PKCE code verifier

        Returns:
            Dictionary with access_token, refresh_token, expires_in

        Raises:
            JiraAuthError: If token exchange fails
        """
        client = await self._get_client()

        try:
            response = await client.post(
                f"{self.ATLASSIAN_AUTH_URL}/oauth/token",
                data={
                    "grant_type": "authorization_code",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "redirect_uri": self.redirect_uri,
                    "code_verifier": code_verifier,
                },
            )

            if response.status_code != 200:
                error_data = response.json() if response.content else {}
                raise JiraAuthError(
                    message=error_data.get("error_description", "Token exchange failed"),
                    status_code=response.status_code,
                )

            data = response.json()
            return {
                "access_token": data["access_token"],
                "refresh_token": data["refresh_token"],
                "expires_in": data["expires_in"],
            }
        except httpx.RequestError as e:
            raise JiraAuthError(f"Network error during token exchange: {e}")

    async def refresh_access_token(self, refresh_token: str) -> Dict[str, str]:
        """Refresh expired access token.

        Args:
            refresh_token: Valid refresh token

        Returns:
            Dictionary with new access_token, refresh_token, expires_in

        Raises:
            JiraAuthError: If refresh fails
        """
        client = await self._get_client()

        try:
            response = await client.post(
                f"{self.ATLASSIAN_AUTH_URL}/oauth/token",
                data={
                    "grant_type": "refresh_token",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "refresh_token": refresh_token,
                },
            )

            if response.status_code != 200:
                error_data = response.json() if response.content else {}
                raise JiraAuthError(
                    message=error_data.get("error_description", "Token refresh failed"),
                    status_code=response.status_code,
                )

            data = response.json()
            return {
                "access_token": data["access_token"],
                "refresh_token": data["refresh_token"],
                "expires_in": data["expires_in"],
            }
        except httpx.RequestError as e:
            raise JiraAuthError(f"Network error during token refresh: {e}")

    async def get_user_info(self, access_token: str) -> UserInfo:
        """Get current user information from Jira.

        Args:
            access_token: Valid access token

        Returns:
            UserInfo with user details

        Raises:
            JiraAuthError: If token is invalid or expired
            JiraAPIError: If API request fails
        """
        client = await self._get_client()

        try:
            response = await client.get(
                f"{self.base_url}/me",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            if response.status_code == 401:
                raise JiraAuthError("Access token is invalid or expired", 401)

            if response.status_code != 200:
                raise JiraAPIError(
                    f"Failed to get user info: {response.status_code}",
                    response.status_code,
                )

            data = response.json()
            return UserInfo(
                jira_user_id=data.get("account_id", ""),
                display_name=data.get("name", data.get("displayName", "")),
                email=data.get("email", ""),
            )
        except httpx.RequestError as e:
            raise JiraAPIError(f"Network error getting user info: {e}")

    async def get_accessible_resources(
        self, access_token: str
    ) -> List[Dict[str, str]]:
        """Get accessible Jira cloud sites for the user.

        Args:
            access_token: Valid access token

        Returns:
            List of accessible resources with id, url, name

        Raises:
            JiraAuthError: If token is invalid
            JiraAPIError: If API request fails
        """
        client = await self._get_client()

        try:
            response = await client.get(
                f"{self.base_url}/oauth/token/accessible-resources",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            if response.status_code == 401:
                raise JiraAuthError("Access token is invalid or expired", 401)

            if response.status_code != 200:
                raise JiraAPIError(
                    f"Failed to get resources: {response.status_code}",
                    response.status_code,
                )

            return response.json()
        except httpx.RequestError as e:
            raise JiraAPIError(f"Network error getting resources: {e}")

    async def validate_project_access(
        self,
        project_key: str,
        access_token: str,
        cloud_id: str = None,
    ) -> bool:
        """Validate user has access to create issues in project.

        Args:
            project_key: Jira project key
            access_token: Valid access token
            cloud_id: Cloud instance ID (optional)

        Returns:
            True if user can create issues, False otherwise

        Raises:
            JiraAuthError: If token is invalid
        """
        client = await self._get_client()

        try:
            # Get cloud ID if not provided
            if not cloud_id:
                resources = await self.get_accessible_resources(access_token)
                if not resources:
                    return False
                cloud_id = resources[0]["id"]

            # Check project exists and user has access
            response = await client.get(
                f"{self.base_url}/ex/jira/{cloud_id}/rest/api/3/project/{project_key}",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            if response.status_code == 404:
                return False

            if response.status_code == 401:
                raise JiraAuthError("Access token is invalid or expired", 401)

            if response.status_code != 200:
                return False

            # Check CREATE_ISSUES permission
            permissions_response = await client.get(
                f"{self.base_url}/ex/jira/{cloud_id}/rest/api/3/mypermissions",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"projectKey": project_key, "permissions": "CREATE_ISSUES"},
            )

            if permissions_response.status_code != 200:
                return False

            perms = permissions_response.json()
            create_perm = perms.get("permissions", {}).get("CREATE_ISSUES", {})
            return create_perm.get("havePermission", False)

        except httpx.RequestError:
            return False

    async def get_project_metadata(
        self,
        project_key: str,
        access_token: str,
        cloud_id: str = None,
    ) -> ProjectContextData:
        """Get project metadata including sprints and team members.

        Args:
            project_key: Jira project key
            access_token: Valid access token
            cloud_id: Cloud instance ID (optional)

        Returns:
            ProjectContextData with project info

        Raises:
            JiraAuthError: If token is invalid
            JiraProjectNotFoundError: If project doesn't exist
            JiraAPIError: If API request fails
        """
        client = await self._get_client()

        try:
            # Get cloud ID if not provided
            if not cloud_id:
                resources = await self.get_accessible_resources(access_token)
                if not resources:
                    raise JiraAPIError("No accessible Jira sites found")
                cloud_id = resources[0]["id"]

            base_jira_url = f"{self.base_url}/ex/jira/{cloud_id}/rest/api/3"

            # Get project info
            project_response = await client.get(
                f"{base_jira_url}/project/{project_key}",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            if project_response.status_code == 404:
                raise JiraProjectNotFoundError(
                    f"Project {project_key} not found", 404
                )

            if project_response.status_code == 401:
                raise JiraAuthError("Access token is invalid or expired", 401)

            if project_response.status_code != 200:
                raise JiraAPIError(
                    f"Failed to get project: {project_response.status_code}",
                    project_response.status_code,
                )

            project_data = project_response.json()

            # Get permissions
            can_create = await self.validate_project_access(
                project_key, access_token, cloud_id
            )

            # Get sprints (if using Jira Software)
            sprints = await self._get_project_sprints(
                project_key, access_token, cloud_id, client
            )

            # Get team members (project assignable users)
            team_members = await self._get_project_users(
                project_key, access_token, cloud_id, client
            )

            return ProjectContextData(
                project_key=project_key,
                project_name=project_data.get("name", project_key),
                permissions=ProjectPermissions(
                    can_create_tickets=can_create,
                    can_assign_tickets=len(team_members) > 0,
                ),
                available_sprints=sprints,
                team_members=team_members,
                cached_at=datetime.utcnow(),
            )

        except (JiraAuthError, JiraProjectNotFoundError, JiraAPIError):
            raise
        except httpx.RequestError as e:
            raise JiraAPIError(f"Network error getting project metadata: {e}")

    async def _get_project_sprints(
        self,
        project_key: str,
        access_token: str,
        cloud_id: str,
        client: httpx.AsyncClient,
    ) -> List[SprintOption]:
        """Get sprints for project board."""
        try:
            # Get boards for project
            agile_url = f"{self.base_url}/ex/jira/{cloud_id}/rest/agile/1.0"

            boards_response = await client.get(
                f"{agile_url}/board",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"projectKeyOrId": project_key},
            )

            if boards_response.status_code != 200:
                return []

            boards = boards_response.json().get("values", [])
            if not boards:
                return []

            # Get sprints from first board
            board_id = boards[0]["id"]
            sprints_response = await client.get(
                f"{agile_url}/board/{board_id}/sprint",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"state": "active,future"},
            )

            if sprints_response.status_code != 200:
                return []

            sprints_data = sprints_response.json().get("values", [])
            return [
                SprintOption(
                    id=str(s["id"]),
                    name=s["name"],
                    state=s["state"],
                )
                for s in sprints_data
            ]
        except Exception:
            return []

    async def _get_project_users(
        self,
        project_key: str,
        access_token: str,
        cloud_id: str,
        client: httpx.AsyncClient,
    ) -> List[TeamMemberOption]:
        """Get assignable users for project."""
        try:
            base_jira_url = f"{self.base_url}/ex/jira/{cloud_id}/rest/api/3"

            response = await client.get(
                f"{base_jira_url}/user/assignable/search",
                headers={"Authorization": f"Bearer {access_token}"},
                params={"project": project_key, "maxResults": 100},
            )

            if response.status_code != 200:
                return []

            users_data = response.json()
            return [
                TeamMemberOption(
                    account_id=u["accountId"],
                    display_name=u.get("displayName", ""),
                    email=u.get("emailAddress"),
                    active=u.get("active", True),
                )
                for u in users_data
                if u.get("accountType") == "atlassian"
            ]
        except Exception:
            return []
