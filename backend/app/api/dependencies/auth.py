"""Authentication dependencies for API endpoints."""

from typing import Optional, Tuple
from datetime import datetime

from fastapi import Depends, HTTPException, status, Request, Cookie
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.database import get_db
from app.core.config import settings
from app.integrations.jira.client import JiraService
from app.integrations.jira.exceptions import JiraAuthError
from app.repositories.sqlalchemy.auth_repository import SQLAlchemyAuthRepository
from app.schemas.auth import UserInfo


# PKCE state storage (in production, use Redis)
_oauth_states: dict[str, dict] = {}


def store_oauth_state(state: str, code_verifier: str) -> None:
    """Store OAuth state and PKCE verifier."""
    _oauth_states[state] = {
        "code_verifier": code_verifier,
        "created_at": datetime.utcnow(),
    }


def get_oauth_state(state: str) -> Optional[str]:
    """Get and remove PKCE verifier for state."""
    data = _oauth_states.pop(state, None)
    if data:
        return data["code_verifier"]
    return None


def get_jira_service() -> JiraService:
    """Get JiraService singleton."""
    return JiraService(
        client_id=settings.JIRA_CLIENT_ID or "",
        client_secret=settings.JIRA_CLIENT_SECRET or "",
        redirect_uri=settings.JIRA_REDIRECT_URI or "",
    )


async def get_current_user(
    request: Request,
    session_token: Optional[str] = Cookie(default=None, alias="session"),
    db: AsyncSession = Depends(get_db),
    jira_service: JiraService = Depends(get_jira_service),
) -> Tuple[UserInfo, str]:
    """Get current authenticated user.

    Returns:
        Tuple of (UserInfo, access_token)

    Raises:
        HTTPException: If not authenticated or token expired
    """
    # Check for session token in cookie
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # The session_token is the jira_user_id for simplicity
    # In production, this would be a JWT or session ID
    jira_user_id = session_token

    # Get tokens from database
    auth_repo = SQLAlchemyAuthRepository(db)
    token_record = await auth_repo.get_tokens(jira_user_id)

    if not token_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired. Please log in again.",
        )

    # Check if token needs refresh
    if token_record.needs_refresh():
        try:
            refresh_token = token_record.decrypt_refresh_token()
            new_tokens = await jira_service.refresh_access_token(refresh_token)

            await auth_repo.refresh_tokens(
                jira_user_id=jira_user_id,
                new_access_token=new_tokens["access_token"],
                new_refresh_token=new_tokens["refresh_token"],
                expires_in=new_tokens["expires_in"],
            )

            access_token = new_tokens["access_token"]
        except JiraAuthError:
            # Refresh failed, user needs to re-authenticate
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session expired. Please log in again.",
            )
    else:
        access_token = token_record.decrypt_access_token()

    # Get user info
    try:
        user_info = await jira_service.get_user_info(access_token)
        return user_info, access_token
    except JiraAuthError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Failed to verify authentication",
        )


async def get_optional_user(
    request: Request,
    session_token: Optional[str] = Cookie(default=None, alias="session"),
    db: AsyncSession = Depends(get_db),
    jira_service: JiraService = Depends(get_jira_service),
) -> Optional[Tuple[UserInfo, str]]:
    """Get current user if authenticated, None otherwise."""
    if not session_token:
        return None

    try:
        return await get_current_user(request, session_token, db, jira_service)
    except HTTPException:
        return None
