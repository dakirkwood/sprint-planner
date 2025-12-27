# app/models/auth.py
"""
Authentication-related SQLAlchemy models: JiraAuthToken, JiraProjectContext.
"""
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING, Any

from sqlalchemy import String, Integer, DateTime, LargeBinary, ForeignKey, Index, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin, GUIDString

if TYPE_CHECKING:
    pass  # No circular imports needed


class JiraAuthToken(Base, TimestampMixin):
    """
    Encrypted Jira OAuth tokens storage.
    One token set per Jira user.
    """
    __tablename__ = "jira_auth_tokens"
    __table_args__ = (
        Index('idx_jira_auth_tokens_expires_at', 'expires_at'),
    )

    # Primary key is jira_user_id (one token set per user)
    jira_user_id: Mapped[str] = mapped_column(String(255), primary_key=True)

    # Encrypted tokens (stored as bytes)
    access_token_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    refresh_token_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)

    # Token metadata
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    granted_scopes: Mapped[List[str]] = mapped_column(JSON, nullable=False)

    def is_expired(self) -> bool:
        """Check if access token is expired."""
        return datetime.utcnow() > self.expires_at.replace(tzinfo=None)

    def needs_refresh(self, buffer_minutes: int = 5) -> bool:
        """Check if token should be refreshed (within buffer of expiry)."""
        from datetime import timedelta
        buffer = timedelta(minutes=buffer_minutes)
        return datetime.utcnow() > (self.expires_at.replace(tzinfo=None) - buffer)

    def to_dict(self) -> dict:
        """Serialize token metadata (not actual tokens)."""
        return {
            "jira_user_id": self.jira_user_id,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "granted_scopes": self.granted_scopes,
            "is_expired": self.is_expired(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class JiraProjectContext(Base, UUIDMixin, TimestampMixin):
    """
    Cached Jira project context for validation.
    Stores sprints, team members, and other project data.
    """
    __tablename__ = "jira_project_context"
    __table_args__ = (
        Index('idx_jira_project_context_session_id', 'session_id'),
    )

    # Parent session
    session_id: Mapped[Any] = mapped_column(
        GUIDString(),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True
    )

    # Project information
    project_key: Mapped[str] = mapped_column(String(50), nullable=False)
    project_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Cached data
    active_sprints: Mapped[Optional[List[dict]]] = mapped_column(JSON)
    team_members: Mapped[Optional[List[dict]]] = mapped_column(JSON)
    issue_types: Mapped[Optional[List[dict]]] = mapped_column(JSON)

    # Cache control
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    def is_stale(self, max_age_hours: int = 24) -> bool:
        """Check if cached data is stale."""
        from datetime import timedelta
        age = datetime.utcnow() - self.fetched_at.replace(tzinfo=None)
        return age > timedelta(hours=max_age_hours)

    def validate_sprint(self, sprint_name: str) -> bool:
        """Validate sprint name against cached sprints."""
        if not self.active_sprints:
            return False
        return any(s.get("name") == sprint_name for s in self.active_sprints)

    def validate_assignee(self, account_id: str) -> bool:
        """Validate assignee against cached team members."""
        if not self.team_members:
            return False
        return any(m.get("accountId") == account_id for m in self.team_members)

    def to_dict(self) -> dict:
        """Serialize project context."""
        return {
            "id": str(self.id),
            "session_id": str(self.session_id),
            "project_key": self.project_key,
            "project_name": self.project_name,
            "active_sprints": self.active_sprints,
            "team_members": self.team_members,
            "issue_types": self.issue_types,
            "fetched_at": self.fetched_at.isoformat() if self.fetched_at else None,
            "is_stale": self.is_stale(),
        }
