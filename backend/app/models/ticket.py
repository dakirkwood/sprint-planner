# app/models/ticket.py
"""
Ticket-related SQLAlchemy models: Ticket, TicketDependency, Attachment.
"""
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING, Any

from sqlalchemy import String, Integer, Boolean, Text, ForeignKey, Index, Enum as SQLEnum, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin, GUIDString
from app.schemas.base import JiraUploadStatus

if TYPE_CHECKING:
    from app.models.session import Session


# Jira character limit for description field
JIRA_DESCRIPTION_LIMIT = 30000


class Ticket(Base, UUIDMixin, TimestampMixin):
    """
    Generated ticket for Jira export.
    Stores content, metadata, and export state.
    """
    __tablename__ = "tickets"
    __table_args__ = (
        Index('idx_tickets_session_id', 'session_id'),
        Index('idx_tickets_entity_group', 'entity_group'),
        Index('idx_tickets_ready_for_jira', 'ready_for_jira'),
    )

    # Parent session
    session_id: Mapped[Any] = mapped_column(
        GUIDString(),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False
    )

    # Content
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    user_notes: Mapped[Optional[str]] = mapped_column(Text)

    # Source tracking
    csv_source_files: Mapped[Optional[List[dict]]] = mapped_column(JSON)

    # Organization
    entity_group: Mapped[str] = mapped_column(String(50), nullable=False)
    user_order: Mapped[int] = mapped_column(Integer, nullable=False)

    # Assignment
    sprint: Mapped[Optional[str]] = mapped_column(String(100))
    assignee: Mapped[Optional[str]] = mapped_column(String(255))

    # Export state
    ready_for_jira: Mapped[bool] = mapped_column(Boolean, default=False)
    jira_ticket_key: Mapped[Optional[str]] = mapped_column(String(50))
    jira_ticket_url: Mapped[Optional[str]] = mapped_column(String(500))

    # Relationships
    session: Mapped["Session"] = relationship("Session", back_populates="tickets")

    # 1:1 relationship to attachment (FK lives on Attachment side)
    attachment: Mapped[Optional["Attachment"]] = relationship(
        "Attachment",
        back_populates="ticket",
        uselist=False,
        cascade="all, delete-orphan"
    )

    # Self-referential dependencies via junction table
    dependencies: Mapped[List["TicketDependency"]] = relationship(
        "TicketDependency",
        foreign_keys="TicketDependency.ticket_id",
        back_populates="dependent_ticket",
        cascade="all, delete-orphan"
    )
    depends_on: Mapped[List["TicketDependency"]] = relationship(
        "TicketDependency",
        foreign_keys="TicketDependency.depends_on_ticket_id",
        back_populates="dependency_ticket",
        cascade="all, delete-orphan"
    )

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
        return self.character_count > JIRA_DESCRIPTION_LIMIT

    @property
    def has_attachment(self) -> bool:
        """Check if ticket has an attachment."""
        return self.attachment is not None

    @property
    def csv_source_summary(self) -> str:
        """Human-readable CSV source description for UI."""
        if not self.csv_source_files:
            return "No source files"

        files = [ref.get("filename", "Unknown") for ref in self.csv_source_files]
        if len(files) == 1:
            return files[0]
        return f"{files[0]} and {len(files) - 1} more"

    def mark_ready_for_jira(self) -> None:
        """Mark ticket as ready for Jira export."""
        self.ready_for_jira = True

    def add_csv_source_reference(self, filename: str, rows: List[int]) -> None:
        """Add or update CSV source tracking."""
        if self.csv_source_files is None:
            self.csv_source_files = []

        # Update existing or add new
        for ref in self.csv_source_files:
            if ref.get("filename") == filename:
                existing_rows = set(ref.get("rows", []))
                existing_rows.update(rows)
                ref["rows"] = sorted(list(existing_rows))
                return

        self.csv_source_files.append({"filename": filename, "rows": rows})

    def set_jira_export_data(self, jira_key: str, jira_url: str) -> None:
        """Store Jira ticket information after successful export."""
        self.jira_ticket_key = jira_key
        self.jira_ticket_url = jira_url

    def to_dict(self) -> dict:
        """Serialize ticket to dictionary."""
        return {
            "id": str(self.id),
            "session_id": str(self.session_id),
            "title": self.title,
            "description": self.description,
            "user_notes": self.user_notes,
            "csv_source_files": self.csv_source_files,
            "entity_group": self.entity_group,
            "user_order": self.user_order,
            "sprint": self.sprint,
            "assignee": self.assignee,
            "ready_for_jira": self.ready_for_jira,
            "jira_ticket_key": self.jira_ticket_key,
            "jira_ticket_url": self.jira_ticket_url,
            "character_count": self.character_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class TicketDependency(Base):
    """
    Junction table for ticket dependencies.
    Tracks which tickets depend on other tickets.
    """
    __tablename__ = "ticket_dependencies"
    __table_args__ = (
        Index('idx_ticket_dependencies_ticket_id', 'ticket_id'),
        Index('idx_ticket_dependencies_depends_on', 'depends_on_ticket_id'),
    )

    # Composite primary key
    ticket_id: Mapped[Any] = mapped_column(
        GUIDString(),
        ForeignKey("tickets.id", ondelete="CASCADE"),
        primary_key=True
    )
    depends_on_ticket_id: Mapped[Any] = mapped_column(
        GUIDString(),
        ForeignKey("tickets.id", ondelete="CASCADE"),
        primary_key=True
    )

    # Relationships
    dependent_ticket: Mapped["Ticket"] = relationship(
        "Ticket",
        foreign_keys=[ticket_id],
        back_populates="dependencies"
    )
    dependency_ticket: Mapped["Ticket"] = relationship(
        "Ticket",
        foreign_keys=[depends_on_ticket_id],
        back_populates="depends_on"
    )


class Attachment(Base, UUIDMixin, TimestampMixin):
    """
    File attachment for large ticket descriptions.
    Used when description exceeds Jira character limits.
    """
    __tablename__ = "attachments"
    __table_args__ = (
        Index('idx_attachments_ticket_id', 'ticket_id'),
    )

    # Parent ticket (unique enforces 1:1)
    ticket_id: Mapped[Any] = mapped_column(
        GUIDString(),
        ForeignKey("tickets.id", ondelete="CASCADE"),
        nullable=False,
        unique=True
    )

    # File information
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)

    # Upload state
    upload_status: Mapped[JiraUploadStatus] = mapped_column(
        SQLEnum(JiraUploadStatus, native_enum=False, length=50),
        default=JiraUploadStatus.PENDING
    )
    jira_attachment_id: Mapped[Optional[str]] = mapped_column(String(100))

    # Relationship
    ticket: Mapped["Ticket"] = relationship("Ticket", back_populates="attachment")

    def to_dict(self) -> dict:
        """Serialize attachment to dictionary."""
        return {
            "id": str(self.id),
            "ticket_id": str(self.ticket_id),
            "filename": self.filename,
            "content_type": self.content_type,
            "file_size": self.file_size,
            "upload_status": self.upload_status.value,
            "jira_attachment_id": self.jira_attachment_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
