# tests/backend/unit/test_repositories/test_upload_repository.py
"""
Tests for UploadRepository operations.
"""
import pytest
from uuid import uuid4

from app.models.session import Session
from app.repositories.sqlalchemy.upload_repository import SQLAlchemyUploadRepository
from app.schemas.base import FileValidationStatus


@pytest.mark.phase1
@pytest.mark.repositories
class TestUploadRepositoryCRUD:
    """Test basic CRUD operations."""

    @pytest.fixture
    async def session_id(self, db_session, sample_session_data):
        session = Session(**sample_session_data)
        db_session.add(session)
        await db_session.flush()
        return session.id

    @pytest.fixture
    def repo(self, db_session):
        return SQLAlchemyUploadRepository(db_session)

    @pytest.mark.asyncio
    async def test_create_file(self, repo, session_id, sample_uploaded_file_data):
        """Should create uploaded file record."""
        file_data = {**sample_uploaded_file_data, "session_id": session_id}
        uploaded_file = await repo.create_file(file_data)

        assert uploaded_file.id is not None
        assert uploaded_file.original_filename == sample_uploaded_file_data["original_filename"]

    @pytest.mark.asyncio
    async def test_get_file_by_id(self, repo, session_id, sample_uploaded_file_data):
        """Should retrieve file by ID."""
        file_data = {**sample_uploaded_file_data, "session_id": session_id}
        created = await repo.create_file(file_data)

        retrieved = await repo.get_file_by_id(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id

    @pytest.mark.asyncio
    async def test_get_files_by_session(self, repo, session_id, sample_uploaded_file_data):
        """Should get all files for a session."""
        await repo.create_file({**sample_uploaded_file_data, "session_id": session_id, "stored_filename": "file1.csv"})
        await repo.create_file({**sample_uploaded_file_data, "session_id": session_id, "stored_filename": "file2.csv"})

        files = await repo.get_files_by_session(session_id)

        assert len(files) == 2


@pytest.mark.phase1
@pytest.mark.repositories
class TestUploadRepositoryClassification:
    """Test classification operations."""

    @pytest.fixture
    async def session_id(self, db_session, sample_session_data):
        session = Session(**sample_session_data)
        db_session.add(session)
        await db_session.flush()
        return session.id

    @pytest.fixture
    def repo(self, db_session):
        return SQLAlchemyUploadRepository(db_session)

    @pytest.mark.asyncio
    async def test_get_files_by_csv_type(self, repo, session_id, sample_uploaded_file_data):
        """Should get files by CSV type."""
        await repo.create_file({**sample_uploaded_file_data, "session_id": session_id, "stored_filename": "f1.csv", "csv_type": "bundles"})
        await repo.create_file({**sample_uploaded_file_data, "session_id": session_id, "stored_filename": "f2.csv", "csv_type": "fields"})

        bundles = await repo.get_files_by_csv_type(session_id, "bundles")

        assert len(bundles) == 1
        assert bundles[0].csv_type == "bundles"

    @pytest.mark.asyncio
    async def test_get_unclassified_files(self, repo, session_id, sample_uploaded_file_data):
        """Should get files without classification."""
        await repo.create_file({**sample_uploaded_file_data, "session_id": session_id, "stored_filename": "f1.csv", "csv_type": "bundles"})
        await repo.create_file({**sample_uploaded_file_data, "session_id": session_id, "stored_filename": "f2.csv", "csv_type": None})

        unclassified = await repo.get_unclassified_files(session_id)

        assert len(unclassified) == 1
        assert unclassified[0].csv_type is None


@pytest.mark.phase1
@pytest.mark.repositories
class TestUploadRepositoryValidation:
    """Test validation operations."""

    @pytest.fixture
    async def session_id(self, db_session, sample_session_data):
        session = Session(**sample_session_data)
        db_session.add(session)
        await db_session.flush()
        return session.id

    @pytest.fixture
    def repo(self, db_session):
        return SQLAlchemyUploadRepository(db_session)

    @pytest.mark.asyncio
    async def test_mark_file_validated(self, repo, session_id, sample_uploaded_file_data):
        """Should mark file as validated."""
        uploaded_file = await repo.create_file({**sample_uploaded_file_data, "session_id": session_id})

        await repo.mark_file_validated(uploaded_file.id, is_valid=True)

        retrieved = await repo.get_file_by_id(uploaded_file.id)
        assert retrieved.validation_status == FileValidationStatus.VALID

    @pytest.mark.asyncio
    async def test_mark_file_invalid(self, repo, session_id, sample_uploaded_file_data):
        """Should mark file as invalid."""
        uploaded_file = await repo.create_file({**sample_uploaded_file_data, "session_id": session_id})

        await repo.mark_file_validated(uploaded_file.id, is_valid=False)

        retrieved = await repo.get_file_by_id(uploaded_file.id)
        assert retrieved.validation_status == FileValidationStatus.INVALID

    @pytest.mark.asyncio
    async def test_get_validation_summary(self, repo, session_id, sample_uploaded_file_data):
        """Should get validation summary for session."""
        f1 = await repo.create_file({**sample_uploaded_file_data, "session_id": session_id, "stored_filename": "f1.csv"})
        f2 = await repo.create_file({**sample_uploaded_file_data, "session_id": session_id, "stored_filename": "f2.csv"})

        await repo.mark_file_validated(f1.id, is_valid=True)
        await repo.mark_file_validated(f2.id, is_valid=False)

        summary = await repo.get_validation_summary(session_id)

        assert summary["total"] == 2
        assert summary["valid"] == 1
        assert summary["invalid"] == 1

    @pytest.mark.asyncio
    async def test_all_files_valid(self, repo, session_id, sample_uploaded_file_data):
        """Should check if all files are valid."""
        f1 = await repo.create_file({**sample_uploaded_file_data, "session_id": session_id, "stored_filename": "f1.csv"})
        f2 = await repo.create_file({**sample_uploaded_file_data, "session_id": session_id, "stored_filename": "f2.csv"})

        # Not all valid yet
        await repo.mark_file_validated(f1.id, is_valid=True)
        assert await repo.all_files_valid(session_id) is False

        # Now all valid
        await repo.mark_file_validated(f2.id, is_valid=True)
        assert await repo.all_files_valid(session_id) is True


@pytest.mark.phase1
@pytest.mark.repositories
class TestUploadRepositoryContent:
    """Test content access operations."""

    @pytest.fixture
    async def session_id(self, db_session, sample_session_data):
        session = Session(**sample_session_data)
        db_session.add(session)
        await db_session.flush()
        return session.id

    @pytest.fixture
    def repo(self, db_session):
        return SQLAlchemyUploadRepository(db_session)

    @pytest.mark.asyncio
    async def test_get_total_entity_count(self, repo, session_id, sample_uploaded_file_data):
        """Should get total entity count across files."""
        await repo.create_file({**sample_uploaded_file_data, "session_id": session_id, "stored_filename": "f1.csv", "entity_count": 10})
        await repo.create_file({**sample_uploaded_file_data, "session_id": session_id, "stored_filename": "f2.csv", "entity_count": 15})

        total = await repo.get_total_entity_count(session_id)

        assert total == 25
