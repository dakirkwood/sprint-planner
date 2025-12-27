# app/repositories/sqlalchemy/ticket_repository.py
"""
SQLAlchemy implementation of TicketRepositoryInterface.
"""
from typing import List, Optional, Dict, Set
from uuid import UUID
from collections import defaultdict

from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.ticket import Ticket, TicketDependency, Attachment
from app.repositories.interfaces.ticket_repository import TicketRepositoryInterface
from app.schemas.base import JiraUploadStatus


class SQLAlchemyTicketRepository(TicketRepositoryInterface):
    """
    SQLAlchemy implementation for ticket repository operations.
    """

    def __init__(self, session: AsyncSession):
        self._session = session

    # ==========================================================================
    # Ticket CRUD Operations
    # ==========================================================================

    async def create_ticket(self, ticket_data: dict) -> Ticket:
        """Create a new ticket."""
        ticket = Ticket(**ticket_data)
        self._session.add(ticket)
        await self._session.flush()
        return ticket

    async def get_ticket_by_id(self, ticket_id: UUID) -> Optional[Ticket]:
        """Get ticket by ID, including attachment and dependencies."""
        stmt = (
            select(Ticket)
            .options(
                selectinload(Ticket.attachment),
                selectinload(Ticket.dependencies),
                selectinload(Ticket.depends_on)
            )
            .where(Ticket.id == ticket_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_tickets_by_session(self, session_id: UUID) -> List[Ticket]:
        """Get all tickets for a session."""
        stmt = (
            select(Ticket)
            .where(Ticket.session_id == session_id)
            .order_by(Ticket.entity_group, Ticket.user_order)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update_ticket(self, ticket_id: UUID, updates: dict) -> Ticket:
        """Update ticket fields."""
        ticket = await self.get_ticket_by_id(ticket_id)
        if ticket is None:
            raise ValueError(f"Ticket not found: {ticket_id}")

        for key, value in updates.items():
            if hasattr(ticket, key):
                setattr(ticket, key, value)

        await self._session.flush()
        return ticket

    async def delete_tickets_by_session(self, session_id: UUID) -> int:
        """Delete all tickets for a session. Returns count deleted."""
        stmt = delete(Ticket).where(Ticket.session_id == session_id)
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount

    # ==========================================================================
    # Review Interface Support
    # ==========================================================================

    async def get_tickets_by_entity_group(self, session_id: UUID, entity_group: str) -> List[Ticket]:
        """Get tickets for a specific entity group, ordered by user_order."""
        stmt = (
            select(Ticket)
            .where(Ticket.session_id == session_id)
            .where(Ticket.entity_group == entity_group)
            .order_by(Ticket.user_order)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_tickets_summary(self, session_id: UUID) -> dict:
        """Get summary of tickets by entity group."""
        tickets = await self.get_tickets_by_session(session_id)

        summary = defaultdict(lambda: {"total": 0, "ready": 0, "exported": 0})

        for ticket in tickets:
            summary[ticket.entity_group]["total"] += 1
            if ticket.ready_for_jira:
                summary[ticket.entity_group]["ready"] += 1
            if ticket.is_exported:
                summary[ticket.entity_group]["exported"] += 1

        return dict(summary)

    async def update_ticket_order(self, session_id: UUID, order_updates: List[dict]) -> None:
        """Update user_order for multiple tickets."""
        for update_item in order_updates:
            ticket_id = update_item.get("ticket_id")
            new_order = update_item.get("user_order")

            if ticket_id and new_order is not None:
                stmt = (
                    update(Ticket)
                    .where(Ticket.id == ticket_id)
                    .where(Ticket.session_id == session_id)
                    .values(user_order=new_order)
                )
                await self._session.execute(stmt)

        await self._session.flush()

    # ==========================================================================
    # Bulk Operations
    # ==========================================================================

    async def bulk_assign_tickets(self, ticket_ids: List[UUID], assignments: dict) -> int:
        """Assign sprint/assignee to multiple tickets. Returns count updated."""
        values = {}
        if "sprint" in assignments:
            values["sprint"] = assignments["sprint"]
        if "assignee" in assignments:
            values["assignee"] = assignments["assignee"]

        if not values:
            return 0

        stmt = update(Ticket).where(Ticket.id.in_(ticket_ids)).values(**values)
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount

    async def bulk_update_tickets(self, ticket_ids: List[UUID], updates: dict) -> int:
        """Update fields for multiple tickets. Returns count updated."""
        if not updates:
            return 0

        stmt = update(Ticket).where(Ticket.id.in_(ticket_ids)).values(**updates)
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount

    # ==========================================================================
    # Export Support
    # ==========================================================================

    async def get_export_ready_tickets(self, session_id: UUID) -> List[Ticket]:
        """Get tickets marked ready for Jira export."""
        stmt = (
            select(Ticket)
            .where(Ticket.session_id == session_id)
            .where(Ticket.ready_for_jira == True)
            .where(Ticket.jira_ticket_key.is_(None))
            .order_by(Ticket.entity_group, Ticket.user_order)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_tickets_in_dependency_order(self, session_id: UUID) -> List[Ticket]:
        """Get export-ready tickets in dependency order (dependencies first)."""
        tickets = await self.get_export_ready_tickets(session_id)

        if not tickets:
            return []

        # Build dependency graph
        ticket_map = {t.id: t for t in tickets}
        graph = await self.get_dependency_graph(session_id)

        # Topological sort
        result = []
        visited: Set[UUID] = set()
        temp_visited: Set[UUID] = set()

        def visit(ticket_id: UUID) -> None:
            if ticket_id in visited:
                return
            if ticket_id in temp_visited:
                return  # Skip circular dependencies

            temp_visited.add(ticket_id)

            # Visit dependencies first
            for dep_id in graph.get(str(ticket_id), {}).get("depends_on", []):
                dep_uuid = UUID(dep_id) if isinstance(dep_id, str) else dep_id
                if dep_uuid in ticket_map:
                    visit(dep_uuid)

            temp_visited.remove(ticket_id)
            visited.add(ticket_id)

            if ticket_id in ticket_map:
                result.append(ticket_map[ticket_id])

        for ticket in tickets:
            visit(ticket.id)

        return result

    async def mark_ticket_exported(self, ticket_id: UUID, jira_key: str, jira_url: str) -> None:
        """Mark ticket as exported with Jira details."""
        ticket = await self.get_ticket_by_id(ticket_id)
        if ticket:
            ticket.jira_ticket_key = jira_key
            ticket.jira_ticket_url = jira_url
            await self._session.flush()

    # ==========================================================================
    # Dependency Operations
    # ==========================================================================

    async def create_dependency(self, ticket_id: UUID, depends_on_ticket_id: UUID) -> TicketDependency:
        """Create a dependency between tickets."""
        dependency = TicketDependency(
            ticket_id=ticket_id,
            depends_on_ticket_id=depends_on_ticket_id
        )
        self._session.add(dependency)
        await self._session.flush()
        return dependency

    async def remove_dependency(self, ticket_id: UUID, depends_on_ticket_id: UUID) -> None:
        """Remove a dependency between tickets."""
        stmt = (
            delete(TicketDependency)
            .where(TicketDependency.ticket_id == ticket_id)
            .where(TicketDependency.depends_on_ticket_id == depends_on_ticket_id)
        )
        await self._session.execute(stmt)
        await self._session.flush()

    async def get_dependencies_for_ticket(self, ticket_id: UUID) -> List[UUID]:
        """Get IDs of tickets that this ticket depends on."""
        stmt = (
            select(TicketDependency.depends_on_ticket_id)
            .where(TicketDependency.ticket_id == ticket_id)
        )
        result = await self._session.execute(stmt)
        return [row[0] for row in result.all()]

    async def get_dependents_for_ticket(self, ticket_id: UUID) -> List[UUID]:
        """Get IDs of tickets that depend on this ticket."""
        stmt = (
            select(TicketDependency.ticket_id)
            .where(TicketDependency.depends_on_ticket_id == ticket_id)
        )
        result = await self._session.execute(stmt)
        return [row[0] for row in result.all()]

    async def has_circular_dependency(self, ticket_id: UUID, depends_on_id: UUID) -> bool:
        """Check if adding dependency would create a cycle."""
        if ticket_id == depends_on_id:
            return True

        visited: Set[UUID] = set()

        async def can_reach(from_id: UUID, to_id: UUID) -> bool:
            if from_id == to_id:
                return True
            if from_id in visited:
                return False

            visited.add(from_id)
            deps = await self.get_dependencies_for_ticket(from_id)

            for dep_id in deps:
                if await can_reach(dep_id, to_id):
                    return True

            return False

        # Check if depends_on_id can reach ticket_id through existing dependencies
        return await can_reach(depends_on_id, ticket_id)

    async def get_dependency_graph(self, session_id: UUID) -> dict:
        """Get complete dependency graph for session."""
        tickets = await self.get_tickets_by_session(session_id)
        ticket_ids = [t.id for t in tickets]

        graph = {}
        for ticket_id in ticket_ids:
            deps = await self.get_dependencies_for_ticket(ticket_id)
            dependents = await self.get_dependents_for_ticket(ticket_id)
            graph[str(ticket_id)] = {
                "depends_on": [str(d) for d in deps],
                "dependents": [str(d) for d in dependents]
            }

        return graph

    # ==========================================================================
    # Attachment Operations
    # ==========================================================================

    async def create_attachment(self, attachment_data: dict) -> Attachment:
        """Create attachment for a ticket."""
        attachment = Attachment(**attachment_data)
        self._session.add(attachment)
        await self._session.flush()
        return attachment

    async def get_attachment_by_ticket(self, ticket_id: UUID) -> Optional[Attachment]:
        """Get attachment for a ticket."""
        stmt = select(Attachment).where(Attachment.ticket_id == ticket_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def mark_attachment_uploaded(self, attachment_id: UUID, jira_attachment_id: str) -> None:
        """Mark attachment as uploaded to Jira."""
        stmt = select(Attachment).where(Attachment.id == attachment_id)
        result = await self._session.execute(stmt)
        attachment = result.scalar_one_or_none()

        if attachment:
            attachment.upload_status = JiraUploadStatus.UPLOADED
            attachment.jira_attachment_id = jira_attachment_id
            await self._session.flush()

    async def get_pending_attachments(self, session_id: UUID) -> List[Attachment]:
        """Get attachments pending upload for a session."""
        stmt = (
            select(Attachment)
            .join(Ticket, Attachment.ticket_id == Ticket.id)
            .where(Ticket.session_id == session_id)
            .where(Attachment.upload_status == JiraUploadStatus.PENDING)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
