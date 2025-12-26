"""UploadedFile model."""

from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import String, Integer, DateTime, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.schemas.base import FileValidationStatus

if TYPE_CHECKING:
    from app.models.session import Session


class UploadedFile(Base):
    """CSV file metadata and parsed content storage."""

    __tablename__ = "uploaded_files"
    __table_args__ = (
        Index("idx_uploaded_files_session_id", "session_id"),
        Index("idx_uploaded_files_csv_type", "csv_type"),
        Index("idx_uploaded_files_validation_status", "validation_status"),
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

    # File metadata
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    csv_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Content
    parsed_content: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # Validation
    validation_status: Mapped[str] = mapped_column(
        String(50),
        default=FileValidationStatus.PENDING.value,
        nullable=False,
    )
    row_count: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamps
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    processed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationship
    session: Mapped["Session"] = relationship("Session", back_populates="uploaded_files")

    def mark_validated(self, is_valid: bool) -> None:
        """Set validation status and processed_at timestamp."""
        self.validation_status = (
            FileValidationStatus.VALID.value
            if is_valid
            else FileValidationStatus.INVALID.value
        )
        self.processed_at = datetime.utcnow()

    def get_csv_headers(self) -> List[str]:
        """Extract column headers from parsed_content."""
        return self.parsed_content.get("headers", [])

    def get_row_data(self) -> List[dict]:
        """Extract row data from parsed_content."""
        return self.parsed_content.get("rows", [])

    @property
    def is_classified(self) -> bool:
        """Check if file has been classified."""
        return self.csv_type is not None

    @property
    def is_valid(self) -> bool:
        """Check if file is valid."""
        return self.validation_status == FileValidationStatus.VALID.value

    @property
    def entity_count(self) -> int:
        """Get number of entities (rows) in this file."""
        return self.row_count

    @property
    def file_size_mb(self) -> float:
        """Get file size in megabytes."""
        return self.file_size_bytes / (1024 * 1024)
