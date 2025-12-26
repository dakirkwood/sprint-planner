"""Session management API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.services import get_session_service
from app.schemas.auth import (
    IncompleteSessionsResponse,
    SessionCreateRequest,
    SessionRecoveryResponse,
    SessionResponse,
    UserInfo,
)
from app.services.exceptions import (
    ResourceNotFoundError,
    SessionError,
    AuthorizationError,
    ExternalServiceError,
)
from app.services.session_service import SessionService


router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    request: SessionCreateRequest,
    user_data: tuple = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service),
) -> SessionResponse:
    """Create a new workflow session.

    Creates a session for the authenticated user with the specified
    site configuration and Jira project.
    """
    user_info, access_token = user_data

    try:
        return await session_service.create_session(
            request=request,
            user_id=user_info.jira_user_id,
            access_token=access_token,
            user_info=user_info,
        )
    except SessionError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": e.message,
                "category": e.category,
                "recovery_actions": e.recovery_actions,
            },
        )
    except AuthorizationError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": e.message,
                "category": e.category,
                "recovery_actions": e.recovery_actions,
            },
        )
    except ExternalServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "message": e.message,
                "category": e.category,
                "recovery_actions": e.recovery_actions,
            },
        )


@router.post("/{session_id}/recover", response_model=SessionRecoveryResponse)
async def recover_session(
    session_id: UUID,
    user_data: tuple = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service),
) -> SessionRecoveryResponse:
    """Recover an incomplete session.

    Allows user to continue from where they left off.
    """
    user_info, _ = user_data

    try:
        return await session_service.recover_session(
            session_id=session_id,
            user_id=user_info.jira_user_id,
        )
    except ResourceNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "message": e.message,
                "category": e.category,
            },
        )
    except SessionError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": e.message,
                "category": e.category,
                "recovery_actions": e.recovery_actions,
            },
        )


@router.get("/incomplete", response_model=IncompleteSessionsResponse)
async def get_incomplete_sessions(
    user_data: tuple = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service),
) -> IncompleteSessionsResponse:
    """Get list of user's incomplete sessions.

    Returns sessions that can be recovered and continued.
    """
    user_info, _ = user_data

    incomplete = await session_service.get_incomplete_sessions(
        user_id=user_info.jira_user_id,
    )

    return IncompleteSessionsResponse(incomplete_sessions=incomplete)
