"""Mock Jira API responses for testing."""

from datetime import datetime
from unittest.mock import AsyncMock

from app.schemas.auth import (
    ProjectContextData,
    ProjectPermissions,
    UserInfo,
)


def create_mock_jira_service() -> AsyncMock:
    """Create a mock JiraService for unit tests."""
    service = AsyncMock()

    # Default successful responses
    service.exchange_code_for_tokens.return_value = {
        "access_token": "test-access-token",
        "refresh_token": "test-refresh-token",
        "expires_in": 3600,
    }

    service.get_user_info.return_value = UserInfo(
        jira_user_id="user-123",
        display_name="Test User",
        email="test@example.com",
    )

    service.get_project_metadata.return_value = ProjectContextData(
        project_key="TEST",
        project_name="Test Project",
        permissions=ProjectPermissions(
            can_create_tickets=True,
            can_assign_tickets=True,
        ),
        available_sprints=[],
        team_members=[],
        cached_at=datetime.utcnow(),
    )

    service.validate_project_access.return_value = True

    service.get_authorization_url.return_value = (
        "https://auth.atlassian.com/authorize?client_id=test"
    )

    return service
