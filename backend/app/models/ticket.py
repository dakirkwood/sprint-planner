"""Ticket, TicketDependency, and Attachment models."""

from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    String,
    Text,
    Integer,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    PrimaryKeyConstraint,
    CheckConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.schemas.base import JiraUploadStatus

if TYPE_CHECKING:
    from app.models.session import Session


class Ticket(Base, TimestampMixin):
    """Generated ticket content and metadata for Jira export."""

    __tablename__ = "tickets"
    __table_args__ = (
        Index("idx_tickets_session_id", "session_id"),
        Index("idx_tickets_entity_group", "entity_group"),
        Index("idx_tickets_ready_for_jira", "ready_for_jira"),
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

    # Content
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    csv_source_files: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # Organization
    entity_group: Mapped[str] = mapped_column(String(100), nullable=False)
    user_order: Mapped[int] = mapped_column(Integer, default=0)

    # Review state
    ready_for_jira: Mapped[bool] = mapped_column(Boolean, default=False)
    sprint: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    assignee: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    user_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Jira export tracking
    jira_ticket_key: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    jira_ticket_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Relationships
    session: Mapped["Session"] = relationship("Session", back_populates="tickets")

    # 1:1 relationship to attachment (FK lives on Attachment side)
    attachment: Mapped[Optional["Attachment"]] = relationship(
        "Attachment",
        back_populates="ticket",
        uselist=False,
        cascade="all, delete-orphan",
    )

    # Self-referential dependencies via junction table
    dependencies: Mapped[List["TicketDependency"]] = relationship(
        "TicketDependency",
        foreign_keys="TicketDependency.ticket_id",
        back_populates="dependent_ticket",
        cascade="all, delete-orphan",
    )
    depends_on: Mapped[List["TicketDependency"]] = relationship(
        "TicketDependency",
        foreign_keys="TicketDependency.depends_on_ticket_id",
        back_populates="dependency_ticket",
        cascade="all, delete-orphan",
    )

    def mark_ready_for_jira(self) -> None:
        """Set ready_for_jira flag."""
        self.ready_for_jira = True

    def add_csv_source_reference(self, filename: str, rows: List[int]) -> None:
        """Add or update CSV source tracking."""
        if self.csv_source_files is None:
            self.csv_source_files = []
        # Check if filename already exists
        for ref in self.csv_source_files:
            if ref.get("filename") == filename:
                existing_rows = set(ref.get("rows", []))
                existing_rows.update(rows)
                ref["rows"] = sorted(list(existing_rows))
                return
        # Add new reference
        self.csv_source_files.append({"filename": filename, "rows": rows})

    def set_jira_export_data(self, jira_key: str, jira_url: str) -> None:
        """Store Jira ticket information after successful export."""
        self.jira_ticket_key = jira_key
        self.jira_ticket_url = jira_url

    @property
    def character_count(self) -> int:
        """Get description length for attachment threshold checking."""
        return len(self.description) if self.description else 0

    @property
    def is_exported(self) -> bool:
        """Check if ticket has been exported to Jira."""
        return self.jira_ticket_key is not None

    @property
    def needs_attachment(self) -> bool:
        """Check if description exceeds Jira character limits."""
        return self.character_count > 30000

    @property
    def has_attachment(self) -> bool:
        """Check if ticket has an attachment."""
        return self.attachment is not None

    @property
    def csv_source_summary(self) -> str:
        """Get human-readable CSV source description."""
        if not self.csv_source_files:
            return "No sources"
        sources = []
        for ref in self.csv_source_files:
            filename = ref.get("filename", "unknown")
            rows = ref.get("rows", [])
            if len(rows) == 1:
                sources.append(f"{filename}:row {rows[0]}")
            else:
                sources.append(f"{filename}:rows {min(rows)}-{max(rows)}")
        return ", ".join(sources)


class TicketDependency(Base):
    """Ticket relationship tracking for implementation ordering."""

    __tablename__ = "ticket_dependencies"
    __table_args__ = (
        PrimaryKeyConstraint("ticket_id", "depends_on_ticket_id"),
        CheckConstraint(
            "ticket_id != depends_on_ticket_id",
            name="ck_no_self_dependency",
        ),
        Index("idx_ticket_dependencies_ticket_id", "ticket_id"),
        Index("idx_ticket_dependencies_depends_on", "depends_on_ticket_id"),
    )

    # Composite primary key
    ticket_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tickets.id", ondelete="CASCADE"),
        nullable=False,
    )
    depends_on_ticket_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tickets.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    dependent_ticket: Mapped["Ticket"] = relationship(
        "Ticket",
        foreign_keys=[ticket_id],
        back_populates="dependencies",
    )
    dependency_ticket: Mapped["Ticket"] = relationship(
        "Ticket",
        foreign_keys=[depends_on_ticket_id],
        back_populates="depends_on",
    )


class Attachment(Base):
    """Auto-generated attachments for oversized ticket content."""

    __tablename__ = "attachments"
    __table_args__ = (
        Index("idx_attachments_session_id", "session_id"),
        Index("idx_attachments_ticket_id", "ticket_id"),
        Index("idx_attachments_jira_upload_status", "jira_upload_status"),
    )

    # Primary key
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    # Foreign keys
    session_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    ticket_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tickets.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # Enforces 1:1 relationship
    )

    # File metadata
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)

    # Jira upload tracking
    jira_attachment_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    jira_upload_status: Mapped[str] = mapped_column(
        String(50),
        default=JiraUploadStatus.PENDING.value,
        nullable=False,
    )

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationship
    ticket: Mapped["Ticket"] = relationship("Ticket", back_populates="attachment")

    def mark_uploaded_to_jira(self, jira_attachment_id: str) -> None:
        """Set upload status and Jira reference after successful upload."""
        self.jira_upload_status = JiraUploadStatus.UPLOADED.value
        self.jira_attachment_id = jira_attachment_id

    def mark_upload_failed(self) -> None:
        """Set failed status, clear any partial Jira references."""
        self.jira_upload_status = JiraUploadStatus.FAILED.value
        self.jira_attachment_id = None

    @property
    def file_size_kb(self) -> float:
        """Get file size in kilobytes."""
        return self.file_size_bytes / 1024

    @property
    def is_uploaded_to_jira(self) -> bool:
        """Check if successfully uploaded to Jira."""
        return self.jira_upload_status == JiraUploadStatus.UPLOADED.value

    @property
    def content_preview(self) -> str:
        """Get first 200 characters of content for UI preview."""
        if not self.content:
            return ""
        return self.content[:200] + ("..." if len(self.content) > 200 else "")
