"""SQLAlchemy implementation of auth repository."""

from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth import JiraAuthToken, JiraProjectContext
from app.repositories.interfaces.auth_repository import AuthRepositoryInterface
from app.core.security import encrypt_token


class SQLAlchemyAuthRepository(AuthRepositoryInterface):
    """SQLAlchemy implementation of auth repository."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def store_tokens(
        self,
        jira_user_id: str,
        access_token: str,
        refresh_token: str,
        expires_in: int,
        granted_scopes: List[str],
    ) -> None:
        """Store OAuth tokens for a user."""
        # Check if token record exists
        existing = await self.get_tokens(jira_user_id)

        if existing:
            existing.update_tokens(access_token, refresh_token, expires_in)
            existing.granted_scopes = granted_scopes
        else:
            token = JiraAuthToken(
                jira_user_id=jira_user_id,
                encrypted_access_token=encrypt_token(access_token),
                encrypted_refresh_token=encrypt_token(refresh_token),
                token_expires_at=datetime.utcnow() + timedelta(seconds=expires_in),
                granted_scopes=granted_scopes,
            )
            self.db.add(token)

        await self.db.flush()

    async def get_tokens(self, jira_user_id: str) -> Optional[JiraAuthToken]:
        """Get tokens for a user."""
        stmt = select(JiraAuthToken).where(
            JiraAuthToken.jira_user_id == jira_user_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def refresh_tokens(
        self,
        jira_user_id: str,
        new_access_token: str,
        new_refresh_token: str,
        expires_in: int,
    ) -> None:
        """Update tokens after refresh."""
        token = await self.get_tokens(jira_user_id)
        if token:
            token.update_tokens(new_access_token, new_refresh_token, expires_in)
            await self.db.flush()

    async def delete_tokens(self, jira_user_id: str) -> None:
        """Delete tokens for a user."""
        stmt = delete(JiraAuthToken).where(
            JiraAuthToken.jira_user_id == jira_user_id
        )
        await self.db.execute(stmt)
        await self.db.flush()

    async def find_expiring_tokens(
        self,
        buffer_minutes: int = 60,
    ) -> List[JiraAuthToken]:
        """Find tokens that will expire soon."""
        cutoff = datetime.utcnow() + timedelta(minutes=buffer_minutes)
        stmt = select(JiraAuthToken).where(
            JiraAuthToken.token_expires_at < cutoff
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def token_needs_refresh(
        self,
        jira_user_id: str,
        buffer_minutes: int = 5,
    ) -> bool:
        """Check if token needs refresh."""
        token = await self.get_tokens(jira_user_id)
        if not token:
            return True
        return token.needs_refresh(buffer_minutes)

    async def cache_project_context(
        self,
        session_id: UUID,
        project_data: dict,
    ) -> JiraProjectContext:
        """Cache project context for session."""
        # Check if context exists
        existing = await self.get_project_context(session_id)

        if existing:
            # Replace with fresh data
            existing.project_key = project_data["project_key"]
            existing.project_name = project_data["project_name"]
            existing.can_create_tickets = project_data.get("can_create_tickets", False)
            existing.can_assign_tickets = project_data.get("can_assign_tickets", False)
            existing.available_sprints = project_data.get("available_sprints", [])
            existing.team_members = project_data.get("team_members", [])
            existing.cached_at = datetime.utcnow()
            await self.db.flush()
            return existing

        context = JiraProjectContext(
            session_id=session_id,
            project_key=project_data["project_key"],
            project_name=project_data["project_name"],
            can_create_tickets=project_data.get("can_create_tickets", False),
            can_assign_tickets=project_data.get("can_assign_tickets", False),
            available_sprints=project_data.get("available_sprints", []),
            team_members=project_data.get("team_members", []),
        )
        self.db.add(context)
        await self.db.flush()
        return context

    async def get_project_context(
        self,
        session_id: UUID,
    ) -> Optional[JiraProjectContext]:
        """Get cached project context for session."""
        stmt = select(JiraProjectContext).where(
            JiraProjectContext.session_id == session_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def is_project_context_stale(
        self,
        session_id: UUID,
        max_age_hours: int = 24,
    ) -> bool:
        """Check if project context cache is stale."""
        context = await self.get_project_context(session_id)
        if not context:
            return True
        return context.is_stale(max_age_hours)

    async def refresh_project_context(
        self,
        session_id: UUID,
        fresh_data: dict,
    ) -> JiraProjectContext:
        """Replace project context with fresh data."""
        return await self.cache_project_context(session_id, fresh_data)

    async def validate_sprint_name(
        self,
        session_id: UUID,
        sprint_name: str,
    ) -> bool:
        """Validate sprint name against cached data."""
        context = await self.get_project_context(session_id)
        if not context:
            return False
        return context.validate_sprint_name(sprint_name)

    async def validate_assignee_id(
        self,
        session_id: UUID,
        account_id: str,
    ) -> bool:
        """Validate assignee ID against cached data."""
        context = await self.get_project_context(session_id)
        if not context:
            return False
        return context.validate_assignee_id(account_id)

    async def get_active_sprints(self, session_id: UUID) -> List[dict]:
        """Get active sprints from cached data."""
        context = await self.get_project_context(session_id)
        if not context:
            return []
        return context.get_active_sprints()

    async def get_team_members(self, session_id: UUID) -> List[dict]:
        """Get team members from cached data."""
        context = await self.get_project_context(session_id)
        if not context:
            return []
        return context.team_members or []

    async def cleanup_expired_tokens(self, grace_period_days: int = 30) -> int:
        """Delete tokens expired beyond grace period."""
        cutoff = datetime.utcnow() - timedelta(days=grace_period_days)
        stmt = delete(JiraAuthToken).where(
            JiraAuthToken.token_expires_at < cutoff
        )
        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.rowcount
