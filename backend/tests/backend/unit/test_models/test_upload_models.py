# tests/backend/unit/test_models/test_upload_models.py
"""
Tests for UploadedFile model.
"""
import pytest
from sqlalchemy import inspect

from app.models.upload import UploadedFile
from app.models.session import Session
from app.schemas.base import FileValidationStatus


@pytest.mark.phase1
@pytest.mark.models
class TestUploadedFileModel:
    """Test UploadedFile model field definitions."""

    def test_uploaded_file_has_required_fields(self):
        """UploadedFile must have all specified fields."""
        mapper = inspect(UploadedFile)
        columns = {c.key for c in mapper.columns}

        required_fields = {
            'id', 'session_id', 'original_filename', 'stored_filename',
            'file_size', 'mime_type', 'csv_type', 'entity_count',
            'validation_status', 'validation_errors', 'parsed_content',
            'created_at', 'updated_at'
        }
        assert required_fields.issubset(columns)

    def test_uploaded_file_has_session_relationship(self):
        """UploadedFile should have relationship to Session."""
        mapper = inspect(UploadedFile)
        relationships = {r.key for r in mapper.relationships}

        assert 'session' in relationships

    @pytest.mark.asyncio
    async def test_uploaded_file_default_validation_status(self, db_session, sample_session_data, sample_uploaded_file_data):
        """validation_status should default to PENDING."""
        session = Session(**sample_session_data)
        db_session.add(session)
        await db_session.flush()

        uploaded_file = UploadedFile(session_id=session.id, **sample_uploaded_file_data)
        db_session.add(uploaded_file)
        await db_session.flush()

        assert uploaded_file.validation_status == FileValidationStatus.PENDING

    @pytest.mark.asyncio
    async def test_uploaded_file_default_entity_count(self, db_session, sample_session_data):
        """entity_count should default to 0."""
        session = Session(**sample_session_data)
        db_session.add(session)
        await db_session.flush()

        file_data = {
            "original_filename": "test.csv",
            "stored_filename": "stored_test.csv",
            "file_size": 100,
            "mime_type": "text/csv"
        }
        uploaded_file = UploadedFile(session_id=session.id, **file_data)
        db_session.add(uploaded_file)
        await db_session.flush()

        assert uploaded_file.entity_count == 0

    @pytest.mark.asyncio
    async def test_uploaded_file_to_dict(self, db_session, sample_session_data, sample_uploaded_file_data):
        """to_dict should serialize all expected fields."""
        session = Session(**sample_session_data)
        db_session.add(session)
        await db_session.flush()

        uploaded_file = UploadedFile(session_id=session.id, **sample_uploaded_file_data)
        db_session.add(uploaded_file)
        await db_session.flush()

        file_dict = uploaded_file.to_dict()

        assert "id" in file_dict
        assert file_dict["original_filename"] == sample_uploaded_file_data["original_filename"]
        assert file_dict["validation_status"] == FileValidationStatus.PENDING.value

    def test_file_validation_status_enum_values(self):
        """FileValidationStatus enum must have expected values."""
        expected = {'pending', 'valid', 'invalid'}
        actual = {e.value for e in FileValidationStatus}

        assert expected == actual
