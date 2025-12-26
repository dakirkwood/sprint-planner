"""SQLAlchemy implementation of ticket repository."""

from typing import List, Optional, Set
from uuid import UUID

from sqlalchemy import select, delete, update, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.ticket import Ticket, TicketDependency, Attachment
from app.repositories.interfaces.ticket_repository import TicketRepositoryInterface
from app.schemas.base import JiraUploadStatus


class SQLAlchemyTicketRepository(TicketRepositoryInterface):
    """SQLAlchemy implementation of ticket repository."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def create_ticket(self, ticket_data: dict) -> Ticket:
        """Create a new ticket."""
        ticket = Ticket(
            session_id=ticket_data["session_id"],
            title=ticket_data["title"],
            description=ticket_data["description"],
            csv_source_files=ticket_data.get("csv_source_files", []),
            entity_group=ticket_data["entity_group"],
            user_order=ticket_data.get("user_order", 0),
            ready_for_jira=ticket_data.get("ready_for_jira", False),
            sprint=ticket_data.get("sprint"),
            assignee=ticket_data.get("assignee"),
            user_notes=ticket_data.get("user_notes"),
        )
        self.db.add(ticket)
        await self.db.flush()
        return ticket

    async def get_ticket_by_id(self, ticket_id: UUID) -> Optional[Ticket]:
        """Get ticket by ID with relationships."""
        stmt = (
            select(Ticket)
            .options(
                selectinload(Ticket.attachment),
                selectinload(Ticket.dependencies),
                selectinload(Ticket.depends_on),
            )
            .where(Ticket.id == ticket_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_tickets_by_session(self, session_id: UUID) -> List[Ticket]:
        """Get all tickets for a session."""
        stmt = (
            select(Ticket)
            .where(Ticket.session_id == session_id)
            .order_by(Ticket.entity_group, Ticket.user_order)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update_ticket(
        self,
        ticket_id: UUID,
        updates: dict,
    ) -> Optional[Ticket]:
        """Update ticket fields."""
        ticket = await self.get_ticket_by_id(ticket_id)
        if not ticket:
            return None

        for key, value in updates.items():
            if hasattr(ticket, key):
                setattr(ticket, key, value)

        await self.db.flush()
        return ticket

    async def delete_tickets_by_session(self, session_id: UUID) -> int:
        """Delete all tickets for a session."""
        stmt = delete(Ticket).where(Ticket.session_id == session_id)
        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.rowcount

    async def get_tickets_by_entity_group(
        self,
        session_id: UUID,
        entity_group: str,
    ) -> List[Ticket]:
        """Get tickets for specific entity group."""
        stmt = (
            select(Ticket)
            .where(
                Ticket.session_id == session_id,
                Ticket.entity_group == entity_group,
            )
            .order_by(Ticket.user_order)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_tickets_summary(self, session_id: UUID) -> dict:
        """Get ticket summary for session."""
        tickets = await self.get_tickets_by_session(session_id)

        # Group by entity_group
        groups = {}
        for ticket in tickets:
            group = ticket.entity_group
            if group not in groups:
                groups[group] = {"total": 0, "ready": 0, "exported": 0}
            groups[group]["total"] += 1
            if ticket.ready_for_jira:
                groups[group]["ready"] += 1
            if ticket.is_exported:
                groups[group]["exported"] += 1

        return {
            "total_tickets": len(tickets),
            "ready_for_export": sum(1 for t in tickets if t.ready_for_jira),
            "exported": sum(1 for t in tickets if t.is_exported),
            "by_entity_group": groups,
        }

    async def update_ticket_order(
        self,
        session_id: UUID,
        order_updates: List[dict],
    ) -> None:
        """Update ticket ordering."""
        for update_info in order_updates:
            ticket_id = update_info["ticket_id"]
            new_order = update_info["user_order"]
            await self.update_ticket(ticket_id, {"user_order": new_order})

    async def bulk_assign_tickets(
        self,
        ticket_ids: List[UUID],
        assignments: dict,
    ) -> int:
        """Bulk assign tickets."""
        count = 0
        for ticket_id in ticket_ids:
            ticket = await self.update_ticket(ticket_id, assignments)
            if ticket:
                count += 1
        return count

    async def bulk_update_tickets(
        self,
        ticket_ids: List[UUID],
        updates: dict,
    ) -> int:
        """Bulk update tickets."""
        count = 0
        for ticket_id in ticket_ids:
            ticket = await self.update_ticket(ticket_id, updates)
            if ticket:
                count += 1
        return count

    async def get_export_ready_tickets(self, session_id: UUID) -> List[Ticket]:
        """Get all tickets marked ready for export."""
        stmt = (
            select(Ticket)
            .where(
                Ticket.session_id == session_id,
                Ticket.ready_for_jira == True,
            )
            .order_by(Ticket.entity_group, Ticket.user_order)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_tickets_in_dependency_order(self, session_id: UUID) -> List[Ticket]:
        """Get tickets ordered by dependencies (topological sort)."""
        tickets = await self.get_tickets_by_session(session_id)
        if not tickets:
            return []

        # Build dependency graph
        ticket_map = {t.id: t for t in tickets}
        deps_map = {}

        for ticket in tickets:
            deps = await self.get_dependencies_for_ticket(ticket.id)
            deps_map[ticket.id] = set(deps)

        # Topological sort using Kahn's algorithm
        in_degree = {t.id: 0 for t in tickets}
        for ticket_id, deps in deps_map.items():
            in_degree[ticket_id] = len(deps)

        # Start with tickets that have no dependencies
        queue = [t_id for t_id, degree in in_degree.items() if degree == 0]
        result = []

        while queue:
            current = queue.pop(0)
            result.append(ticket_map[current])

            # Find tickets that depend on current
            for ticket_id, deps in deps_map.items():
                if current in deps:
                    in_degree[ticket_id] -= 1
                    if in_degree[ticket_id] == 0:
                        queue.append(ticket_id)

        # If we didn't process all tickets, there's a cycle
        if len(result) != len(tickets):
            # Fall back to regular order for cycles
            return tickets

        return result

    async def mark_ticket_exported(
        self,
        ticket_id: UUID,
        jira_key: str,
        jira_url: str,
    ) -> None:
        """Mark ticket as exported to Jira."""
        ticket = await self.get_ticket_by_id(ticket_id)
        if ticket:
            ticket.set_jira_export_data(jira_key, jira_url)
            await self.db.flush()

    async def create_dependency(
        self,
        ticket_id: UUID,
        depends_on_ticket_id: UUID,
    ) -> TicketDependency:
        """Create a dependency between tickets."""
        dependency = TicketDependency(
            ticket_id=ticket_id,
            depends_on_ticket_id=depends_on_ticket_id,
        )
        self.db.add(dependency)
        await self.db.flush()
        return dependency

    async def remove_dependency(
        self,
        ticket_id: UUID,
        depends_on_ticket_id: UUID,
    ) -> None:
        """Remove a dependency between tickets."""
        stmt = delete(TicketDependency).where(
            TicketDependency.ticket_id == ticket_id,
            TicketDependency.depends_on_ticket_id == depends_on_ticket_id,
        )
        await self.db.execute(stmt)
        await self.db.flush()

    async def get_dependencies_for_ticket(self, ticket_id: UUID) -> List[UUID]:
        """Get list of ticket IDs that this ticket depends on."""
        stmt = select(TicketDependency.depends_on_ticket_id).where(
            TicketDependency.ticket_id == ticket_id
        )
        result = await self.db.execute(stmt)
        return [row[0] for row in result.all()]

    async def get_dependents_for_ticket(self, ticket_id: UUID) -> List[UUID]:
        """Get list of ticket IDs that depend on this ticket."""
        stmt = select(TicketDependency.ticket_id).where(
            TicketDependency.depends_on_ticket_id == ticket_id
        )
        result = await self.db.execute(stmt)
        return [row[0] for row in result.all()]

    async def has_circular_dependency(
        self,
        ticket_id: UUID,
        depends_on_id: UUID,
    ) -> bool:
        """Check if adding dependency would create circular reference."""
        # Check if depends_on_id already depends on ticket_id (directly or indirectly)
        visited: Set[UUID] = set()
        queue = [depends_on_id]

        while queue:
            current = queue.pop(0)
            if current == ticket_id:
                return True

            if current in visited:
                continue
            visited.add(current)

            deps = await self.get_dependencies_for_ticket(current)
            queue.extend(deps)

        return False

    async def get_dependency_graph(self, session_id: UUID) -> dict:
        """Get complete dependency graph for session."""
        tickets = await self.get_tickets_by_session(session_id)

        graph = {
            "nodes": [],
            "edges": [],
        }

        for ticket in tickets:
            graph["nodes"].append({
                "id": str(ticket.id),
                "title": ticket.title,
                "entity_group": ticket.entity_group,
            })

            deps = await self.get_dependencies_for_ticket(ticket.id)
            for dep_id in deps:
                graph["edges"].append({
                    "from": str(ticket.id),
                    "to": str(dep_id),
                })

        return graph

    async def create_attachment(self, attachment_data: dict) -> Attachment:
        """Create an attachment for a ticket."""
        attachment = Attachment(
            session_id=attachment_data["session_id"],
            ticket_id=attachment_data["ticket_id"],
            filename=attachment_data["filename"],
            content=attachment_data["content"],
            file_size_bytes=attachment_data["file_size_bytes"],
            jira_upload_status=attachment_data.get(
                "jira_upload_status",
                JiraUploadStatus.PENDING.value,
            ),
        )
        self.db.add(attachment)
        await self.db.flush()
        return attachment

    async def get_attachment_by_ticket(self, ticket_id: UUID) -> Optional[Attachment]:
        """Get attachment for a ticket."""
        stmt = select(Attachment).where(Attachment.ticket_id == ticket_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def mark_attachment_uploaded(
        self,
        attachment_id: UUID,
        jira_attachment_id: str,
    ) -> None:
        """Mark attachment as uploaded to Jira."""
        stmt = (
            update(Attachment)
            .where(Attachment.id == attachment_id)
            .values(
                jira_upload_status=JiraUploadStatus.UPLOADED.value,
                jira_attachment_id=jira_attachment_id,
            )
        )
        await self.db.execute(stmt)
        await self.db.flush()

    async def get_pending_attachments(self, session_id: UUID) -> List[Attachment]:
        """Get all attachments pending upload."""
        stmt = (
            select(Attachment)
            .where(
                Attachment.session_id == session_id,
                Attachment.jira_upload_status == JiraUploadStatus.PENDING.value,
            )
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
