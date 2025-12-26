"""SessionError and AuditLog models."""

from datetime import datetime, timedelta
from typing import Optional, List, TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    String,
    Text,
    Integer,
    DateTime,
    ForeignKey,
    Index,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.schemas.base import ErrorCategory, ErrorSeverity, EventCategory, AuditLevel

if TYPE_CHECKING:
    from app.models.session import Session


class SessionError(Base):
    """Error tracking and storage for session workflow issues."""

    __tablename__ = "session_errors"
    __table_args__ = (
        Index("idx_session_errors_session_id", "session_id"),
        Index("idx_session_errors_category", "error_category"),
        Index("idx_session_errors_severity", "severity"),
    )

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Foreign key
    session_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Error classification
    error_category: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(50), nullable=False)
    operation_stage: Mapped[str] = mapped_column(String(50), nullable=False)

    # Related entities (optional)
    related_file_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("uploaded_files.id", ondelete="SET NULL"),
        nullable=True,
    )
    related_ticket_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tickets.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Error details
    user_message: Mapped[str] = mapped_column(Text, nullable=False)
    recovery_actions: Mapped[dict] = mapped_column(JSONB, nullable=False)
    technical_details: Mapped[dict] = mapped_column(JSONB, nullable=False)
    error_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationship
    session: Mapped["Session"] = relationship("Session", back_populates="session_errors")

    def is_blocking(self) -> bool:
        """Check if error is blocking."""
        return self.severity == ErrorSeverity.BLOCKING.value

    def get_recovery_action_list(self) -> List[str]:
        """Extract recovery actions from JSON field."""
        actions = self.recovery_actions or {}
        return actions.get("actions", [])

    @property
    def is_user_fixable(self) -> bool:
        """Check if error is user fixable."""
        return self.error_category == ErrorCategory.USER_FIXABLE.value

    @property
    def requires_admin(self) -> bool:
        """Check if error requires admin intervention."""
        return self.error_category == ErrorCategory.ADMIN_REQUIRED.value

    @property
    def age_minutes(self) -> float:
        """Get error age in minutes."""
        now = datetime.utcnow()
        created = self.created_at.replace(tzinfo=None)
        delta = now - created
        return delta.total_seconds() / 60


class AuditLog(Base):
    """Comprehensive audit trail for user actions and system events."""

    __tablename__ = "audit_log"
    __table_args__ = (
        Index("idx_audit_log_session_id", "session_id"),
        Index("idx_audit_log_jira_user_id", "jira_user_id"),
        Index("idx_audit_log_event_category", "event_category"),
        Index("idx_audit_log_audit_level", "audit_level"),
        Index("idx_audit_log_created_at", "created_at"),
    )

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Optional relationships
    session_id: Mapped[Optional[UUID]] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
    jira_user_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Event classification
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    event_category: Mapped[str] = mapped_column(String(50), nullable=False)
    audit_level: Mapped[str] = mapped_column(
        String(50),
        default=AuditLevel.BASIC.value,
        nullable=False,
    )

    # Event details
    description: Mapped[str] = mapped_column(Text, nullable=False)
    entity_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    entity_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    event_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Request context
    request_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    execution_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    @property
    def is_comprehensive(self) -> bool:
        """Check if this is a comprehensive audit log."""
        return self.audit_level == AuditLevel.COMPREHENSIVE.value

    @property
    def age_days(self) -> float:
        """Get log age in days."""
        now = datetime.utcnow()
        created = self.created_at.replace(tzinfo=None)
        delta = now - created
        return delta.total_seconds() / (60 * 60 * 24)

    @property
    def has_performance_data(self) -> bool:
        """Check if execution time is recorded."""
        return self.execution_time_ms is not None
