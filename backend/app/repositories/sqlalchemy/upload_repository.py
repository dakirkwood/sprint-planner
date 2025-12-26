"""SQLAlchemy implementation of upload repository."""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, delete, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.upload import UploadedFile
from app.repositories.interfaces.upload_repository import UploadRepositoryInterface
from app.schemas.base import FileValidationStatus


class SQLAlchemyUploadRepository(UploadRepositoryInterface):
    """SQLAlchemy implementation of upload repository."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def create_file(self, file_data: dict) -> UploadedFile:
        """Create a new uploaded file record."""
        uploaded_file = UploadedFile(
            session_id=file_data["session_id"],
            filename=file_data["filename"],
            file_size_bytes=file_data["file_size_bytes"],
            csv_type=file_data.get("csv_type"),
            parsed_content=file_data["parsed_content"],
            row_count=file_data.get("row_count", 0),
            validation_status=file_data.get(
                "validation_status",
                FileValidationStatus.PENDING.value,
            ),
        )
        self.db.add(uploaded_file)
        await self.db.flush()
        return uploaded_file

    async def get_file_by_id(self, file_id: UUID) -> Optional[UploadedFile]:
        """Get file by ID."""
        stmt = select(UploadedFile).where(UploadedFile.id == file_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_files_by_session(self, session_id: UUID) -> List[UploadedFile]:
        """Get all files for a session."""
        stmt = (
            select(UploadedFile)
            .where(UploadedFile.session_id == session_id)
            .order_by(UploadedFile.uploaded_at)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update_file(
        self,
        file_id: UUID,
        updates: dict,
    ) -> Optional[UploadedFile]:
        """Update file fields."""
        uploaded_file = await self.get_file_by_id(file_id)
        if not uploaded_file:
            return None

        for key, value in updates.items():
            if hasattr(uploaded_file, key):
                setattr(uploaded_file, key, value)

        await self.db.flush()
        return uploaded_file

    async def delete_files_by_session(self, session_id: UUID) -> int:
        """Delete all files for a session."""
        stmt = delete(UploadedFile).where(UploadedFile.session_id == session_id)
        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.rowcount

    async def update_classifications(
        self,
        classifications: List[dict],
    ) -> List[UploadedFile]:
        """Update classifications for multiple files."""
        updated_files = []
        for classification in classifications:
            file_id = classification["file_id"]
            csv_type = classification["csv_type"]

            uploaded_file = await self.get_file_by_id(file_id)
            if uploaded_file:
                uploaded_file.csv_type = csv_type
                updated_files.append(uploaded_file)

        await self.db.flush()
        return updated_files

    async def get_files_by_csv_type(
        self,
        session_id: UUID,
        csv_type: str,
    ) -> List[UploadedFile]:
        """Get all files of a specific CSV type for session."""
        stmt = (
            select(UploadedFile)
            .where(
                UploadedFile.session_id == session_id,
                UploadedFile.csv_type == csv_type,
            )
            .order_by(UploadedFile.uploaded_at)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_unclassified_files(self, session_id: UUID) -> List[UploadedFile]:
        """Get all files without a classification."""
        stmt = (
            select(UploadedFile)
            .where(
                UploadedFile.session_id == session_id,
                UploadedFile.csv_type.is_(None),
            )
            .order_by(UploadedFile.uploaded_at)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def mark_file_validated(self, file_id: UUID, is_valid: bool) -> None:
        """Mark file as validated or invalid."""
        uploaded_file = await self.get_file_by_id(file_id)
        if uploaded_file:
            uploaded_file.mark_validated(is_valid)
            await self.db.flush()

    async def get_validation_summary(self, session_id: UUID) -> dict:
        """Get validation summary for session."""
        files = await self.get_files_by_session(session_id)

        pending = sum(
            1
            for f in files
            if f.validation_status == FileValidationStatus.PENDING.value
        )
        valid = sum(
            1
            for f in files
            if f.validation_status == FileValidationStatus.VALID.value
        )
        invalid = sum(
            1
            for f in files
            if f.validation_status == FileValidationStatus.INVALID.value
        )

        return {
            "total": len(files),
            "pending": pending,
            "valid": valid,
            "invalid": invalid,
        }

    async def all_files_valid(self, session_id: UUID) -> bool:
        """Check if all files in session are valid."""
        summary = await self.get_validation_summary(session_id)
        return summary["total"] > 0 and summary["valid"] == summary["total"]

    async def get_parsed_content(self, file_id: UUID) -> Optional[dict]:
        """Get parsed content for a file."""
        uploaded_file = await self.get_file_by_id(file_id)
        return uploaded_file.parsed_content if uploaded_file else None

    async def get_total_entity_count(self, session_id: UUID) -> int:
        """Get total entity count across all files in session."""
        stmt = select(func.sum(UploadedFile.row_count)).where(
            UploadedFile.session_id == session_id
        )
        result = await self.db.execute(stmt)
        total = result.scalar_one_or_none()
        return total or 0
