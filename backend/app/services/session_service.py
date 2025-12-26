"""Session management service."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from app.integrations.jira.client import JiraService
from app.integrations.jira.exceptions import JiraAuthError, JiraAPIError
from app.repositories.interfaces.auth_repository import AuthRepositoryInterface
from app.repositories.interfaces.session_repository import SessionRepositoryInterface
from app.schemas.auth import (
    CurrentSessionInfo,
    IncompleteSessionInfo,
    ProjectContextData,
    SessionCreateRequest,
    SessionRecoveryResponse,
    SessionResponse,
    UserInfo,
)
from app.schemas.base import SessionStage
from app.services.exceptions import (
    AuthorizationError,
    ExternalServiceError,
    ResourceNotFoundError,
    SessionError,
)


class SessionService:
    """Service for managing workflow sessions."""

    def __init__(
        self,
        session_repo: SessionRepositoryInterface,
        auth_repo: AuthRepositoryInterface,
        jira_service: JiraService,
    ):
        """Initialize session service.

        Args:
            session_repo: Session repository
            auth_repo: Auth repository for token/context storage
            jira_service: Jira API client
        """
        self.session_repo = session_repo
        self.auth_repo = auth_repo
        self.jira_service = jira_service

    async def create_session(
        self,
        request: SessionCreateRequest,
        user_id: str,
        access_token: str,
        user_info: UserInfo,
    ) -> SessionResponse:
        """Create a new workflow session.

        Args:
            request: Session creation request
            user_id: Jira user ID
            access_token: Valid Jira access token
            user_info: User information

        Returns:
            SessionResponse with session details

        Raises:
            SessionError: If project access validation fails
            ExternalServiceError: If Jira API fails
        """
        try:
            # Validate project access
            has_access = await self.jira_service.validate_project_access(
                project_key=request.jira_project_key,
                access_token=access_token,
            )

            if not has_access:
                raise SessionError(
                    message=f"You don't have access to create issues in project {request.jira_project_key}",
                    category="user_fixable",
                    recovery_actions=[
                        "Check that you have the correct project key",
                        "Request access from your Jira administrator",
                    ],
                )

            # Get project metadata for caching
            project_context = await self.jira_service.get_project_metadata(
                project_key=request.jira_project_key,
                access_token=access_token,
            )

            # Create session in database
            session = await self.session_repo.create_session({
                "jira_user_id": user_id,
                "jira_display_name": user_info.display_name,
                "site_name": request.site_name,
                "site_description": request.site_description,
                "llm_provider_choice": request.llm_provider_choice,
                "jira_project_key": request.jira_project_key,
                "current_stage": SessionStage.UPLOAD.value,
            })

            # Cache project context
            await self.auth_repo.cache_project_context(
                session_id=session.id,
                project_data={
                    "project_key": project_context.project_key,
                    "project_name": project_context.project_name,
                    "can_create_tickets": project_context.permissions.can_create_tickets,
                    "can_assign_tickets": project_context.permissions.can_assign_tickets,
                    "available_sprints": [
                        {"id": s.id, "name": s.name, "state": s.state}
                        for s in project_context.available_sprints
                    ],
                    "team_members": [
                        {
                            "account_id": m.account_id,
                            "display_name": m.display_name,
                            "email": m.email,
                            "active": m.active,
                        }
                        for m in project_context.team_members
                    ],
                },
            )

            return SessionResponse(
                session_id=session.id,
                site_name=request.site_name,
                current_stage=SessionStage.UPLOAD,
                user_info=user_info,
                project_context=project_context,
            )

        except JiraAuthError as e:
            raise AuthorizationError(
                message="Your Jira authentication has expired",
                recovery_actions=["Please log in again"],
            ) from e
        except JiraAPIError as e:
            raise ExternalServiceError("Jira", str(e)) from e

    async def recover_session(
        self,
        session_id: UUID,
        user_id: str,
    ) -> SessionRecoveryResponse:
        """Recover an incomplete session.

        Args:
            session_id: ID of session to recover
            user_id: Current user's Jira ID

        Returns:
            SessionRecoveryResponse with session state

        Raises:
            ResourceNotFoundError: If session not found
            SessionError: If user doesn't own session
        """
        session = await self.session_repo.get_session_by_id(session_id)

        if not session:
            raise ResourceNotFoundError("Session", str(session_id))

        # Validate ownership
        if session.jira_user_id != user_id:
            raise SessionError(
                message="You don't have access to this session",
                category="user_fixable",
                recovery_actions=["Log in with the correct account"],
            )

        # Check if recoverable
        if not session.is_recoverable:
            raise SessionError(
                message="This session cannot be recovered",
                category="user_fixable",
                recovery_actions=["Create a new session"],
            )

        return SessionRecoveryResponse(
            session_id=session.id,
            restored_session=CurrentSessionInfo(
                session_id=session.id,
                stage=SessionStage(session.current_stage),
                site_name=session.site_name or "",
                created_at=session.created_at,
            ),
            tokens_applied=True,
            ready_to_continue=True,
        )

    async def get_incomplete_sessions(
        self,
        user_id: str,
    ) -> List[IncompleteSessionInfo]:
        """Get list of user's incomplete sessions.

        Args:
            user_id: Jira user ID

        Returns:
            List of incomplete session summaries
        """
        sessions = await self.session_repo.find_incomplete_sessions_by_user(user_id)

        return [
            IncompleteSessionInfo(
                session_id=s.id,
                site_name=s.site_name or "",
                stage=SessionStage(s.current_stage),
                created_at=s.created_at,
                tickets_generated=s.total_tickets_generated,
                last_activity=s.updated_at or s.created_at,
            )
            for s in sessions
        ]

    async def get_session_status(
        self,
        session_id: UUID,
        user_id: str,
    ) -> CurrentSessionInfo:
        """Get current session status.

        Args:
            session_id: Session ID
            user_id: Current user's Jira ID

        Returns:
            CurrentSessionInfo with session state

        Raises:
            ResourceNotFoundError: If session not found
            SessionError: If user doesn't own session
        """
        session = await self.session_repo.get_session_by_id(session_id)

        if not session:
            raise ResourceNotFoundError("Session", str(session_id))

        if session.jira_user_id != user_id:
            raise SessionError(
                message="You don't have access to this session",
                category="user_fixable",
            )

        return CurrentSessionInfo(
            session_id=session.id,
            stage=SessionStage(session.current_stage),
            site_name=session.site_name or "",
            created_at=session.created_at,
        )

    async def transition_stage(
        self,
        session_id: UUID,
        new_stage: SessionStage,
        user_id: str,
    ) -> CurrentSessionInfo:
        """Transition session to new stage.

        Args:
            session_id: Session ID
            new_stage: Target stage
            user_id: Current user's Jira ID

        Returns:
            Updated session info

        Raises:
            ResourceNotFoundError: If session not found
            SessionError: If transition not allowed
        """
        session = await self.session_repo.get_session_by_id(session_id)

        if not session:
            raise ResourceNotFoundError("Session", str(session_id))

        if session.jira_user_id != user_id:
            raise SessionError(
                message="You don't have access to this session",
                category="user_fixable",
            )

        if not session.can_transition_to(new_stage):
            raise SessionError(
                message=f"Cannot transition from {session.current_stage} to {new_stage.value}",
                category="user_fixable",
                recovery_actions=["Complete the current stage first"],
            )

        await self.session_repo.transition_stage(session_id, new_stage)

        return CurrentSessionInfo(
            session_id=session.id,
            stage=new_stage,
            site_name=session.site_name or "",
            created_at=session.created_at,
        )
