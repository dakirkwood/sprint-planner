"""Tests for Ticket, TicketDependency, and Attachment models."""

import pytest
from uuid import UUID, uuid4
from sqlalchemy import inspect

from app.models.ticket import Ticket, TicketDependency, Attachment
from app.schemas.base import JiraUploadStatus


class TestTicketModel:
    """Test Ticket model field definitions."""

    def test_ticket_has_required_fields(self):
        """Ticket must have all 14 specified fields."""
        mapper = inspect(Ticket)
        columns = {c.key for c in mapper.columns}

        required_fields = {
            "id",
            "session_id",
            "title",
            "description",
            "csv_source_files",
            "entity_group",
            "user_order",
            "ready_for_jira",
            "sprint",
            "assignee",
            "user_notes",
            "jira_ticket_key",
            "jira_ticket_url",
            "created_at",
            "updated_at",
        }
        assert required_fields.issubset(columns)

    def test_ticket_does_not_have_attachment_id_fk(self):
        """Ticket should NOT have attachment_id FK (circular FK fix)."""
        mapper = inspect(Ticket)
        columns = {c.key for c in mapper.columns}

        assert "attachment_id" not in columns

    def test_ticket_has_relationship_to_attachment(self):
        """Ticket should navigate to Attachment via relationship."""
        mapper = inspect(Ticket)
        relationships = {r.key for r in mapper.relationships}

        assert "attachment" in relationships

    def test_ticket_has_dependency_relationships(self):
        """Ticket should have dependencies and depends_on relationships."""
        mapper = inspect(Ticket)
        relationships = {r.key for r in mapper.relationships}

        assert "dependencies" in relationships
        assert "depends_on" in relationships

    @pytest.mark.asyncio
    async def test_ready_for_jira_defaults_to_false(
        self, db_session, sample_session, sample_ticket_data
    ):
        """ready_for_jira should default to False."""
        ticket = Ticket(session_id=sample_session.id, **sample_ticket_data)
        db_session.add(ticket)
        await db_session.flush()

        assert ticket.ready_for_jira is False

    @pytest.mark.asyncio
    async def test_ticket_generates_uuid_on_create(
        self, db_session, sample_session, sample_ticket_data
    ):
        """Ticket should auto-generate UUID primary key."""
        ticket = Ticket(session_id=sample_session.id, **sample_ticket_data)
        db_session.add(ticket)
        await db_session.flush()

        assert ticket.id is not None
        assert isinstance(ticket.id, UUID)

    def test_mark_ready_for_jira(self):
        """mark_ready_for_jira sets the flag."""
        ticket = Ticket(
            session_id=uuid4(),
            title="Test",
            description="Test description",
            entity_group="Content",
            csv_source_files=[],
        )
        ticket.mark_ready_for_jira()

        assert ticket.ready_for_jira is True

    def test_set_jira_export_data(self):
        """set_jira_export_data stores Jira info."""
        ticket = Ticket(
            session_id=uuid4(),
            title="Test",
            description="Test description",
            entity_group="Content",
            csv_source_files=[],
        )
        ticket.set_jira_export_data("TEST-123", "https://jira.example.com/TEST-123")

        assert ticket.jira_ticket_key == "TEST-123"
        assert ticket.jira_ticket_url == "https://jira.example.com/TEST-123"

    def test_is_exported_when_has_jira_key(self):
        """is_exported is True when jira_ticket_key is set."""
        ticket = Ticket(
            session_id=uuid4(),
            title="Test",
            description="Test description",
            entity_group="Content",
            csv_source_files=[],
            jira_ticket_key="TEST-123",
        )
        assert ticket.is_exported is True

    def test_is_not_exported_when_no_jira_key(self):
        """is_exported is False when jira_ticket_key is not set."""
        ticket = Ticket(
            session_id=uuid4(),
            title="Test",
            description="Test description",
            entity_group="Content",
            csv_source_files=[],
        )
        assert ticket.is_exported is False

    def test_needs_attachment_for_long_description(self):
        """needs_attachment is True for descriptions over 30k chars."""
        long_description = "x" * 35000
        ticket = Ticket(
            session_id=uuid4(),
            title="Test",
            description=long_description,
            entity_group="Content",
            csv_source_files=[],
        )
        assert ticket.needs_attachment is True

    def test_does_not_need_attachment_for_short_description(self):
        """needs_attachment is False for descriptions under 30k chars."""
        ticket = Ticket(
            session_id=uuid4(),
            title="Test",
            description="Short description",
            entity_group="Content",
            csv_source_files=[],
        )
        assert ticket.needs_attachment is False

    def test_character_count(self):
        """character_count returns description length."""
        ticket = Ticket(
            session_id=uuid4(),
            title="Test",
            description="Test description with 31 chars!",
            entity_group="Content",
            csv_source_files=[],
        )
        assert ticket.character_count == 31


