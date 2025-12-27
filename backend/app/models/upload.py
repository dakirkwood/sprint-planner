# app/models/upload.py
"""
Upload-related SQLAlchemy model: UploadedFile.
"""
from datetime import datetime
from typing import Optional, TYPE_CHECKING, Any

from sqlalchemy import String, Integer, DateTime, ForeignKey, Index, Enum as SQLEnum, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin, GUIDString
from app.schemas.base import FileValidationStatus

if TYPE_CHECKING:
    from app.models.session import Session


class UploadedFile(Base, UUIDMixin, TimestampMixin):
    """
    Uploaded CSV file tracking model.
    Stores metadata and parsed content for uploaded files.
    """
    __tablename__ = "uploaded_files"
    __table_args__ = (
        Index('idx_uploaded_files_session_id', 'session_id'),
        Index('idx_uploaded_files_csv_type', 'csv_type'),
        Index('idx_uploaded_files_validation_status', 'validation_status'),
    )

    # Parent session
    session_id: Mapped[Any] = mapped_column(
        GUIDString(),
        ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False
    )

    # File metadata
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)

    # Classification
    csv_type: Mapped[Optional[str]] = mapped_column(String(100))
    entity_count: Mapped[int] = mapped_column(Integer, default=0)

    # Validation
    validation_status: Mapped[FileValidationStatus] = mapped_column(
        SQLEnum(FileValidationStatus, native_enum=False, length=50),
        default=FileValidationStatus.PENDING
    )
    validation_errors: Mapped[Optional[dict]] = mapped_column(JSON)

    # Parsed content
    parsed_content: Mapped[Optional[dict]] = mapped_column(JSON)

    # Relationship
    session: Mapped["Session"] = relationship("Session", back_populates="uploaded_files")

    def to_dict(self) -> dict:
        """Serialize uploaded file to dictionary."""
        return {
            "id": str(self.id),
            "session_id": str(self.session_id),
            "original_filename": self.original_filename,
            "stored_filename": self.stored_filename,
            "file_size": self.file_size,
            "mime_type": self.mime_type,
            "csv_type": self.csv_type,
            "entity_count": self.entity_count,
            "validation_status": self.validation_status.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
