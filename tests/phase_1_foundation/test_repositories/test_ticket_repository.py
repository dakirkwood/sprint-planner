"""Tests for SQLAlchemy ticket repository."""

import pytest
from uuid import uuid4

from app.repositories.sqlalchemy.ticket_repository import SQLAlchemyTicketRepository
from app.models.ticket import Ticket
from app.schemas.base import JiraUploadStatus


class TestTicketRepositoryCreate:
    """Test ticket creation methods."""

    @pytest.mark.asyncio
    async def test_create_ticket(self, db_session, sample_session, sample_ticket_data):
        """Create a ticket."""
        repo = SQLAlchemyTicketRepository(db_session)
        sample_ticket_data["session_id"] = sample_session.id

        ticket = await repo.create_ticket(sample_ticket_data)

        assert ticket.id is not None
        assert ticket.title == sample_ticket_data["title"]
        assert ticket.entity_group == sample_ticket_data["entity_group"]

    @pytest.mark.asyncio
    async def test_create_ticket_defaults(self, db_session, sample_session):
        """Create ticket with default values."""
        repo = SQLAlchemyTicketRepository(db_session)

        ticket = await repo.create_ticket({
            "session_id": sample_session.id,
            "title": "Test Ticket",
            "description": "Description",
            "entity_group": "Test",
        })

        assert ticket.ready_for_jira is False
        assert ticket.user_order == 0


class TestTicketRepositoryRead:
    """Test ticket retrieval methods."""

    @pytest.mark.asyncio
    async def test_get_ticket_by_id(self, db_session, sample_ticket):
        """Get ticket by ID."""
        repo = SQLAlchemyTicketRepository(db_session)

        result = await repo.get_ticket_by_id(sample_ticket.id)

        assert result is not None
        assert result.id == sample_ticket.id

    @pytest.mark.asyncio
    async def test_get_ticket_by_id_not_found(self, db_session):
        """Get ticket by non-existent ID."""
        repo = SQLAlchemyTicketRepository(db_session)

        result = await repo.get_ticket_by_id(uuid4())

        assert result is None

    @pytest.mark.asyncio
    async def test_get_tickets_by_session(self, db_session, sample_session):
        """Get all tickets for a session."""
        repo = SQLAlchemyTicketRepository(db_session)

        await repo.create_ticket({
            "session_id": sample_session.id,
            "title": "Ticket 1",
            "description": "Desc",
            "entity_group": "Group A",
        })
        await repo.create_ticket({
            "session_id": sample_session.id,
            "title": "Ticket 2",
            "description": "Desc",
            "entity_group": "Group B",
        })

        results = await repo.get_tickets_by_session(sample_session.id)

        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_get_tickets_by_entity_group(self, db_session, sample_session):
        """Get tickets by entity group."""
        repo = SQLAlchemyTicketRepository(db_session)

        await repo.create_ticket({
            "session_id": sample_session.id,
            "title": "Content 1",
            "description": "Desc",
            "entity_group": "Content",
        })
        await repo.create_ticket({
            "session_id": sample_session.id,
            "title": "Content 2",
            "description": "Desc",
            "entity_group": "Content",
        })
        await repo.create_ticket({
            "session_id": sample_session.id,
            "title": "Config",
            "description": "Desc",
            "entity_group": "Configuration",
        })

        results = await repo.get_tickets_by_entity_group(sample_session.id, "Content")

        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_get_export_ready_tickets(self, db_session, sample_session):
        """Get tickets ready for export."""
        repo = SQLAlchemyTicketRepository(db_session)

        await repo.create_ticket({
            "session_id": sample_session.id,
            "title": "Ready",
            "description": "Desc",
            "entity_group": "Test",
            "ready_for_jira": True,
        })
        await repo.create_ticket({
            "session_id": sample_session.id,
            "title": "Not Ready",
            "description": "Desc",
            "entity_group": "Test",
            "ready_for_jira": False,
        })

        results = await repo.get_export_ready_tickets(sample_session.id)

        assert len(results) == 1
        assert results[0].title == "Ready"


