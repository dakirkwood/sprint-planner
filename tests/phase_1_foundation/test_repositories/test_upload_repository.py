"""Tests for SQLAlchemy upload repository."""

import pytest
from uuid import uuid4

from app.repositories.sqlalchemy.upload_repository import SQLAlchemyUploadRepository
from app.models.upload import UploadedFile
from app.schemas.base import FileValidationStatus


class TestUploadRepositoryCreate:
    """Test file creation methods."""

    @pytest.mark.asyncio
    async def test_create_file(self, db_session, sample_session, sample_file_data):
        """Create an uploaded file."""
        repo = SQLAlchemyUploadRepository(db_session)
        sample_file_data["session_id"] = sample_session.id

        file = await repo.create_file(sample_file_data)

        assert file.id is not None
        assert file.filename == sample_file_data["filename"]
        assert file.file_size_bytes == sample_file_data["file_size_bytes"]
        assert file.csv_type == sample_file_data["csv_type"]

    @pytest.mark.asyncio
    async def test_create_file_default_validation_status(
        self, db_session, sample_session
    ):
        """Create file with default pending validation status."""
        repo = SQLAlchemyUploadRepository(db_session)

        file = await repo.create_file({
            "session_id": sample_session.id,
            "filename": "test.csv",
            "file_size_bytes": 100,
            "parsed_content": {},
        })

        assert file.validation_status == FileValidationStatus.PENDING.value


class TestUploadRepositoryRead:
    """Test file retrieval methods."""

    @pytest.mark.asyncio
    async def test_get_file_by_id(self, db_session, sample_uploaded_file):
        """Get file by ID."""
        repo = SQLAlchemyUploadRepository(db_session)

        result = await repo.get_file_by_id(sample_uploaded_file.id)

        assert result is not None
        assert result.id == sample_uploaded_file.id

    @pytest.mark.asyncio
    async def test_get_file_by_id_not_found(self, db_session):
        """Get file by non-existent ID."""
        repo = SQLAlchemyUploadRepository(db_session)

        result = await repo.get_file_by_id(uuid4())

        assert result is None

    @pytest.mark.asyncio
    async def test_get_files_by_session(
        self, db_session, sample_session
    ):
        """Get all files for a session."""
        repo = SQLAlchemyUploadRepository(db_session)

        # Create multiple files
        await repo.create_file({
            "session_id": sample_session.id,
            "filename": "file1.csv",
            "file_size_bytes": 100,
            "parsed_content": {},
        })
        await repo.create_file({
            "session_id": sample_session.id,
            "filename": "file2.csv",
            "file_size_bytes": 200,
            "parsed_content": {},
        })

        results = await repo.get_files_by_session(sample_session.id)

        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_get_files_by_csv_type(self, db_session, sample_session):
        """Get files by CSV type."""
        repo = SQLAlchemyUploadRepository(db_session)

        # Create files with different types
        await repo.create_file({
            "session_id": sample_session.id,
            "filename": "bundles.csv",
            "file_size_bytes": 100,
            "parsed_content": {},
            "csv_type": "bundles",
        })
        await repo.create_file({
            "session_id": sample_session.id,
            "filename": "fields.csv",
            "file_size_bytes": 100,
            "parsed_content": {},
            "csv_type": "fields",
        })

        results = await repo.get_files_by_csv_type(sample_session.id, "bundles")

        assert len(results) == 1
        assert results[0].csv_type == "bundles"

    @pytest.mark.asyncio
    async def test_get_unclassified_files(self, db_session, sample_session):
        """Get files without classification."""
        repo = SQLAlchemyUploadRepository(db_session)

        # Create classified and unclassified files
        await repo.create_file({
            "session_id": sample_session.id,
            "filename": "classified.csv",
            "file_size_bytes": 100,
            "parsed_content": {},
            "csv_type": "bundles",
        })
        await repo.create_file({
            "session_id": sample_session.id,
            "filename": "unclassified.csv",
            "file_size_bytes": 100,
            "parsed_content": {},
        })

        results = await repo.get_unclassified_files(sample_session.id)

        assert len(results) == 1
        assert results[0].filename == "unclassified.csv"


class TestUploadRepositoryUpdate:
    """Test file update methods."""

    @pytest.mark.asyncio
    async def test_update_file(self, db_session, sample_uploaded_file):
        """Update file fields."""
        repo = SQLAlchemyUploadRepository(db_session)

        result = await repo.update_file(
            sample_uploaded_file.id,
            {"csv_type": "updated_type", "row_count": 100},
        )

        assert result is not None
        assert result.csv_type == "updated_type"
        assert result.row_count == 100

    @pytest.mark.asyncio
    async def test_update_file_not_found(self, db_session):
        """Update non-existent file."""
        repo = SQLAlchemyUploadRepository(db_session)

        result = await repo.update_file(uuid4(), {"csv_type": "test"})

        assert result is None

    @pytest.mark.asyncio
    async def test_update_classifications(self, db_session, sample_session):
        """Update classifications for multiple files."""
        repo = SQLAlchemyUploadRepository(db_session)

        file1 = await repo.create_file({
            "session_id": sample_session.id,
            "filename": "file1.csv",
            "file_size_bytes": 100,
            "parsed_content": {},
        })
        file2 = await repo.create_file({
            "session_id": sample_session.id,
            "filename": "file2.csv",
            "file_size_bytes": 100,
            "parsed_content": {},
        })

        classifications = [
            {"file_id": file1.id, "csv_type": "bundles"},
            {"file_id": file2.id, "csv_type": "fields"},
        ]
        updated = await repo.update_classifications(classifications)

        assert len(updated) == 2
        assert updated[0].csv_type == "bundles"
        assert updated[1].csv_type == "fields"


