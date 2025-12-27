# tests/backend/unit/test_repositories/test_ticket_repository.py
"""
Tests for TicketRepository operations.
"""
import pytest
from uuid import uuid4

from app.models.session import Session
from app.repositories.sqlalchemy.ticket_repository import SQLAlchemyTicketRepository


@pytest.mark.phase1
@pytest.mark.repositories
class TestTicketRepositoryCRUD:
    """Test basic CRUD operations."""

    @pytest.fixture
    async def session_id(self, db_session, sample_session_data):
        """Create a session and return its ID."""
        session = Session(**sample_session_data)
        db_session.add(session)
        await db_session.flush()
        return session.id

    @pytest.fixture
    def repo(self, db_session):
        return SQLAlchemyTicketRepository(db_session)

    @pytest.mark.asyncio
    async def test_create_ticket(self, repo, session_id, sample_ticket_data):
        """Should create a ticket and return it with ID."""
        ticket_data = {**sample_ticket_data, "session_id": session_id}
        ticket = await repo.create_ticket(ticket_data)

        assert ticket.id is not None
        assert ticket.title == sample_ticket_data["title"]
        assert ticket.entity_group == sample_ticket_data["entity_group"]

    @pytest.mark.asyncio
    async def test_get_ticket_by_id(self, repo, session_id, sample_ticket_data):
        """Should retrieve ticket by ID."""
        ticket_data = {**sample_ticket_data, "session_id": session_id}
        created = await repo.create_ticket(ticket_data)

        retrieved = await repo.get_ticket_by_id(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id

    @pytest.mark.asyncio
    async def test_get_ticket_by_id_not_found(self, repo):
        """Should return None for non-existent ticket."""
        result = await repo.get_ticket_by_id(uuid4())

        assert result is None

    @pytest.mark.asyncio
    async def test_get_tickets_by_session(self, repo, session_id, sample_ticket_data):
        """Should get all tickets for a session."""
        await repo.create_ticket({**sample_ticket_data, "session_id": session_id, "user_order": 1})
        await repo.create_ticket({**sample_ticket_data, "session_id": session_id, "user_order": 2, "title": "Ticket 2"})

        tickets = await repo.get_tickets_by_session(session_id)

        assert len(tickets) == 2

    @pytest.mark.asyncio
    async def test_update_ticket(self, repo, session_id, sample_ticket_data):
        """Should update ticket fields."""
        ticket = await repo.create_ticket({**sample_ticket_data, "session_id": session_id})

        updated = await repo.update_ticket(ticket.id, {"title": "Updated Title"})

        assert updated.title == "Updated Title"


@pytest.mark.phase1
@pytest.mark.repositories
class TestTicketRepositoryReviewSupport:
    """Test review interface support operations."""

    @pytest.fixture
    async def session_id(self, db_session, sample_session_data):
        session = Session(**sample_session_data)
        db_session.add(session)
        await db_session.flush()
        return session.id

    @pytest.fixture
    def repo(self, db_session):
        return SQLAlchemyTicketRepository(db_session)

    @pytest.mark.asyncio
    async def test_get_tickets_by_entity_group(self, repo, session_id, sample_ticket_data):
        """Should get tickets for specific entity group."""
        await repo.create_ticket({**sample_ticket_data, "session_id": session_id, "entity_group": "Content", "user_order": 1})
        await repo.create_ticket({**sample_ticket_data, "session_id": session_id, "entity_group": "Media", "user_order": 1})

        content_tickets = await repo.get_tickets_by_entity_group(session_id, "Content")

        assert len(content_tickets) == 1
        assert content_tickets[0].entity_group == "Content"

    @pytest.mark.asyncio
    async def test_get_tickets_summary(self, repo, session_id, sample_ticket_data):
        """Should get summary by entity group."""
        await repo.create_ticket({**sample_ticket_data, "session_id": session_id, "entity_group": "Content", "user_order": 1})
        await repo.create_ticket({**sample_ticket_data, "session_id": session_id, "entity_group": "Content", "user_order": 2, "ready_for_jira": True})
        await repo.create_ticket({**sample_ticket_data, "session_id": session_id, "entity_group": "Media", "user_order": 1})

        summary = await repo.get_tickets_summary(session_id)

        assert summary["Content"]["total"] == 2
        assert summary["Content"]["ready"] == 1
        assert summary["Media"]["total"] == 1


@pytest.mark.phase1
@pytest.mark.repositories
class TestTicketRepositoryExportSupport:
    """Test export support operations."""

    @pytest.fixture
    async def session_id(self, db_session, sample_session_data):
        session = Session(**sample_session_data)
        db_session.add(session)
        await db_session.flush()
        return session.id

    @pytest.fixture
    def repo(self, db_session):
        return SQLAlchemyTicketRepository(db_session)

    @pytest.mark.asyncio
    async def test_get_export_ready_tickets(self, repo, session_id, sample_ticket_data):
        """Should get only tickets marked ready for export."""
        await repo.create_ticket({**sample_ticket_data, "session_id": session_id, "user_order": 1, "ready_for_jira": True})
        await repo.create_ticket({**sample_ticket_data, "session_id": session_id, "user_order": 2, "ready_for_jira": False})

        ready_tickets = await repo.get_export_ready_tickets(session_id)

        assert len(ready_tickets) == 1
        assert ready_tickets[0].ready_for_jira is True

    @pytest.mark.asyncio
    async def test_mark_ticket_exported(self, repo, session_id, sample_ticket_data):
        """Should mark ticket as exported with Jira details."""
        ticket = await repo.create_ticket({**sample_ticket_data, "session_id": session_id})

        await repo.mark_ticket_exported(ticket.id, "TEST-123", "https://jira.example.com/TEST-123")

        updated = await repo.get_ticket_by_id(ticket.id)
        assert updated.jira_ticket_key == "TEST-123"
        assert updated.jira_ticket_url == "https://jira.example.com/TEST-123"


@pytest.mark.phase1
@pytest.mark.repositories
class TestTicketRepositoryDependencies:
    """Test dependency operations."""

    @pytest.fixture
    async def session_id(self, db_session, sample_session_data):
        session = Session(**sample_session_data)
        db_session.add(session)
        await db_session.flush()
        return session.id

    @pytest.fixture
    def repo(self, db_session):
        return SQLAlchemyTicketRepository(db_session)

    @pytest.mark.asyncio
    async def test_create_dependency(self, repo, session_id, sample_ticket_data):
        """Should create dependency between tickets."""
        ticket1 = await repo.create_ticket({**sample_ticket_data, "session_id": session_id, "user_order": 1})
        ticket2 = await repo.create_ticket({**sample_ticket_data, "session_id": session_id, "user_order": 2})

        dependency = await repo.create_dependency(ticket2.id, ticket1.id)

        assert dependency is not None
        assert dependency.ticket_id == ticket2.id
        assert dependency.depends_on_ticket_id == ticket1.id

    @pytest.mark.asyncio
    async def test_get_dependencies_for_ticket(self, repo, session_id, sample_ticket_data):
        """Should get IDs of dependencies."""
        ticket1 = await repo.create_ticket({**sample_ticket_data, "session_id": session_id, "user_order": 1})
        ticket2 = await repo.create_ticket({**sample_ticket_data, "session_id": session_id, "user_order": 2})
        await repo.create_dependency(ticket2.id, ticket1.id)

        deps = await repo.get_dependencies_for_ticket(ticket2.id)

        assert ticket1.id in deps

    @pytest.mark.asyncio
    async def test_has_circular_dependency(self, repo, session_id, sample_ticket_data):
        """Should detect circular dependencies."""
        ticket1 = await repo.create_ticket({**sample_ticket_data, "session_id": session_id, "user_order": 1})
        ticket2 = await repo.create_ticket({**sample_ticket_data, "session_id": session_id, "user_order": 2})
        await repo.create_dependency(ticket2.id, ticket1.id)

        # Adding ticket1 -> ticket2 would create a cycle
        has_cycle = await repo.has_circular_dependency(ticket1.id, ticket2.id)

        assert has_cycle is True

    @pytest.mark.asyncio
    async def test_remove_dependency(self, repo, session_id, sample_ticket_data):
        """Should remove dependency between tickets."""
        ticket1 = await repo.create_ticket({**sample_ticket_data, "session_id": session_id, "user_order": 1})
        ticket2 = await repo.create_ticket({**sample_ticket_data, "session_id": session_id, "user_order": 2})
        await repo.create_dependency(ticket2.id, ticket1.id)

        await repo.remove_dependency(ticket2.id, ticket1.id)

        deps = await repo.get_dependencies_for_ticket(ticket2.id)
        assert len(deps) == 0
