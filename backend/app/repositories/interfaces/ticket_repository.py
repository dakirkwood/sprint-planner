"""Ticket repository interface."""

from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from app.models.ticket import Ticket, TicketDependency, Attachment


class TicketRepositoryInterface(ABC):
    """Interface for ticket repository operations."""

    # Ticket CRUD
    @abstractmethod
    async def create_ticket(self, ticket_data: dict) -> Ticket:
        """Create a new ticket."""
        pass

    @abstractmethod
    async def get_ticket_by_id(self, ticket_id: UUID) -> Optional[Ticket]:
        """Get ticket by ID."""
        pass

    @abstractmethod
    async def get_tickets_by_session(self, session_id: UUID) -> List[Ticket]:
        """Get all tickets for a session."""
        pass

    @abstractmethod
    async def update_ticket(self, ticket_id: UUID, updates: dict) -> Optional[Ticket]:
        """Update ticket fields."""
        pass

    @abstractmethod
    async def delete_tickets_by_session(self, session_id: UUID) -> int:
        """Delete all tickets for a session. Returns count deleted."""
        pass

    # Review Interface Support
    @abstractmethod
    async def get_tickets_by_entity_group(
        self,
        session_id: UUID,
        entity_group: str,
    ) -> List[Ticket]:
        """Get tickets for specific entity group."""
        pass

    @abstractmethod
    async def get_tickets_summary(self, session_id: UUID) -> dict:
        """Get ticket summary for session."""
        pass

    @abstractmethod
    async def update_ticket_order(
        self,
        session_id: UUID,
        order_updates: List[dict],
    ) -> None:
        """Update ticket ordering."""
        pass

    # Bulk Operations
    @abstractmethod
    async def bulk_assign_tickets(
        self,
        ticket_ids: List[UUID],
        assignments: dict,
    ) -> int:
        """Bulk assign tickets. Returns count updated."""
        pass

    @abstractmethod
    async def bulk_update_tickets(
        self,
        ticket_ids: List[UUID],
        updates: dict,
    ) -> int:
        """Bulk update tickets. Returns count updated."""
        pass

    # Export Support
    @abstractmethod
    async def get_export_ready_tickets(self, session_id: UUID) -> List[Ticket]:
        """Get all tickets marked ready for export."""
        pass

    @abstractmethod
    async def get_tickets_in_dependency_order(self, session_id: UUID) -> List[Ticket]:
        """Get tickets ordered by dependencies."""
        pass

    @abstractmethod
    async def mark_ticket_exported(
        self,
        ticket_id: UUID,
        jira_key: str,
        jira_url: str,
    ) -> None:
        """Mark ticket as exported to Jira."""
        pass

    # Dependency Operations
    @abstractmethod
    async def create_dependency(
        self,
        ticket_id: UUID,
        depends_on_ticket_id: UUID,
    ) -> TicketDependency:
        """Create a dependency between tickets."""
        pass

    @abstractmethod
    async def remove_dependency(
        self,
        ticket_id: UUID,
        depends_on_ticket_id: UUID,
    ) -> None:
        """Remove a dependency between tickets."""
        pass

    @abstractmethod
    async def get_dependencies_for_ticket(self, ticket_id: UUID) -> List[UUID]:
        """Get list of ticket IDs that this ticket depends on."""
        pass

    @abstractmethod
    async def get_dependents_for_ticket(self, ticket_id: UUID) -> List[UUID]:
        """Get list of ticket IDs that depend on this ticket."""
        pass

    @abstractmethod
    async def has_circular_dependency(
        self,
        ticket_id: UUID,
        depends_on_id: UUID,
    ) -> bool:
        """Check if adding dependency would create circular reference."""
        pass

    @abstractmethod
    async def get_dependency_graph(self, session_id: UUID) -> dict:
        """Get complete dependency graph for session."""
        pass

    # Attachment Operations
    @abstractmethod
    async def create_attachment(self, attachment_data: dict) -> Attachment:
        """Create an attachment for a ticket."""
        pass

    @abstractmethod
    async def get_attachment_by_ticket(self, ticket_id: UUID) -> Optional[Attachment]:
        """Get attachment for a ticket."""
        pass

    @abstractmethod
    async def mark_attachment_uploaded(
        self,
        attachment_id: UUID,
        jira_attachment_id: str,
    ) -> None:
        """Mark attachment as uploaded to Jira."""
        pass

    @abstractmethod
    async def get_pending_attachments(self, session_id: UUID) -> List[Attachment]:
        """Get all attachments pending upload."""
        pass
