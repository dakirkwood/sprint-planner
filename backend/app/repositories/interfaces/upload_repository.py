# app/repositories/interfaces/upload_repository.py
"""
Upload repository interface.
Repository for UploadedFile model operations.
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict
from uuid import UUID

from app.models.upload import UploadedFile


class UploadRepositoryInterface(ABC):
    """
    Interface for uploaded file repository operations.
    """

    # ==========================================================================
    # File CRUD Operations
    # ==========================================================================

    @abstractmethod
    async def create_file(self, file_data: dict) -> UploadedFile:
        """Create a new uploaded file record."""
        pass

    @abstractmethod
    async def get_file_by_id(self, file_id: UUID) -> Optional[UploadedFile]:
        """Get uploaded file by ID."""
        pass

    @abstractmethod
    async def get_files_by_session(self, session_id: UUID) -> List[UploadedFile]:
        """Get all uploaded files for a session."""
        pass

    @abstractmethod
    async def update_file(self, file_id: UUID, updates: dict) -> UploadedFile:
        """Update uploaded file fields."""
        pass

    @abstractmethod
    async def delete_files_by_session(self, session_id: UUID) -> int:
        """Delete all files for a session. Returns count deleted."""
        pass

    # ==========================================================================
    # Classification Operations
    # ==========================================================================

    @abstractmethod
    async def update_classifications(self, classifications: List[dict]) -> List[UploadedFile]:
        """Update CSV type classifications for multiple files."""
        pass

    @abstractmethod
    async def get_files_by_csv_type(self, session_id: UUID, csv_type: str) -> List[UploadedFile]:
        """Get files of a specific CSV type."""
        pass

    @abstractmethod
    async def get_unclassified_files(self, session_id: UUID) -> List[UploadedFile]:
        """Get files without CSV type classification."""
        pass

    # ==========================================================================
    # Validation Operations
    # ==========================================================================

    @abstractmethod
    async def mark_file_validated(self, file_id: UUID, is_valid: bool) -> None:
        """Mark file as validated or invalid."""
        pass

    @abstractmethod
    async def get_validation_summary(self, session_id: UUID) -> dict:
        """Get validation summary for all files in session."""
        pass

    @abstractmethod
    async def all_files_valid(self, session_id: UUID) -> bool:
        """Check if all files in session are valid."""
        pass

    # ==========================================================================
    # Content Access
    # ==========================================================================

    @abstractmethod
    async def get_parsed_content(self, file_id: UUID) -> Optional[dict]:
        """Get parsed content for a file."""
        pass

    @abstractmethod
    async def get_total_entity_count(self, session_id: UUID) -> int:
        """Get total entity count across all files in session."""
        pass
