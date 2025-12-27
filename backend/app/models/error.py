# app/models/error.py
"""
Error and audit log SQLAlchemy models: SessionError, AuditLog.
"""
from datetime import datetime
from typing import Optional, TYPE_CHECKING, Any

from sqlalchemy import String, Integer, DateTime, Text, ForeignKey, Index, Enum as SQLEnum, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin, GUIDString
from app.schemas.base import ErrorCategory, ErrorSeverity, EventCategory, AuditLevel

if TYPE_CHECKING:
    from app.models.session import Session


class SessionError(Base, UUIDMixin, TimestampMixin):
    """
    Session-specific error tracking.
    Stores errors with categorization for UI presentation.
    """
    __tablename__ = "session_errors"
    __table_args__ = (
        Index('idx_session_errors_session_id', 'session_id'),
        Index('idx_session_errors_category', 'category'),
        Index('idx_session_errors_severity', 'severity'),
    )

    # Parent session
    session_id: Mapped[Any] = mapped_column(
        GUIDString(),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False
    )

    # Error classification
    category: Mapped[ErrorCategory] = mapped_column(
        SQLEnum(ErrorCategory, native_enum=False, length=50),
        nullable=False
    )
    severity: Mapped[ErrorSeverity] = mapped_column(
        SQLEnum(ErrorSeverity, native_enum=False, length=50),
        nullable=False
    )

    # Error content
    error_code: Mapped[Optional[str]] = mapped_column(String(50))
    user_message: Mapped[str] = mapped_column(Text, nullable=False)
    technical_details: Mapped[Optional[dict]] = mapped_column(JSON)

    # Recovery guidance
    recovery_actions: Mapped[Optional[list]] = mapped_column(JSON)

    # Context
    workflow_stage: Mapped[Optional[str]] = mapped_column(String(50))
    entity_type: Mapped[Optional[str]] = mapped_column(String(50))
    entity_id: Mapped[Optional[str]] = mapped_column(String(255))

    # Relationship
    session: Mapped["Session"] = relationship("Session", back_populates="session_errors")

    def to_dict(self) -> dict:
        """Serialize error to dictionary."""
        return {
            "id": str(self.id),
            "session_id": str(self.session_id),
            "category": self.category.value,
            "severity": self.severity.value,
            "error_code": self.error_code,
            "user_message": self.user_message,
            "recovery_actions": self.recovery_actions,
            "workflow_stage": self.workflow_stage,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class AuditLog(Base, UUIDMixin):
    """
    Comprehensive audit logging for compliance and debugging.
    Tracks all significant operations in the system.
    """
    __tablename__ = "audit_log"
    __table_args__ = (
        Index('idx_audit_log_session_id', 'session_id'),
        Index('idx_audit_log_jira_user_id', 'jira_user_id'),
        Index('idx_audit_log_category', 'category'),
        Index('idx_audit_log_created_at', 'created_at'),
    )

    # Event identification
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[EventCategory] = mapped_column(
        SQLEnum(EventCategory, native_enum=False, length=50),
        nullable=False
    )
    audit_level: Mapped[AuditLevel] = mapped_column(
        SQLEnum(AuditLevel, native_enum=False, length=50),
        default=AuditLevel.BASIC
    )

    # Event description
    description: Mapped[str] = mapped_column(Text, nullable=False)
    event_data: Mapped[Optional[dict]] = mapped_column(JSON)

    # Context references
    session_id: Mapped[Optional[Any]] = mapped_column(
        GUIDString(),
        ForeignKey("sessions.id", ondelete="SET NULL")
    )
    jira_user_id: Mapped[Optional[str]] = mapped_column(String(255))
    entity_type: Mapped[Optional[str]] = mapped_column(String(50))
    entity_id: Mapped[Optional[str]] = mapped_column(String(255))

    # Request tracking
    request_id: Mapped[Optional[str]] = mapped_column(String(100))
    execution_time_ms: Mapped[Optional[int]] = mapped_column(Integer)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )

    def to_dict(self) -> dict:
        """Serialize audit log entry to dictionary."""
        return {
            "id": str(self.id),
            "event_type": self.event_type,
            "category": self.category.value,
            "audit_level": self.audit_level.value,
            "description": self.description,
            "event_data": self.event_data,
            "session_id": str(self.session_id) if self.session_id else None,
            "jira_user_id": self.jira_user_id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "request_id": self.request_id,
            "execution_time_ms": self.execution_time_ms,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
