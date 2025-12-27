# app/models/session.py
"""
Session-related SQLAlchemy models: Session, SessionTask, SessionValidation.
"""
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import String, Integer, DateTime, Boolean, ForeignKey, Index, Enum as SQLEnum, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin, GUIDString
from app.schemas.base import (
    SessionStage,
    SessionStatus,
    TaskType,
    TaskStatus,
    AdfValidationStatus
)

if TYPE_CHECKING:
    from app.models.ticket import Ticket
    from app.models.upload import UploadedFile
    from app.models.error import SessionError


# Stage transition rules: allowed transitions from each stage
STAGE_TRANSITIONS = {
    SessionStage.SITE_INFO_COLLECTION: [SessionStage.UPLOAD],
    SessionStage.UPLOAD: [SessionStage.PROCESSING],
    SessionStage.PROCESSING: [SessionStage.REVIEW],
    SessionStage.REVIEW: [SessionStage.JIRA_EXPORT, SessionStage.PROCESSING],  # Can reprocess
    SessionStage.JIRA_EXPORT: [SessionStage.COMPLETED, SessionStage.REVIEW],  # Can go back
    SessionStage.COMPLETED: [],  # Terminal state
}


class Session(Base, UUIDMixin, TimestampMixin):
    """
    Core workflow state tracking model.
    Tracks user workflow progression through defined stages.
    """
    __tablename__ = "sessions"
    __table_args__ = (
        Index('idx_sessions_jira_user_id', 'jira_user_id'),
        Index('idx_sessions_status', 'status'),
        Index('idx_sessions_current_stage', 'current_stage'),
        Index('idx_sessions_created_at', 'created_at'),
    )

    # User identity
    jira_user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    jira_display_name: Mapped[Optional[str]] = mapped_column(String(255))

    # Site information
    site_name: Mapped[Optional[str]] = mapped_column(String(255))
    site_description: Mapped[Optional[str]] = mapped_column(Text)

    # Configuration
    jira_project_key: Mapped[Optional[str]] = mapped_column(String(50))
    llm_provider_choice: Mapped[Optional[str]] = mapped_column(String(50))

    # Workflow state
    current_stage: Mapped[SessionStage] = mapped_column(
        SQLEnum(SessionStage, native_enum=False, length=50),
        default=SessionStage.UPLOAD,
        nullable=False
    )
    status: Mapped[SessionStatus] = mapped_column(
        SQLEnum(SessionStatus, native_enum=False, length=50),
        default=SessionStatus.ACTIVE,
        nullable=False
    )

    # Progress tracking
    total_tickets_generated: Mapped[int] = mapped_column(Integer, default=0)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relationships - Eager loading for frequently accessed data
    session_task: Mapped[Optional["SessionTask"]] = relationship(
        "SessionTask",
        back_populates="session",
        uselist=False,
        lazy="joined",
        cascade="all, delete-orphan"
    )
    session_validation: Mapped[Optional["SessionValidation"]] = relationship(
        "SessionValidation",
        back_populates="session",
        uselist=False,
        lazy="joined",
        cascade="all, delete-orphan"
    )

    # Relationships - Lazy loading for large collections
    uploaded_files: Mapped[List["UploadedFile"]] = relationship(
        "UploadedFile",
        back_populates="session",
        lazy="select",
        cascade="all, delete-orphan"
    )
    tickets: Mapped[List["Ticket"]] = relationship(
        "Ticket",
        back_populates="session",
        lazy="select",
        cascade="all, delete-orphan"
    )
    session_errors: Mapped[List["SessionError"]] = relationship(
        "SessionError",
        back_populates="session",
        lazy="select",
        cascade="all, delete-orphan"
    )

    def can_transition_to(self, new_stage: SessionStage) -> bool:
        """Check if transition to new stage is allowed."""
        allowed = STAGE_TRANSITIONS.get(self.current_stage, [])
        return new_stage in allowed

    @property
    def is_recoverable(self) -> bool:
        """Check if session can be recovered (not completed, within 7-day window)."""
        if self.status == SessionStatus.COMPLETED:
            return False
        if self.created_at is None:
            return True
        days_old = (datetime.utcnow() - self.created_at.replace(tzinfo=None)).days
        return days_old <= 7

    @property
    def stage_display_name(self) -> str:
        """Human-readable stage names for UI display."""
        display_names = {
            SessionStage.SITE_INFO_COLLECTION: "Site Information",
            SessionStage.UPLOAD: "File Upload",
            SessionStage.PROCESSING: "Processing",
            SessionStage.REVIEW: "Review",
            SessionStage.JIRA_EXPORT: "Jira Export",
            SessionStage.COMPLETED: "Completed",
        }
        return display_names.get(self.current_stage, str(self.current_stage.value))

    def to_dict(self) -> dict:
        """Serialize session to dictionary (direct columns only)."""
        return {
            "id": str(self.id),
            "jira_user_id": self.jira_user_id,
            "jira_display_name": self.jira_display_name,
            "site_name": self.site_name,
            "site_description": self.site_description,
            "jira_project_key": self.jira_project_key,
            "llm_provider_choice": self.llm_provider_choice,
            "current_stage": self.current_stage.value,
            "status": self.status.value,
            "total_tickets_generated": self.total_tickets_generated,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class SessionTask(Base):
    """
    Background task tracking for a session.
    Tracks currently running or most recent background task.
    """
    __tablename__ = "session_tasks"

    # Primary key is session_id (1:1 relationship)
    session_id: Mapped[Any] = mapped_column(
        GUIDString(),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        primary_key=True
    )

    # Task identification
    task_id: Mapped[Optional[Any]] = mapped_column(GUIDString())
    task_type: Mapped[Optional[TaskType]] = mapped_column(
        SQLEnum(TaskType, native_enum=False, length=50)
    )
    status: Mapped[Optional[TaskStatus]] = mapped_column(
        SQLEnum(TaskStatus, native_enum=False, length=50)
    )

    # Timing
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Error tracking
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    failure_context: Mapped[Optional[dict]] = mapped_column(JSON)

    # Relationship
    session: Mapped["Session"] = relationship("Session", back_populates="session_task")


class SessionValidation(Base):
    """
    ADF validation state tracking for a session.
    Tracks validation status for Jira export readiness.
    """
    __tablename__ = "session_validations"

    # Primary key is session_id (1:1 relationship)
    session_id: Mapped[Any] = mapped_column(
        GUIDString(),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        primary_key=True
    )

    # Validation state
    validation_status: Mapped[AdfValidationStatus] = mapped_column(
        SQLEnum(AdfValidationStatus, native_enum=False, length=50),
        default=AdfValidationStatus.PENDING
    )
    validation_passed: Mapped[bool] = mapped_column(Boolean, default=False)

    # Timing
    last_validated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_invalidated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Results
    validation_results: Mapped[Optional[dict]] = mapped_column(JSON)

    # Relationship
    session: Mapped["Session"] = relationship("Session", back_populates="session_validation")
