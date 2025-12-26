"""Session, SessionTask, and SessionValidation models."""

from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    String,
    Integer,
    DateTime,
    ForeignKey,
    Index,
    UniqueConstraint,
    Boolean,
    CheckConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.schemas.base import (
    SessionStage,
    SessionStatus,
    TaskType,
    TaskStatus,
    AdfValidationStatus,
)

if TYPE_CHECKING:
    from app.models.upload import UploadedFile
    from app.models.ticket import Ticket
    from app.models.error import SessionError


# Stage transition rules: sequential progression only
STAGE_ORDER = [
    SessionStage.SITE_INFO_COLLECTION,
    SessionStage.UPLOAD,
    SessionStage.PROCESSING,
    SessionStage.REVIEW,
    SessionStage.JIRA_EXPORT,
    SessionStage.COMPLETED,
]


class Session(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Core workflow state tracking model."""

    __tablename__ = "sessions"
    __table_args__ = (
        Index("idx_sessions_jira_user_id", "jira_user_id"),
        Index("idx_sessions_status", "status"),
        Index("idx_sessions_current_stage", "current_stage"),
        Index("idx_sessions_created_at", "created_at"),
    )

    # Core fields
    jira_user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    jira_display_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    site_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    site_description: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)
    jira_project_key: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    llm_provider_choice: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Workflow state
    current_stage: Mapped[str] = mapped_column(
        String(50),
        default=SessionStage.UPLOAD.value,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default=SessionStatus.ACTIVE.value,
        nullable=False,
    )

    # Metrics
    total_tickets_generated: Mapped[int] = mapped_column(Integer, default=0)

    # Completion tracking
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships - eager loading for small collections
    session_task: Mapped[Optional["SessionTask"]] = relationship(
        "SessionTask",
        back_populates="session",
        uselist=False,
        cascade="all, delete-orphan",
    )
    session_validation: Mapped[Optional["SessionValidation"]] = relationship(
        "SessionValidation",
        back_populates="session",
        uselist=False,
        cascade="all, delete-orphan",
    )
    uploaded_files: Mapped[List["UploadedFile"]] = relationship(
        "UploadedFile",
        back_populates="session",
        cascade="all, delete-orphan",
    )

    # Relationships - lazy loading for large collections
    tickets: Mapped[List["Ticket"]] = relationship(
        "Ticket",
        back_populates="session",
        cascade="all, delete-orphan",
        lazy="select",
    )
    session_errors: Mapped[List["SessionError"]] = relationship(
        "SessionError",
        back_populates="session",
        cascade="all, delete-orphan",
        lazy="select",
    )

    def can_transition_to(self, new_stage: SessionStage) -> bool:
        """Check if session can transition to the new stage."""
        current = SessionStage(self.current_stage)
        try:
            current_idx = STAGE_ORDER.index(current)
            new_idx = STAGE_ORDER.index(new_stage)
            # Can only move forward one stage at a time, or stay at same stage
            return new_idx == current_idx + 1 or new_idx == current_idx
        except ValueError:
            return False

    @property
    def is_recoverable(self) -> bool:
        """Check if session can be recovered."""
        return (
            self.status != SessionStatus.COMPLETED.value
            and self.current_stage != SessionStage.COMPLETED.value
        )

    @property
    def stage_display_name(self) -> str:
        """Get human-readable stage name."""
        stage_names = {
            SessionStage.SITE_INFO_COLLECTION.value: "Site Information",
            SessionStage.UPLOAD.value: "File Upload",
            SessionStage.PROCESSING.value: "Processing",
            SessionStage.REVIEW.value: "Review",
            SessionStage.JIRA_EXPORT.value: "Jira Export",
            SessionStage.COMPLETED.value: "Completed",
        }
        return stage_names.get(self.current_stage, self.current_stage)


class SessionTask(Base):
    """Background task execution tracking for sessions."""

    __tablename__ = "session_tasks"
    __table_args__ = (
        UniqueConstraint("session_id", name="uq_session_tasks_session_id"),
    )

    # Primary key is separate UUID for this model
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

    # Task tracking
    task_type: Mapped[str] = mapped_column(String(50), nullable=False)
    task_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50),
        default=TaskStatus.RUNNING.value,
        nullable=False,
    )

    # Timing
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    failed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Retry tracking
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    failure_context: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Relationship
    session: Mapped["Session"] = relationship("Session", back_populates="session_task")

    def can_retry(self) -> bool:
        """Check if task can be retried."""
        return self.status == TaskStatus.FAILED.value and self.retry_count < 3

    def mark_started(self, task_id: UUID) -> None:
        """Set task as running with new task_id."""
        self.task_id = task_id
        self.status = TaskStatus.RUNNING.value
        self.started_at = datetime.utcnow()
        self.completed_at = None
        self.failed_at = None

    def mark_completed(self) -> None:
        """Set task as completed with timestamp."""
        self.status = TaskStatus.COMPLETED.value
        self.completed_at = datetime.utcnow()

    def mark_failed(self, error_context: dict) -> None:
        """Set task as failed with error details."""
        self.status = TaskStatus.FAILED.value
        self.failed_at = datetime.utcnow()
        self.failure_context = error_context
        self.retry_count += 1

    @property
    def is_running(self) -> bool:
        """Check if task is currently running."""
        return self.status == TaskStatus.RUNNING.value

    @property
    def duration_minutes(self) -> Optional[float]:
        """Calculate task duration in minutes."""
        if self.completed_at:
            delta = self.completed_at - self.started_at
            return delta.total_seconds() / 60
        if self.failed_at:
            delta = self.failed_at - self.started_at
            return delta.total_seconds() / 60
        return None

    @property
    def can_be_retried(self) -> bool:
        """Check if task can be retried by user."""
        return self.status == TaskStatus.FAILED.value and self.retry_count < 3


class SessionValidation(Base):
    """ADF validation state tracking for export readiness."""

    __tablename__ = "session_validations"
    __table_args__ = (
        CheckConstraint(
            "validation_passed = false OR validation_status = 'completed'",
            name="ck_validation_passed_only_when_completed",
        ),
    )

    # session_id as primary key (true 1:1 relationship)
    session_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        primary_key=True,
    )

    # Validation state
    validation_status: Mapped[str] = mapped_column(
        String(50),
        default=AdfValidationStatus.PENDING.value,
        nullable=False,
    )
    validation_passed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Timestamps
    last_validated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_invalidated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Results
    validation_results: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Relationship
    session: Mapped["Session"] = relationship(
        "Session",
        back_populates="session_validation",
    )

    def mark_validation_started(self) -> None:
        """Set status to processing and clear previous results."""
        self.validation_status = AdfValidationStatus.PROCESSING.value
        self.validation_results = None

    def mark_validation_completed(self, passed: bool, results: dict) -> None:
        """Set completion status and results."""
        self.validation_status = AdfValidationStatus.COMPLETED.value
        self.validation_passed = passed
        self.last_validated_at = datetime.utcnow()
        self.validation_results = results

    def mark_validation_failed(self, error_context: dict) -> None:
        """Set failed status with error details."""
        self.validation_status = AdfValidationStatus.FAILED.value
        self.validation_passed = False
        self.validation_results = error_context

    def invalidate_validation(self) -> None:
        """Mark validation as invalidated due to ticket edits."""
        self.validation_passed = False
        self.last_invalidated_at = datetime.utcnow()

    @property
    def is_export_ready(self) -> bool:
        """Check if export is ready."""
        return (
            self.validation_status == AdfValidationStatus.COMPLETED.value
            and self.validation_passed
        )

    @property
    def is_invalidated(self) -> bool:
        """Check if validation was invalidated after passing."""
        if not self.last_invalidated_at or not self.last_validated_at:
            return False
        return self.last_invalidated_at > self.last_validated_at

    @property
    def validation_age_minutes(self) -> Optional[float]:
        """Get age of validation in minutes."""
        if not self.last_validated_at:
            return None
        delta = datetime.utcnow() - self.last_validated_at.replace(tzinfo=None)
        return delta.total_seconds() / 60
