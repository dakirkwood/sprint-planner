"""Service dependencies for API endpoints."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.database import get_db
from app.api.dependencies.auth import get_jira_service
from app.integrations.jira.client import JiraService
from app.repositories.sqlalchemy.auth_repository import SQLAlchemyAuthRepository
from app.repositories.sqlalchemy.session_repository import SQLAlchemySessionRepository
from app.services.session_service import SessionService


async def get_session_service(
    db: AsyncSession = Depends(get_db),
    jira_service: JiraService = Depends(get_jira_service),
) -> SessionService:
    """Get SessionService instance."""
    session_repo = SQLAlchemySessionRepository(db)
    auth_repo = SQLAlchemyAuthRepository(db)

    return SessionService(
        session_repo=session_repo,
        auth_repo=auth_repo,
        jira_service=jira_service,
    )