class TestTicketRepositoryUpdate:
    """Test ticket update methods."""

    @pytest.mark.asyncio
    async def test_update_ticket(self, db_session, sample_ticket):
        """Update ticket fields."""
        repo = SQLAlchemyTicketRepository(db_session)

        result = await repo.update_ticket(
            sample_ticket.id,
            {"title": "Updated Title", "assignee": "user-123"},
        )

        assert result is not None
        assert result.title == "Updated Title"
        assert result.assignee == "user-123"

    @pytest.mark.asyncio
    async def test_update_ticket_not_found(self, db_session):
        """Update non-existent ticket."""
        repo = SQLAlchemyTicketRepository(db_session)

        result = await repo.update_ticket(uuid4(), {"title": "New Title"})

        assert result is None

    @pytest.mark.asyncio
    async def test_update_ticket_order(self, db_session, sample_session):
        """Update ticket ordering."""
        repo = SQLAlchemyTicketRepository(db_session)

        ticket1 = await repo.create_ticket({
            "session_id": sample_session.id,
            "title": "Ticket 1",
            "description": "Desc",
            "entity_group": "Test",
            "user_order": 0,
        })
        ticket2 = await repo.create_ticket({
            "session_id": sample_session.id,
            "title": "Ticket 2",
            "description": "Desc",
            "entity_group": "Test",
            "user_order": 1,
        })

        await repo.update_ticket_order(sample_session.id, [
            {"ticket_id": ticket1.id, "user_order": 1},
            {"ticket_id": ticket2.id, "user_order": 0},
        ])

        t1 = await repo.get_ticket_by_id(ticket1.id)
        t2 = await repo.get_ticket_by_id(ticket2.id)

        assert t1.user_order == 1
        assert t2.user_order == 0

    @pytest.mark.asyncio
    async def test_bulk_assign_tickets(self, db_session, sample_session):
        """Bulk assign tickets."""
        repo = SQLAlchemyTicketRepository(db_session)

        ticket1 = await repo.create_ticket({
            "session_id": sample_session.id,
            "title": "Ticket 1",
            "description": "Desc",
            "entity_group": "Test",
        })
        ticket2 = await repo.create_ticket({
            "session_id": sample_session.id,
            "title": "Ticket 2",
            "description": "Desc",
            "entity_group": "Test",
        })

        count = await repo.bulk_assign_tickets(
            [ticket1.id, ticket2.id],
            {"assignee": "user-abc", "sprint": "Sprint 1"},
        )

        assert count == 2

        t1 = await repo.get_ticket_by_id(ticket1.id)
        assert t1.assignee == "user-abc"
        assert t1.sprint == "Sprint 1"

    @pytest.mark.asyncio
    async def test_mark_ticket_exported(self, db_session, sample_ticket):
        """Mark ticket as exported to Jira."""
        repo = SQLAlchemyTicketRepository(db_session)

        await repo.mark_ticket_exported(
            sample_ticket.id,
            jira_key="TEST-123",
            jira_url="https://jira.example.com/browse/TEST-123",
        )

        ticket = await repo.get_ticket_by_id(sample_ticket.id)
        assert ticket.jira_ticket_key == "TEST-123"
        assert ticket.is_exported is True


class TestTicketRepositoryDelete:
    """Test ticket deletion methods."""

    @pytest.mark.asyncio
    async def test_delete_tickets_by_session(self, db_session, sample_session):
        """Delete all tickets for a session."""
        repo = SQLAlchemyTicketRepository(db_session)

        await repo.create_ticket({
            "session_id": sample_session.id,
            "title": "Ticket 1",
            "description": "Desc",
            "entity_group": "Test",
        })
        await repo.create_ticket({
            "session_id": sample_session.id,
            "title": "Ticket 2",
            "description": "Desc",
            "entity_group": "Test",
        })

        deleted = await repo.delete_tickets_by_session(sample_session.id)

        assert deleted == 2