class TestUploadRepositoryValidation:
    """Test validation-related methods."""

    @pytest.mark.asyncio
    async def test_mark_file_validated_valid(self, db_session, sample_uploaded_file):
        """Mark file as validated and valid."""
        repo = SQLAlchemyUploadRepository(db_session)

        await repo.mark_file_validated(sample_uploaded_file.id, is_valid=True)

        file = await repo.get_file_by_id(sample_uploaded_file.id)
        assert file.validation_status == FileValidationStatus.VALID.value
        assert file.processed_at is not None

    @pytest.mark.asyncio
    async def test_mark_file_validated_invalid(self, db_session, sample_uploaded_file):
        """Mark file as validated but invalid."""
        repo = SQLAlchemyUploadRepository(db_session)

        await repo.mark_file_validated(sample_uploaded_file.id, is_valid=False)

        file = await repo.get_file_by_id(sample_uploaded_file.id)
        assert file.validation_status == FileValidationStatus.INVALID.value

    @pytest.mark.asyncio
    async def test_get_validation_summary(self, db_session, sample_session):
        """Get validation summary for session."""
        repo = SQLAlchemyUploadRepository(db_session)

        # Create files with different validation statuses
        valid_file = await repo.create_file({
            "session_id": sample_session.id,
            "filename": "valid.csv",
            "file_size_bytes": 100,
            "parsed_content": {},
            "validation_status": FileValidationStatus.VALID.value,
        })
        pending_file = await repo.create_file({
            "session_id": sample_session.id,
            "filename": "pending.csv",
            "file_size_bytes": 100,
            "parsed_content": {},
        })
        invalid_file = await repo.create_file({
            "session_id": sample_session.id,
            "filename": "invalid.csv",
            "file_size_bytes": 100,
            "parsed_content": {},
            "validation_status": FileValidationStatus.INVALID.value,
        })

        summary = await repo.get_validation_summary(sample_session.id)

        assert summary["total"] == 3
        assert summary["valid"] == 1
        assert summary["pending"] == 1
        assert summary["invalid"] == 1

    @pytest.mark.asyncio
    async def test_all_files_valid_true(self, db_session, sample_session):
        """all_files_valid returns True when all files are valid."""
        repo = SQLAlchemyUploadRepository(db_session)

        await repo.create_file({
            "session_id": sample_session.id,
            "filename": "file1.csv",
            "file_size_bytes": 100,
            "parsed_content": {},
            "validation_status": FileValidationStatus.VALID.value,
        })
        await repo.create_file({
            "session_id": sample_session.id,
            "filename": "file2.csv",
            "file_size_bytes": 100,
            "parsed_content": {},
            "validation_status": FileValidationStatus.VALID.value,
        })

        result = await repo.all_files_valid(sample_session.id)

        assert result is True

    @pytest.mark.asyncio
    async def test_all_files_valid_false(self, db_session, sample_session):
        """all_files_valid returns False when not all files are valid."""
        repo = SQLAlchemyUploadRepository(db_session)

        await repo.create_file({
            "session_id": sample_session.id,
            "filename": "valid.csv",
            "file_size_bytes": 100,
            "parsed_content": {},
            "validation_status": FileValidationStatus.VALID.value,
        })
        await repo.create_file({
            "session_id": sample_session.id,
            "filename": "pending.csv",
            "file_size_bytes": 100,
            "parsed_content": {},
        })

        result = await repo.all_files_valid(sample_session.id)

        assert result is False


class TestUploadRepositoryDelete:
    """Test file deletion methods."""

    @pytest.mark.asyncio
    async def test_delete_files_by_session(self, db_session, sample_session):
        """Delete all files for a session."""
        repo = SQLAlchemyUploadRepository(db_session)

        await repo.create_file({
            "session_id": sample_session.id,
            "filename": "file1.csv",
            "file_size_bytes": 100,
            "parsed_content": {},
        })
        await repo.create_file({
            "session_id": sample_session.id,
            "filename": "file2.csv",
            "file_size_bytes": 100,
            "parsed_content": {},
        })

        deleted = await repo.delete_files_by_session(sample_session.id)

        assert deleted == 2

        files = await repo.get_files_by_session(sample_session.id)
        assert len(files) == 0


class TestUploadRepositoryContent:
    """Test content-related methods."""

    @pytest.mark.asyncio
    async def test_get_parsed_content(self, db_session, sample_uploaded_file):
        """Get parsed content for file."""
        repo = SQLAlchemyUploadRepository(db_session)

        content = await repo.get_parsed_content(sample_uploaded_file.id)

        assert content is not None
        assert "headers" in content
        assert "rows" in content

    @pytest.mark.asyncio
    async def test_get_parsed_content_not_found(self, db_session):
        """Get parsed content for non-existent file."""
        repo = SQLAlchemyUploadRepository(db_session)

        content = await repo.get_parsed_content(uuid4())

        assert content is None

    @pytest.mark.asyncio
    async def test_get_total_entity_count(self, db_session, sample_session):
        """Get total entity count across session files."""
        repo = SQLAlchemyUploadRepository(db_session)

        await repo.create_file({
            "session_id": sample_session.id,
            "filename": "file1.csv",
            "file_size_bytes": 100,
            "parsed_content": {},
            "row_count": 10,
        })
        await repo.create_file({
            "session_id": sample_session.id,
            "filename": "file2.csv",
            "file_size_bytes": 100,
            "parsed_content": {},
            "row_count": 15,
        })

        total = await repo.get_total_entity_count(sample_session.id)

        assert total == 25
