"""Authentication API endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import (
    get_current_user,
    get_jira_service,
    get_optional_user,
    get_oauth_state,
    store_oauth_state,
)
from app.api.dependencies.database import get_db
from app.core.security import generate_csrf_state, generate_pkce_pair
from app.integrations.jira.client import JiraService
from app.integrations.jira.exceptions import JiraAuthError
from app.repositories.sqlalchemy.auth_repository import SQLAlchemyAuthRepository
from app.schemas.auth import (
    AuthStatusResponse,
    LoginRedirectResponse,
    UserInfo,
)


router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/login", response_model=LoginRedirectResponse)
async def login(
    jira_service: JiraService = Depends(get_jira_service),
) -> LoginRedirectResponse:
    """Initiate OAuth login flow.

    Returns redirect URL for Atlassian OAuth with PKCE.
    """
    # Generate PKCE pair
    code_verifier, code_challenge = generate_pkce_pair()

    # Generate CSRF state
    state = generate_csrf_state()

    # Store state and verifier for callback
    store_oauth_state(state, code_verifier)

    # Generate authorization URL
    redirect_url = jira_service.get_authorization_url(
        state=state,
        code_challenge=code_challenge,
    )

    return LoginRedirectResponse(
        redirect_url=redirect_url,
        state=state,
    )


@router.get("/callback")
async def oauth_callback(
    response: Response,
    code: str = Query(..., description="Authorization code from Jira"),
    state: str = Query(..., description="CSRF state token"),
    db: AsyncSession = Depends(get_db),
    jira_service: JiraService = Depends(get_jira_service),
) -> dict:
    """Handle OAuth callback from Jira.

    Exchanges authorization code for tokens and creates session.
    """
    # Validate state and get verifier
    code_verifier = get_oauth_state(state)
    if not code_verifier:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired state token",
        )

    try:
        # Exchange code for tokens
        tokens = await jira_service.exchange_code_for_tokens(
            code=code,
            code_verifier=code_verifier,
        )

        # Get user info
        user_info = await jira_service.get_user_info(tokens["access_token"])

        # Store tokens in database
        auth_repo = SQLAlchemyAuthRepository(db)
        await auth_repo.store_tokens(
            jira_user_id=user_info.jira_user_id,
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            expires_in=tokens["expires_in"],
            granted_scopes=[
                "read:jira-work",
                "read:jira-user",
                "write:jira-work",
                "offline_access",
            ],
        )

        # Set session cookie
        response.set_cookie(
            key="session",
            value=user_info.jira_user_id,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=60 * 60 * 24 * 7,  # 7 days
        )

        return {
            "success": True,
            "user": {
                "jira_user_id": user_info.jira_user_id,
                "display_name": user_info.display_name,
                "email": user_info.email,
            },
        }

    except JiraAuthError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth authentication failed: {e.message}",
        )


@router.get("/status", response_model=AuthStatusResponse)
async def get_auth_status(
    user_data: Optional[tuple] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
) -> AuthStatusResponse:
    """Get current authentication status.

    Returns user info if authenticated, or unauthenticated status.
    """
    if not user_data:
        return AuthStatusResponse(authenticated=False)

    user_info, access_token = user_data

    # Get incomplete sessions
    from app.repositories.sqlalchemy.session_repository import SQLAlchemySessionRepository
    session_repo = SQLAlchemySessionRepository(db)
    incomplete = await session_repo.find_incomplete_sessions_by_user(
        user_info.jira_user_id
    )

    from app.schemas.auth import IncompleteSessionInfo
    from app.schemas.base import SessionStage

    incomplete_sessions = [
        IncompleteSessionInfo(
            session_id=s.id,
            site_name=s.site_name or "",
            stage=SessionStage(s.current_stage),
            created_at=s.created_at,
            tickets_generated=s.total_tickets_generated,
            last_activity=s.updated_at or s.created_at,
        )
        for s in incomplete
    ]

    return AuthStatusResponse(
        authenticated=True,
        user_info=user_info,
        recovery_available=len(incomplete_sessions) > 0,
        incomplete_sessions=incomplete_sessions,
    )


@router.post("/logout")
async def logout(
    response: Response,
    user_data: tuple = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Log out current user.

    Clears session cookie and deletes stored tokens.
    """
    user_info, _ = user_data

    # Delete tokens from database
    auth_repo = SQLAlchemyAuthRepository(db)
    await auth_repo.delete_tokens(user_info.jira_user_id)

    # Clear session cookie
    response.delete_cookie(key="session")

    return {"success": True, "message": "Logged out successfully"}
