# app/repositories/sqlalchemy/auth_repository.py
"""
SQLAlchemy implementation of AuthRepositoryInterface.
"""
from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth import JiraAuthToken, JiraProjectContext
from app.repositories.interfaces.auth_repository import AuthRepositoryInterface


class SQLAlchemyAuthRepository(AuthRepositoryInterface):
    """
    SQLAlchemy implementation for authentication repository operations.
    """

    def __init__(self, session: AsyncSession):
        self._session = session

    # ==========================================================================
    # Token Management
    # ==========================================================================

    async def store_tokens(
        self,
        jira_user_id: str,
        access_token: str,
        refresh_token: str,
        expires_in: int,
        granted_scopes: List[str]
    ) -> None:
        """Store encrypted OAuth tokens for a user."""
        # For now, store as-is (encryption should be added in security module)
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

        # Check if token exists
        existing = await self.get_tokens(jira_user_id)

        if existing:
            existing.access_token_encrypted = access_token.encode()
            existing.refresh_token_encrypted = refresh_token.encode()
            existing.expires_at = expires_at
            existing.granted_scopes = granted_scopes
        else:
            token = JiraAuthToken(
                jira_user_id=jira_user_id,
                access_token_encrypted=access_token.encode(),
                refresh_token_encrypted=refresh_token.encode(),
                expires_at=expires_at,
                granted_scopes=granted_scopes
            )
            self._session.add(token)

        await self._session.flush()

    async def get_tokens(self, jira_user_id: str) -> Optional[JiraAuthToken]:
        """Get stored tokens for a user."""
        stmt = select(JiraAuthToken).where(JiraAuthToken.jira_user_id == jira_user_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def refresh_tokens(
        self,
        jira_user_id: str,
        new_access_token: str,
        new_refresh_token: str,
        expires_in: int
    ) -> None:
        """Update tokens after OAuth refresh."""
        token = await self.get_tokens(jira_user_id)
        if token:
            token.access_token_encrypted = new_access_token.encode()
            token.refresh_token_encrypted = new_refresh_token.encode()
            token.expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            await self._session.flush()

    async def delete_tokens(self, jira_user_id: str) -> None:
        """Delete stored tokens for a user."""
        stmt = delete(JiraAuthToken).where(JiraAuthToken.jira_user_id == jira_user_id)
        await self._session.execute(stmt)
        await self._session.flush()

    async def find_expiring_tokens(self, buffer_minutes: int = 60) -> List[JiraAuthToken]:
        """Find tokens expiring within buffer period."""
        threshold = datetime.utcnow() + timedelta(minutes=buffer_minutes)
        stmt = (
            select(JiraAuthToken)
            .where(JiraAuthToken.expires_at < threshold)
            .where(JiraAuthToken.expires_at > datetime.utcnow())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def token_needs_refresh(self, jira_user_id: str, buffer_minutes: int = 5) -> bool:
        """Check if user's token needs refresh."""
        token = await self.get_tokens(jira_user_id)
        if not token:
            return True
        return token.needs_refresh(buffer_minutes)

    # ==========================================================================
    # Project Context Management
    # ==========================================================================

    async def cache_project_context(self, session_id: UUID, project_data: dict) -> JiraProjectContext:
        """Cache Jira project context for validation."""
        context = JiraProjectContext(
            session_id=session_id,
            project_key=project_data.get("project_key", ""),
            project_name=project_data.get("project_name", ""),
            active_sprints=project_data.get("active_sprints"),
            team_members=project_data.get("team_members"),
            issue_types=project_data.get("issue_types"),
            fetched_at=datetime.utcnow()
        )
        self._session.add(context)
        await self._session.flush()
        return context

    async def get_project_context(self, session_id: UUID) -> Optional[JiraProjectContext]:
        """Get cached project context for session."""
        stmt = select(JiraProjectContext).where(JiraProjectContext.session_id == session_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def is_project_context_stale(self, session_id: UUID, max_age_hours: int = 24) -> bool:
        """Check if project context cache is stale."""
        context = await self.get_project_context(session_id)
        if not context:
            return True
        return context.is_stale(max_age_hours)

    async def refresh_project_context(self, session_id: UUID, fresh_data: dict) -> JiraProjectContext:
        """Update project context with fresh data."""
        context = await self.get_project_context(session_id)

        if context:
            context.project_key = fresh_data.get("project_key", context.project_key)
            context.project_name = fresh_data.get("project_name", context.project_name)
            context.active_sprints = fresh_data.get("active_sprints", context.active_sprints)
            context.team_members = fresh_data.get("team_members", context.team_members)
            context.issue_types = fresh_data.get("issue_types", context.issue_types)
            context.fetched_at = datetime.utcnow()
            await self._session.flush()
            return context
        else:
            return await self.cache_project_context(session_id, fresh_data)

    # ==========================================================================
    # Validation Support
    # ==========================================================================

    async def validate_sprint_name(self, session_id: UUID, sprint_name: str) -> bool:
        """Validate sprint name against cached project context."""
        context = await self.get_project_context(session_id)
        if not context:
            return False
        return context.validate_sprint(sprint_name)

    async def validate_assignee_id(self, session_id: UUID, account_id: str) -> bool:
        """Validate assignee ID against cached project context."""
        context = await self.get_project_context(session_id)
        if not context:
            return False
        return context.validate_assignee(account_id)

    async def get_active_sprints(self, session_id: UUID) -> List[dict]:
        """Get active sprints from cached project context."""
        context = await self.get_project_context(session_id)
        if not context or not context.active_sprints:
            return []
        return context.active_sprints

    async def get_team_members(self, session_id: UUID) -> List[dict]:
        """Get team members from cached project context."""
        context = await self.get_project_context(session_id)
        if not context or not context.team_members:
            return []
        return context.team_members

    # ==========================================================================
    # Cleanup Operations
    # ==========================================================================

    async def cleanup_expired_tokens(self, grace_period_days: int = 30) -> int:
        """Delete tokens expired beyond grace period. Returns count deleted."""
        cutoff = datetime.utcnow() - timedelta(days=grace_period_days)
        stmt = delete(JiraAuthToken).where(JiraAuthToken.expires_at < cutoff)
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount
