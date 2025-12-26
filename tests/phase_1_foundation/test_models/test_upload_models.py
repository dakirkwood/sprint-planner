"""Tests for UploadedFile model."""

import pytest
from uuid import UUID, uuid4
from sqlalchemy import inspect

from app.models.upload import UploadedFile
from app.schemas.base import FileValidationStatus


class TestUploadedFileModel:
    """Test UploadedFile model field definitions."""

    def test_uploaded_file_has_required_fields(self):
        """UploadedFile must have all 10 specified fields."""
        mapper = inspect(UploadedFile)
        columns = {c.key for c in mapper.columns}

        required_fields = {
            "id",
            "session_id",
            "filename",
            "file_size_bytes",
            "csv_type",
            "parsed_content",
            "validation_status",
            "row_count",
            "uploaded_at",
            "processed_at",
        }
        assert required_fields.issubset(columns)

    def test_file_validation_status_enum_values(self):
        """FileValidationStatus enum must have expected values."""
        expected = {"pending", "valid", "invalid"}
        actual = {e.value for e in FileValidationStatus}

        assert expected == actual

    @pytest.mark.asyncio
    async def test_uploaded_file_defaults(self, db_session, sample_session, sample_file_data):
        """UploadedFile should have correct defaults."""
        uploaded_file = UploadedFile(
            session_id=sample_session.id,
            **sample_file_data,
        )
        db_session.add(uploaded_file)
        await db_session.flush()

        assert uploaded_file.id is not None
        assert isinstance(uploaded_file.id, UUID)

    @pytest.mark.asyncio
    async def test_validation_status_defaults_to_pending(
        self, db_session, sample_session
    ):
        """validation_status should default to pending."""
        uploaded_file = UploadedFile(
            session_id=sample_session.id,
            filename="test.csv",
            file_size_bytes=100,
            parsed_content={"headers": [], "rows": []},
            row_count=0,
        )
        db_session.add(uploaded_file)
        await db_session.flush()

        assert uploaded_file.validation_status == FileValidationStatus.PENDING.value

    def test_mark_validated_valid(self):
        """mark_validated sets status to valid."""
        uploaded_file = UploadedFile(
            session_id=uuid4(),
            filename="test.csv",
            file_size_bytes=100,
            parsed_content={"headers": [], "rows": []},
            row_count=0,
        )
        uploaded_file.mark_validated(is_valid=True)

        assert uploaded_file.validation_status == FileValidationStatus.VALID.value
        assert uploaded_file.processed_at is not None

    def test_mark_validated_invalid(self):
        """mark_validated sets status to invalid."""
        uploaded_file = UploadedFile(
            session_id=uuid4(),
            filename="test.csv",
            file_size_bytes=100,
            parsed_content={"headers": [], "rows": []},
            row_count=0,
        )
        uploaded_file.mark_validated(is_valid=False)

        assert uploaded_file.validation_status == FileValidationStatus.INVALID.value
        assert uploaded_file.processed_at is not None

    def test_get_csv_headers(self):
        """get_csv_headers returns headers from parsed_content."""
        uploaded_file = UploadedFile(
            session_id=uuid4(),
            filename="test.csv",
            file_size_bytes=100,
            parsed_content={"headers": ["id", "name", "type"], "rows": []},
            row_count=0,
        )
        headers = uploaded_file.get_csv_headers()

        assert headers == ["id", "name", "type"]

    def test_get_row_data(self):
        """get_row_data returns rows from parsed_content."""
        rows = [{"id": "1", "name": "Test"}, {"id": "2", "name": "Test2"}]
        uploaded_file = UploadedFile(
            session_id=uuid4(),
            filename="test.csv",
            file_size_bytes=100,
            parsed_content={"headers": ["id", "name"], "rows": rows},
            row_count=2,
        )
        result = uploaded_file.get_row_data()

        assert result == rows

    def test_is_classified_when_csv_type_set(self):
        """is_classified is True when csv_type is set."""
        uploaded_file = UploadedFile(
            session_id=uuid4(),
            filename="test.csv",
            file_size_bytes=100,
            parsed_content={"headers": [], "rows": []},
            csv_type="bundles",
            row_count=0,
        )
        assert uploaded_file.is_classified is True

    def test_is_not_classified_when_csv_type_not_set(self):
        """is_classified is False when csv_type is not set."""
        uploaded_file = UploadedFile(
            session_id=uuid4(),
            filename="test.csv",
            file_size_bytes=100,
            parsed_content={"headers": [], "rows": []},
            row_count=0,
        )
        assert uploaded_file.is_classified is False

    def test_is_valid_when_validation_passed(self):
        """is_valid is True when validation_status is valid."""
        uploaded_file = UploadedFile(
            session_id=uuid4(),
            filename="test.csv",
            file_size_bytes=100,
            parsed_content={"headers": [], "rows": []},
            validation_status=FileValidationStatus.VALID.value,
            row_count=0,
        )
        assert uploaded_file.is_valid is True

    def test_is_not_valid_when_validation_pending(self):
        """is_valid is False when validation_status is pending."""
        uploaded_file = UploadedFile(
            session_id=uuid4(),
            filename="test.csv",
            file_size_bytes=100,
            parsed_content={"headers": [], "rows": []},
            validation_status=FileValidationStatus.PENDING.value,
            row_count=0,
        )
        assert uploaded_file.is_valid is False

    def test_entity_count_returns_row_count(self):
        """entity_count returns row_count."""
        uploaded_file = UploadedFile(
            session_id=uuid4(),
            filename="test.csv",
            file_size_bytes=100,
            parsed_content={"headers": [], "rows": []},
            row_count=42,
        )
        assert uploaded_file.entity_count == 42

    def test_file_size_mb(self):
        """file_size_mb returns size in megabytes."""
        uploaded_file = UploadedFile(
            session_id=uuid4(),
            filename="test.csv",
            file_size_bytes=1048576,  # 1MB
            parsed_content={"headers": [], "rows": []},
            row_count=0,
        )
        assert uploaded_file.file_size_mb == 1.0