class TestTicketRepositorySummary:
    """Test ticket summary methods."""

    @pytest.mark.asyncio
    async def test_get_tickets_summary(self, db_session, sample_session):
        """Get tickets summary for session."""
        repo = SQLAlchemyTicketRepository(db_session)

        await repo.create_ticket({
            "session_id": sample_session.id,
            "title": "Ready Ticket",
            "description": "Desc",
            "entity_group": "Content",
            "ready_for_jira": True,
        })
        ticket2 = await repo.create_ticket({
            "session_id": sample_session.id,
            "title": "Exported Ticket",
            "description": "Desc",
            "entity_group": "Content",
            "ready_for_jira": True,
        })
        await repo.mark_ticket_exported(
            ticket2.id, "TEST-1", "https://example.com"
        )
        await repo.create_ticket({
            "session_id": sample_session.id,
            "title": "Not Ready",
            "description": "Desc",
            "entity_group": "Config",
        })

        summary = await repo.get_tickets_summary(sample_session.id)

        assert summary["total_tickets"] == 3
        assert summary["ready_for_export"] == 2
        assert summary["exported"] == 1
        assert "Content" in summary["by_entity_group"]
        assert summary["by_entity_group"]["Content"]["total"] == 2


class TestTicketDependencies:
    """Test ticket dependency methods."""

    @pytest.mark.asyncio
    async def test_create_dependency(self, db_session, sample_session):
        """Create a dependency between tickets."""
        repo = SQLAlchemyTicketRepository(db_session)

        ticket1 = await repo.create_ticket({
            "session_id": sample_session.id,
            "title": "Ticket 1",
            "description": "Desc",
            "entity_group": "Test",
        })
        ticket2 = await repo.create_ticket({
            "session_id": sample_session.id,
            "title": "Ticket 2",
            "description": "Desc",
            "entity_group": "Test",
        })

        dep = await repo.create_dependency(ticket2.id, ticket1.id)

        assert dep.ticket_id == ticket2.id
        assert dep.depends_on_ticket_id == ticket1.id

    @pytest.mark.asyncio
    async def test_get_dependencies_for_ticket(self, db_session, sample_session):
        """Get dependencies for a ticket."""
        repo = SQLAlchemyTicketRepository(db_session)

        ticket1 = await repo.create_ticket({
            "session_id": sample_session.id,
            "title": "Ticket 1",
            "description": "Desc",
            "entity_group": "Test",
        })
        ticket2 = await repo.create_ticket({
            "session_id": sample_session.id,
            "title": "Ticket 2",
            "description": "Desc",
            "entity_group": "Test",
        })
        ticket3 = await repo.create_ticket({
            "session_id": sample_session.id,
            "title": "Ticket 3",
            "description": "Desc",
            "entity_group": "Test",
        })

        # ticket3 depends on both ticket1 and ticket2
        await repo.create_dependency(ticket3.id, ticket1.id)
        await repo.create_dependency(ticket3.id, ticket2.id)

        deps = await repo.get_dependencies_for_ticket(ticket3.id)

        assert len(deps) == 2
        assert ticket1.id in deps
        assert ticket2.id in deps

    @pytest.mark.asyncio
    async def test_get_dependents_for_ticket(self, db_session, sample_session):
        """Get tickets that depend on a ticket."""
        repo = SQLAlchemyTicketRepository(db_session)

        ticket1 = await repo.create_ticket({
            "session_id": sample_session.id,
            "title": "Ticket 1",
            "description": "Desc",
            "entity_group": "Test",
        })
        ticket2 = await repo.create_ticket({
            "session_id": sample_session.id,
            "title": "Ticket 2",
            "description": "Desc",
            "entity_group": "Test",
        })

        await repo.create_dependency(ticket2.id, ticket1.id)

        dependents = await repo.get_dependents_for_ticket(ticket1.id)

        assert len(dependents) == 1
        assert ticket2.id in dependents

    @pytest.mark.asyncio
    async def test_remove_dependency(self, db_session, sample_session):
        """Remove a dependency between tickets."""
        repo = SQLAlchemyTicketRepository(db_session)

        ticket1 = await repo.create_ticket({
            "session_id": sample_session.id,
            "title": "Ticket 1",
            "description": "Desc",
            "entity_group": "Test",
        })
        ticket2 = await repo.create_ticket({
            "session_id": sample_session.id,
            "title": "Ticket 2",
            "description": "Desc",
            "entity_group": "Test",
        })

        await repo.create_dependency(ticket2.id, ticket1.id)
        await repo.remove_dependency(ticket2.id, ticket1.id)

        deps = await repo.get_dependencies_for_ticket(ticket2.id)
        assert len(deps) == 0

    @pytest.mark.asyncio
    async def test_has_circular_dependency(self, db_session, sample_session):
        """Detect circular dependency."""
        repo = SQLAlchemyTicketRepository(db_session)

        ticket1 = await repo.create_ticket({
            "session_id": sample_session.id,
            "title": "Ticket 1",
            "description": "Desc",
            "entity_group": "Test",
        })
        ticket2 = await repo.create_ticket({
            "session_id": sample_session.id,
            "title": "Ticket 2",
            "description": "Desc",
            "entity_group": "Test",
        })
        ticket3 = await repo.create_ticket({
            "session_id": sample_session.id,
            "title": "Ticket 3",
            "description": "Desc",
            "entity_group": "Test",
        })

        # ticket2 depends on ticket1
        await repo.create_dependency(ticket2.id, ticket1.id)
        # ticket3 depends on ticket2
        await repo.create_dependency(ticket3.id, ticket2.id)

        # Adding ticket1 depends on ticket3 would create a cycle
        has_cycle = await repo.has_circular_dependency(ticket1.id, ticket3.id)

        assert has_cycle is True

    @pytest.mark.asyncio
    async def test_no_circular_dependency(self, db_session, sample_session):
        """No circular dependency detected."""
        repo = SQLAlchemyTicketRepository(db_session)

        ticket1 = await repo.create_ticket({
            "session_id": sample_session.id,
            "title": "Ticket 1",
            "description": "Desc",
            "entity_group": "Test",
        })
        ticket2 = await repo.create_ticket({
            "session_id": sample_session.id,
            "title": "Ticket 2",
            "description": "Desc",
            "entity_group": "Test",
        })

        # No existing dependencies
        has_cycle = await repo.has_circular_dependency(ticket2.id, ticket1.id)

        assert has_cycle is False

    @pytest.mark.asyncio
    async def test_get_tickets_in_dependency_order(self, db_session, sample_session):
        """Get tickets in topological order."""
        repo = SQLAlchemyTicketRepository(db_session)

        ticket1 = await repo.create_ticket({
            "session_id": sample_session.id,
            "title": "Ticket 1",
            "description": "Base",
            "entity_group": "Test",
        })
        ticket2 = await repo.create_ticket({
            "session_id": sample_session.id,
            "title": "Ticket 2",
            "description": "Depends on 1",
            "entity_group": "Test",
        })
        ticket3 = await repo.create_ticket({
            "session_id": sample_session.id,
            "title": "Ticket 3",
            "description": "Depends on 1 and 2",
            "entity_group": "Test",
        })

        await repo.create_dependency(ticket2.id, ticket1.id)
        await repo.create_dependency(ticket3.id, ticket1.id)
        await repo.create_dependency(ticket3.id, ticket2.id)

        ordered = await repo.get_tickets_in_dependency_order(sample_session.id)

        # ticket1 must come before ticket2 and ticket3
        # ticket2 must come before ticket3
        t1_idx = next(i for i, t in enumerate(ordered) if t.id == ticket1.id)
        t2_idx = next(i for i, t in enumerate(ordered) if t.id == ticket2.id)
        t3_idx = next(i for i, t in enumerate(ordered) if t.id == ticket3.id)

        assert t1_idx < t2_idx
        assert t1_idx < t3_idx
        assert t2_idx < t3_idx

    @pytest.mark.asyncio
    async def test_get_dependency_graph(self, db_session, sample_session):
        """Get dependency graph for session."""
        repo = SQLAlchemyTicketRepository(db_session)

        ticket1 = await repo.create_ticket({
            "session_id": sample_session.id,
            "title": "Ticket 1",
            "description": "Desc",
            "entity_group": "Test",
        })
        ticket2 = await repo.create_ticket({
            "session_id": sample_session.id,
            "title": "Ticket 2",
            "description": "Desc",
            "entity_group": "Test",
        })

        await repo.create_dependency(ticket2.id, ticket1.id)

        graph = await repo.get_dependency_graph(sample_session.id)

        assert len(graph["nodes"]) == 2
        assert len(graph["edges"]) == 1