class TestTicketDependencyModel:
    """Test TicketDependency junction table."""

    def test_ticket_dependency_has_composite_primary_key(self):
        """TicketDependency uses composite PK of both ticket IDs."""
        mapper = inspect(TicketDependency)
        pk_columns = {c.key for c in mapper.primary_key}

        assert pk_columns == {"ticket_id", "depends_on_ticket_id"}

    def test_ticket_dependency_has_both_relationships(self):
        """TicketDependency should reference both tickets."""
        mapper = inspect(TicketDependency)
        relationships = {r.key for r in mapper.relationships}

        assert "dependent_ticket" in relationships
        assert "dependency_ticket" in relationships

    def test_ticket_dependency_has_created_at(self):
        """TicketDependency should have created_at field."""
        mapper = inspect(TicketDependency)
        columns = {c.key for c in mapper.columns}

        assert "created_at" in columns


class TestAttachmentModel:
    """Test Attachment model."""

    def test_attachment_has_ticket_id_fk(self):
        """Attachment should have ticket_id FK (owns the relationship)."""
        mapper = inspect(Attachment)
        columns = {c.key for c in mapper.columns}

        assert "ticket_id" in columns

    def test_attachment_has_required_fields(self):
        """Attachment must have all specified fields."""
        mapper = inspect(Attachment)
        columns = {c.key for c in mapper.columns}

        required_fields = {
            "id",
            "session_id",
            "ticket_id",
            "filename",
            "content",
            "file_size_bytes",
            "jira_attachment_id",
            "jira_upload_status",
            "created_at",
        }
        assert required_fields.issubset(columns)

    def test_jira_upload_status_enum_values(self):
        """JiraUploadStatus enum must have expected values."""
        expected = {"pending", "uploaded", "failed"}
        actual = {e.value for e in JiraUploadStatus}

        assert expected == actual

    @pytest.mark.asyncio
    async def test_attachment_defaults(self, db_session, sample_ticket):
        """Attachment should have correct defaults."""
        attachment = Attachment(
            session_id=sample_ticket.session_id,
            ticket_id=sample_ticket.id,
            filename="test.md",
            content="Test content",
            file_size_bytes=12,
        )
        db_session.add(attachment)
        await db_session.flush()

        assert attachment.jira_upload_status == JiraUploadStatus.PENDING.value

    def test_mark_uploaded_to_jira(self):
        """mark_uploaded_to_jira sets status and ID."""
        attachment = Attachment(
            session_id=uuid4(),
            ticket_id=uuid4(),
            filename="test.md",
            content="Test content",
            file_size_bytes=12,
        )
        attachment.mark_uploaded_to_jira("jira-attachment-123")

        assert attachment.jira_upload_status == JiraUploadStatus.UPLOADED.value
        assert attachment.jira_attachment_id == "jira-attachment-123"

    def test_mark_upload_failed(self):
        """mark_upload_failed sets status and clears ID."""
        attachment = Attachment(
            session_id=uuid4(),
            ticket_id=uuid4(),
            filename="test.md",
            content="Test content",
            file_size_bytes=12,
            jira_attachment_id="partial-id",
        )
        attachment.mark_upload_failed()

        assert attachment.jira_upload_status == JiraUploadStatus.FAILED.value
        assert attachment.jira_attachment_id is None

    def test_file_size_kb(self):
        """file_size_kb returns size in kilobytes."""
        attachment = Attachment(
            session_id=uuid4(),
            ticket_id=uuid4(),
            filename="test.md",
            content="x" * 1024,
            file_size_bytes=2048,
        )
        assert attachment.file_size_kb == 2.0

    def test_content_preview_short_content(self):
        """content_preview returns full content if short."""
        attachment = Attachment(
            session_id=uuid4(),
            ticket_id=uuid4(),
            filename="test.md",
            content="Short content",
            file_size_bytes=13,
        )
        assert attachment.content_preview == "Short content"

    def test_content_preview_long_content(self):
        """content_preview truncates long content."""
        long_content = "x" * 300
        attachment = Attachment(
            session_id=uuid4(),
            ticket_id=uuid4(),
            filename="test.md",
            content=long_content,
            file_size_bytes=300,
        )
        assert len(attachment.content_preview) == 203  # 200 + "..."
        assert attachment.content_preview.endswith("...")
