# app/repositories/sqlalchemy/upload_repository.py
"""
SQLAlchemy implementation of UploadRepositoryInterface.
"""
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.upload import UploadedFile
from app.repositories.interfaces.upload_repository import UploadRepositoryInterface
from app.schemas.base import FileValidationStatus


class SQLAlchemyUploadRepository(UploadRepositoryInterface):
    """
    SQLAlchemy implementation for upload repository operations.
    """

    def __init__(self, session: AsyncSession):
        self._session = session

    # ==========================================================================
    # File CRUD Operations
    # ==========================================================================

    async def create_file(self, file_data: dict) -> UploadedFile:
        """Create a new uploaded file record."""
        uploaded_file = UploadedFile(**file_data)
        self._session.add(uploaded_file)
        await self._session.flush()
        return uploaded_file

    async def get_file_by_id(self, file_id: UUID) -> Optional[UploadedFile]:
        """Get uploaded file by ID."""
        stmt = select(UploadedFile).where(UploadedFile.id == file_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_files_by_session(self, session_id: UUID) -> List[UploadedFile]:
        """Get all uploaded files for a session."""
        stmt = (
            select(UploadedFile)
            .where(UploadedFile.session_id == session_id)
            .order_by(UploadedFile.created_at)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update_file(self, file_id: UUID, updates: dict) -> UploadedFile:
        """Update uploaded file fields."""
        uploaded_file = await self.get_file_by_id(file_id)
        if uploaded_file is None:
            raise ValueError(f"UploadedFile not found: {file_id}")

        for key, value in updates.items():
            if hasattr(uploaded_file, key):
                setattr(uploaded_file, key, value)

        await self._session.flush()
        return uploaded_file

    async def delete_files_by_session(self, session_id: UUID) -> int:
        """Delete all files for a session. Returns count deleted."""
        stmt = delete(UploadedFile).where(UploadedFile.session_id == session_id)
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount

    # ==========================================================================
    # Classification Operations
    # ==========================================================================

    async def update_classifications(self, classifications: List[dict]) -> List[UploadedFile]:
        """Update CSV type classifications for multiple files."""
        updated_files = []
        for classification in classifications:
            file_id = classification.get("file_id")
            csv_type = classification.get("csv_type")

            if file_id:
                file = await self.get_file_by_id(file_id)
                if file:
                    file.csv_type = csv_type
                    updated_files.append(file)

        await self._session.flush()
        return updated_files

    async def get_files_by_csv_type(self, session_id: UUID, csv_type: str) -> List[UploadedFile]:
        """Get files of a specific CSV type."""
        stmt = (
            select(UploadedFile)
            .where(UploadedFile.session_id == session_id)
            .where(UploadedFile.csv_type == csv_type)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_unclassified_files(self, session_id: UUID) -> List[UploadedFile]:
        """Get files without CSV type classification."""
        stmt = (
            select(UploadedFile)
            .where(UploadedFile.session_id == session_id)
            .where(UploadedFile.csv_type.is_(None))
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    # ==========================================================================
    # Validation Operations
    # ==========================================================================

    async def mark_file_validated(self, file_id: UUID, is_valid: bool) -> None:
        """Mark file as validated or invalid."""
        uploaded_file = await self.get_file_by_id(file_id)
        if uploaded_file:
            uploaded_file.validation_status = (
                FileValidationStatus.VALID if is_valid else FileValidationStatus.INVALID
            )
            await self._session.flush()

    async def get_validation_summary(self, session_id: UUID) -> dict:
        """Get validation summary for all files in session."""
        files = await self.get_files_by_session(session_id)

        summary = {
            "total": len(files),
            "pending": 0,
            "valid": 0,
            "invalid": 0
        }

        for file in files:
            if file.validation_status == FileValidationStatus.PENDING:
                summary["pending"] += 1
            elif file.validation_status == FileValidationStatus.VALID:
                summary["valid"] += 1
            elif file.validation_status == FileValidationStatus.INVALID:
                summary["invalid"] += 1

        return summary

    async def all_files_valid(self, session_id: UUID) -> bool:
        """Check if all files in session are valid."""
        files = await self.get_files_by_session(session_id)
        if not files:
            return False
        return all(f.validation_status == FileValidationStatus.VALID for f in files)

    # ==========================================================================
    # Content Access
    # ==========================================================================

    async def get_parsed_content(self, file_id: UUID) -> Optional[dict]:
        """Get parsed content for a file."""
        uploaded_file = await self.get_file_by_id(file_id)
        return uploaded_file.parsed_content if uploaded_file else None

    async def get_total_entity_count(self, session_id: UUID) -> int:
        """Get total entity count across all files in session."""
        stmt = (
            select(func.sum(UploadedFile.entity_count))
            .where(UploadedFile.session_id == session_id)
        )
        result = await self._session.execute(stmt)
        total = result.scalar()
        return total or 0