class TestAttachmentMethods:
    """Test attachment-related methods."""

    @pytest.mark.asyncio
    async def test_create_attachment(self, db_session, sample_session, sample_ticket):
        """Create an attachment for a ticket."""
        repo = SQLAlchemyTicketRepository(db_session)

        attachment = await repo.create_attachment({
            "session_id": sample_session.id,
            "ticket_id": sample_ticket.id,
            "filename": "config.txt",
            "content": "configuration data",
            "file_size_bytes": 500,
        })

        assert attachment.id is not None
        assert attachment.filename == "config.txt"
        assert attachment.jira_upload_status == JiraUploadStatus.PENDING.value

    @pytest.mark.asyncio
    async def test_get_attachment_by_ticket(
        self, db_session, sample_session, sample_ticket
    ):
        """Get attachment for a ticket."""
        repo = SQLAlchemyTicketRepository(db_session)

        await repo.create_attachment({
            "session_id": sample_session.id,
            "ticket_id": sample_ticket.id,
            "filename": "config.txt",
            "content": "configuration data",
            "file_size_bytes": 500,
        })

        result = await repo.get_attachment_by_ticket(sample_ticket.id)

        assert result is not None
        assert result.filename == "config.txt"

    @pytest.mark.asyncio
    async def test_mark_attachment_uploaded(
        self, db_session, sample_session, sample_ticket
    ):
        """Mark attachment as uploaded to Jira."""
        repo = SQLAlchemyTicketRepository(db_session)

        attachment = await repo.create_attachment({
            "session_id": sample_session.id,
            "ticket_id": sample_ticket.id,
            "filename": "config.txt",
            "content": "configuration data",
            "file_size_bytes": 500,
        })

        await repo.mark_attachment_uploaded(attachment.id, "jira-attach-123")

        result = await repo.get_attachment_by_ticket(sample_ticket.id)
        assert result.jira_upload_status == JiraUploadStatus.UPLOADED.value
        assert result.jira_attachment_id == "jira-attach-123"

    @pytest.mark.asyncio
    async def test_get_pending_attachments(self, db_session, sample_session):
        """Get pending attachments for session."""
        repo = SQLAlchemyTicketRepository(db_session)

        ticket1 = await repo.create_ticket({
            "session_id": sample_session.id,
            "title": "Ticket 1",
            "description": "Desc",
            "entity_group": "Test",
        })
        ticket2 = await repo.create_ticket({
            "session_id": sample_session.id,
            "title": "Ticket 2",
            "description": "Desc",
            "entity_group": "Test",
        })

        attachment1 = await repo.create_attachment({
            "session_id": sample_session.id,
            "ticket_id": ticket1.id,
            "filename": "file1.txt",
            "content": "data",
            "file_size_bytes": 100,
        })
        await repo.create_attachment({
            "session_id": sample_session.id,
            "ticket_id": ticket2.id,
            "filename": "file2.txt",
            "content": "data",
            "file_size_bytes": 100,
        })

        # Upload one attachment
        await repo.mark_attachment_uploaded(attachment1.id, "jira-1")

        pending = await repo.get_pending_attachments(sample_session.id)

        assert len(pending) == 1
        assert pending[0].filename == "file2.txt"
