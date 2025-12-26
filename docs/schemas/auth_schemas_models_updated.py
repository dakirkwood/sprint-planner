# Authentication & Session Pydantic Models
# /backend/app/schemas/auth_schemas.py
#
# UPDATED: December 25, 2025
# - Removed duplicate SessionStage enum (now imported from base_schemas)

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID

# Import base models and enums from base_schemas
from .base_schemas import BaseRequest, BaseResponse, SessionStage


# =============================================================================
# SUPPORTING MODELS
# =============================================================================

class UserInfo(BaseModel):
    """Jira user information from OAuth"""
    jira_user_id: str
    display_name: str
    email: str


class CurrentSessionInfo(BaseModel):
    """Summary of current active session"""
    session_id: UUID
    stage: SessionStage
    site_name: str
    created_at: datetime


class IncompleteSessionInfo(BaseModel):
    """Summary of recoverable incomplete session"""
    session_id: UUID
    site_name: str
    stage: SessionStage
    created_at: datetime
    tickets_generated: int = 0
    last_activity: datetime


class SessionPermissions(BaseModel):
    """User's validated permissions for current session"""
    can_create_tickets: bool
    validated_at: datetime


class ProjectPermissions(BaseModel):
    """Jira project-level permissions"""
    can_create_tickets: bool = True
    can_assign_tickets: bool


class SprintOption(BaseModel):
    """Sprint available for ticket assignment"""
    id: str
    name: str
    state: str  # "active", "closed", "future"


class TeamMemberOption(BaseModel):
    """Team member available for ticket assignment"""
    account_id: str
    display_name: str
    email: Optional[str] = None
    active: bool = True


class ProjectContextData(BaseModel):
    """Cached Jira project metadata for session"""
    project_key: str
    project_name: str
    permissions: ProjectPermissions
    available_sprints: List[SprintOption]
    team_members: List[TeamMemberOption]
    cached_at: datetime


# =============================================================================
# OAUTH FLOW MODELS
# =============================================================================

class LoginRedirectResponse(BaseResponse):
    """Response containing OAuth authorization URL"""
    redirect_url: str  # OAuth authorization URL with PKCE challenge
    state: str         # CSRF protection parameter


# =============================================================================
# SESSION MANAGEMENT MODELS
# =============================================================================

class SessionCreateRequest(BaseRequest):
    """Request to create a new workflow session"""
    site_name: str = Field(min_length=1, max_length=255)
    site_description: Optional[str] = None
    llm_provider_choice: str = Field(default="openai", pattern="^(openai|anthropic)$")
    jira_project_key: str = Field(min_length=1, max_length=50)


class SessionResponse(BaseResponse):
    """Response after session creation or retrieval"""
    session_id: UUID
    site_name: str
    current_stage: SessionStage = SessionStage.UPLOAD
    user_info: UserInfo
    project_context: ProjectContextData


# =============================================================================
# SESSION RECOVERY MODELS
# =============================================================================

class SessionRecoveryRequest(BaseRequest):
    """Request to recover an incomplete session"""
    session_id: UUID


class SessionRecoveryResponse(BaseResponse):
    """Response after session recovery"""
    session_id: UUID
    restored_session: CurrentSessionInfo
    tokens_applied: bool = True
    ready_to_continue: bool = True


# =============================================================================
# AUTH STATUS MODELS
# =============================================================================

class AuthStatusResponse(BaseResponse):
    """Complete authentication and session status"""
    authenticated: bool
    user_info: Optional[UserInfo] = None
    current_session: Optional[CurrentSessionInfo] = None
    recovery_available: bool = False
    incomplete_sessions: List[IncompleteSessionInfo] = []
    permissions: Optional[SessionPermissions] = None
