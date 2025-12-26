"""JiraAuthToken and JiraProjectContext models."""

from datetime import datetime, timedelta
from typing import Optional, List, TYPE_CHECKING
from uuid import UUID

from sqlalchemy import String, Boolean, DateTime, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.core.security import encrypt_token, decrypt_token

if TYPE_CHECKING:
    from app.models.session import Session


class JiraAuthToken(Base):
    """OAuth token storage with encryption for Jira authentication."""

    __tablename__ = "jira_auth_tokens"
    __table_args__ = (
        Index("idx_jira_auth_tokens_expires_at", "token_expires_at"),
    )

    # Primary key is jira_user_id
    jira_user_id: Mapped[str] = mapped_column(String(255), primary_key=True)

    # Encrypted tokens
    encrypted_access_token: Mapped[str] = mapped_column(String(2000), nullable=False)
    encrypted_refresh_token: Mapped[str] = mapped_column(String(2000), nullable=False)

    # Expiration
    token_expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # OAuth scopes
    granted_scopes: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # Refresh tracking
    last_refresh_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Creation timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def is_expired(self) -> bool:
        """Check if token has expired."""
        now = datetime.utcnow()
        expires_at = self.token_expires_at.replace(tzinfo=None)
        return now > expires_at

    def needs_refresh(self, buffer_minutes: int = 5) -> bool:
        """Check if token expires within buffer time."""
        now = datetime.utcnow()
        expires_at = self.token_expires_at.replace(tzinfo=None)
        buffer = timedelta(minutes=buffer_minutes)
        return now + buffer > expires_at

    def decrypt_access_token(self) -> str:
        """Decrypt and return access token."""
        return decrypt_token(self.encrypted_access_token)

    def decrypt_refresh_token(self) -> str:
        """Decrypt and return refresh token."""
        return decrypt_token(self.encrypted_refresh_token)

    def update_tokens(
        self,
        access_token: str,
        refresh_token: str,
        expires_in: int,
    ) -> None:
        """Encrypt and store new token pair."""
        self.encrypted_access_token = encrypt_token(access_token)
        self.encrypted_refresh_token = encrypt_token(refresh_token)
        self.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        self.last_refresh_at = datetime.utcnow()

    @property
    def expires_in_minutes(self) -> Optional[int]:
        """Get minutes until token expiration, None if expired."""
        now = datetime.utcnow()
        expires_at = self.token_expires_at.replace(tzinfo=None)
        if now > expires_at:
            return None
        delta = expires_at - now
        return int(delta.total_seconds() / 60)

    @property
    def is_refresh_needed(self) -> bool:
        """Check if token should be refreshed (within 5-minute buffer)."""
        return self.needs_refresh(buffer_minutes=5)

    @property
    def days_since_created(self) -> float:
        """Get days since token creation."""
        now = datetime.utcnow()
        created = self.created_at.replace(tzinfo=None)
        delta = now - created
        return delta.total_seconds() / (60 * 60 * 24)


class JiraProjectContext(Base):
    """Cached Jira project metadata for session optimization."""

    __tablename__ = "jira_project_context"

    # session_id as primary key (true 1:1 relationship)
    session_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        primary_key=True,
    )

    # Project info
    project_key: Mapped[str] = mapped_column(String(50), nullable=False)
    project_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Permissions
    can_create_tickets: Mapped[bool] = mapped_column(Boolean, default=False)
    can_assign_tickets: Mapped[bool] = mapped_column(Boolean, default=False)

    # Cached data
    available_sprints: Mapped[dict] = mapped_column(JSONB, nullable=False)
    team_members: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # Cache timestamp
    cached_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def is_stale(self, max_age_hours: int = 24) -> bool:
        """Check if cache is older than specified hours."""
        now = datetime.utcnow()
        cached = self.cached_at.replace(tzinfo=None)
        max_age = timedelta(hours=max_age_hours)
        return now - cached > max_age

    def get_active_sprints(self) -> List[dict]:
        """Get sprints with 'active' state."""
        sprints = self.available_sprints or []
        return [s for s in sprints if s.get("state") == "active"]

    def get_team_member_by_id(self, account_id: str) -> Optional[dict]:
        """Find team member by Jira account ID."""
        members = self.team_members or []
        for member in members:
            if member.get("account_id") == account_id:
                return member
        return None

    def validate_sprint_name(self, sprint_name: str) -> bool:
        """Check if sprint name exists in cached data."""
        sprints = self.available_sprints or []
        return any(s.get("name") == sprint_name for s in sprints)

    def validate_assignee_id(self, account_id: str) -> bool:
        """Check if account_id is valid team member."""
        return self.get_team_member_by_id(account_id) is not None

    @property
    def cache_age_hours(self) -> float:
        """Get cache age in hours."""
        now = datetime.utcnow()
        cached = self.cached_at.replace(tzinfo=None)
        delta = now - cached
        return delta.total_seconds() / (60 * 60)

    @property
    def has_active_sprints(self) -> bool:
        """Check if any sprints are active."""
        return len(self.get_active_sprints()) > 0

    @property
    def active_team_member_count(self) -> int:
        """Count active team members."""
        members = self.team_members or []
        return sum(1 for m in members if m.get("active", True))
