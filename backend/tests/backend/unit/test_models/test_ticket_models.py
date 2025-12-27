# tests/backend/unit/test_models/test_ticket_models.py
"""
Tests for Ticket, TicketDependency, and Attachment models.
"""
import pytest
from sqlalchemy import inspect

from app.models.ticket import Ticket, TicketDependency, Attachment
from app.models.session import Session
from app.schemas.base import JiraUploadStatus


@pytest.mark.phase1
@pytest.mark.models
class TestTicketModel:
    """Test Ticket model field definitions."""

    def test_ticket_has_required_fields(self):
        """Ticket must have all 14 specified fields."""
        mapper = inspect(Ticket)
        columns = {c.key for c in mapper.columns}

        required_fields = {
            'id', 'session_id', 'title', 'description', 'csv_source_files',
            'entity_group', 'user_order', 'ready_for_jira', 'sprint',
            'assignee', 'user_notes', 'jira_ticket_key', 'jira_ticket_url',
            'created_at', 'updated_at'
        }
        assert required_fields.issubset(columns)

    def test_ticket_does_not_have_attachment_id_fk(self):
        """Ticket should NOT have attachment_id FK (circular FK fix)."""
        mapper = inspect(Ticket)
        columns = {c.key for c in mapper.columns}

        assert 'attachment_id' not in columns

    def test_ticket_has_relationship_to_attachment(self):
        """Ticket should navigate to Attachment via relationship."""
        mapper = inspect(Ticket)
        relationships = {r.key for r in mapper.relationships}

        assert 'attachment' in relationships

    def test_ticket_has_dependency_relationships(self):
        """Ticket should have dependencies and depends_on relationships."""
        mapper = inspect(Ticket)
        relationships = {r.key for r in mapper.relationships}

        assert 'dependencies' in relationships
        assert 'depends_on' in relationships

    @pytest.mark.asyncio
    async def test_ready_for_jira_defaults_to_false(self, db_session, sample_session_data, sample_ticket_data):
        """ready_for_jira should default to False."""
        session = Session(**sample_session_data)
        db_session.add(session)
        await db_session.flush()

        ticket = Ticket(session_id=session.id, **sample_ticket_data)
        db_session.add(ticket)
        await db_session.flush()

        assert ticket.ready_for_jira is False

    @pytest.mark.asyncio
    async def test_ticket_character_count(self, db_session, sample_session_data, sample_ticket_data):
        """Character count should return description length."""
        session = Session(**sample_session_data)
        db_session.add(session)
        await db_session.flush()

        ticket = Ticket(session_id=session.id, **sample_ticket_data)
        db_session.add(ticket)
        await db_session.flush()

        assert ticket.character_count == len(sample_ticket_data["description"])

    @pytest.mark.asyncio
    async def test_ticket_is_exported(self, db_session, sample_session_data, sample_ticket_data):
        """is_exported should return True when jira_ticket_key is set."""
        session = Session(**sample_session_data)
        db_session.add(session)
        await db_session.flush()

        ticket = Ticket(session_id=session.id, **sample_ticket_data)
        db_session.add(ticket)
        await db_session.flush()

        assert ticket.is_exported is False

        ticket.jira_ticket_key = "TEST-123"
        assert ticket.is_exported is True

    @pytest.mark.asyncio
    async def test_ticket_csv_source_summary(self, db_session, sample_session_data, sample_ticket_data):
        """csv_source_summary should return human-readable summary."""
        session = Session(**sample_session_data)
        db_session.add(session)
        await db_session.flush()

        ticket = Ticket(session_id=session.id, **sample_ticket_data)
        db_session.add(ticket)
        await db_session.flush()

        assert ticket.csv_source_summary == "bundles.csv"

    @pytest.mark.asyncio
    async def test_ticket_add_csv_source_reference(self, db_session, sample_session_data, sample_ticket_data):
        """add_csv_source_reference should add or update references."""
        session = Session(**sample_session_data)
        db_session.add(session)
        await db_session.flush()

        ticket_data = {**sample_ticket_data, "csv_source_files": None}
        ticket = Ticket(session_id=session.id, **ticket_data)
        db_session.add(ticket)
        await db_session.flush()

        ticket.add_csv_source_reference("test.csv", [1, 2])
        assert len(ticket.csv_source_files) == 1
        assert ticket.csv_source_files[0]["filename"] == "test.csv"

        # Adding more rows to same file
        ticket.add_csv_source_reference("test.csv", [3, 4])
        assert len(ticket.csv_source_files) == 1
        assert sorted(ticket.csv_source_files[0]["rows"]) == [1, 2, 3, 4]


@pytest.mark.phase1
@pytest.mark.models
class TestTicketDependencyModel:
    """Test TicketDependency junction table."""

    def test_ticket_dependency_has_composite_primary_key(self):
        """TicketDependency uses composite PK of both ticket IDs."""
        mapper = inspect(TicketDependency)
        pk_columns = {c.key for c in mapper.primary_key}

        assert pk_columns == {'ticket_id', 'depends_on_ticket_id'}

    def test_ticket_dependency_has_both_relationships(self):
        """TicketDependency should reference both tickets."""
        mapper = inspect(TicketDependency)
        relationships = {r.key for r in mapper.relationships}

        assert 'dependent_ticket' in relationships
        assert 'dependency_ticket' in relationships


@pytest.mark.phase1
@pytest.mark.models
class TestAttachmentModel:
    """Test Attachment model."""

    def test_attachment_has_ticket_id_fk(self):
        """Attachment should have ticket_id FK (owns the relationship)."""
        mapper = inspect(Attachment)
        columns = {c.key for c in mapper.columns}

        assert 'ticket_id' in columns

    def test_attachment_ticket_id_is_unique(self):
        """ticket_id should be unique (enforces 1:1)."""
        table = Attachment.__table__
        ticket_id_col = table.c.ticket_id

        assert ticket_id_col.unique is True

    def test_jira_upload_status_enum_values(self):
        """JiraUploadStatus enum must have expected values."""
        expected = {'pending', 'uploaded', 'failed'}
        actual = {e.value for e in JiraUploadStatus}

        assert expected == actual
