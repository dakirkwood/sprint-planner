# app/repositories/interfaces/ticket_repository.py
"""
Ticket repository interface.
Aggregate repository for Ticket, TicketDependency, and Attachment models.
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict
from uuid import UUID

from app.models.ticket import Ticket, TicketDependency, Attachment


class TicketRepositoryInterface(ABC):
    """
    Interface for ticket repository operations.
    Handles Ticket + TicketDependency + Attachment as an aggregate.
    """

    # ==========================================================================
    # Ticket CRUD Operations
    # ==========================================================================

    @abstractmethod
    async def create_ticket(self, ticket_data: dict) -> Ticket:
        """Create a new ticket."""
        pass

    @abstractmethod
    async def get_ticket_by_id(self, ticket_id: UUID) -> Optional[Ticket]:
        """Get ticket by ID, including attachment and dependencies."""
        pass

    @abstractmethod
    async def get_tickets_by_session(self, session_id: UUID) -> List[Ticket]:
        """Get all tickets for a session."""
        pass

    @abstractmethod
    async def update_ticket(self, ticket_id: UUID, updates: dict) -> Ticket:
        """Update ticket fields."""
        pass

    @abstractmethod
    async def delete_tickets_by_session(self, session_id: UUID) -> int:
        """Delete all tickets for a session. Returns count deleted."""
        pass

    # ==========================================================================
    # Review Interface Support
    # ==========================================================================

    @abstractmethod
    async def get_tickets_by_entity_group(self, session_id: UUID, entity_group: str) -> List[Ticket]:
        """Get tickets for a specific entity group, ordered by user_order."""
        pass

    @abstractmethod
    async def get_tickets_summary(self, session_id: UUID) -> dict:
        """Get summary of tickets by entity group."""
        pass

    @abstractmethod
    async def update_ticket_order(self, session_id: UUID, order_updates: List[dict]) -> None:
        """Update user_order for multiple tickets."""
        pass

    # ==========================================================================
    # Bulk Operations
    # ==========================================================================

    @abstractmethod
    async def bulk_assign_tickets(self, ticket_ids: List[UUID], assignments: dict) -> int:
        """Assign sprint/assignee to multiple tickets. Returns count updated."""
        pass

    @abstractmethod
    async def bulk_update_tickets(self, ticket_ids: List[UUID], updates: dict) -> int:
        """Update fields for multiple tickets. Returns count updated."""
        pass

    # ==========================================================================
    # Export Support
    # ==========================================================================

    @abstractmethod
    async def get_export_ready_tickets(self, session_id: UUID) -> List[Ticket]:
        """Get tickets marked ready for Jira export."""
        pass

    @abstractmethod
    async def get_tickets_in_dependency_order(self, session_id: UUID) -> List[Ticket]:
        """Get export-ready tickets in dependency order (dependencies first)."""
        pass

    @abstractmethod
    async def mark_ticket_exported(self, ticket_id: UUID, jira_key: str, jira_url: str) -> None:
        """Mark ticket as exported with Jira details."""
        pass

    # ==========================================================================
    # Dependency Operations
    # ==========================================================================

    @abstractmethod
    async def create_dependency(self, ticket_id: UUID, depends_on_ticket_id: UUID) -> TicketDependency:
        """Create a dependency between tickets."""
        pass

    @abstractmethod
    async def remove_dependency(self, ticket_id: UUID, depends_on_ticket_id: UUID) -> None:
        """Remove a dependency between tickets."""
        pass

    @abstractmethod
    async def get_dependencies_for_ticket(self, ticket_id: UUID) -> List[UUID]:
        """Get IDs of tickets that this ticket depends on."""
        pass

    @abstractmethod
    async def get_dependents_for_ticket(self, ticket_id: UUID) -> List[UUID]:
        """Get IDs of tickets that depend on this ticket."""
        pass

    @abstractmethod
    async def has_circular_dependency(self, ticket_id: UUID, depends_on_id: UUID) -> bool:
        """Check if adding dependency would create a cycle."""
        pass

    @abstractmethod
    async def get_dependency_graph(self, session_id: UUID) -> dict:
        """Get complete dependency graph for session."""
        pass

    # ==========================================================================
    # Attachment Operations
    # ==========================================================================

    @abstractmethod
    async def create_attachment(self, attachment_data: dict) -> Attachment:
        """Create attachment for a ticket."""
        pass

    @abstractmethod
    async def get_attachment_by_ticket(self, ticket_id: UUID) -> Optional[Attachment]:
        """Get attachment for a ticket."""
        pass

    @abstractmethod
    async def mark_attachment_uploaded(self, attachment_id: UUID, jira_attachment_id: str) -> None:
        """Mark attachment as uploaded to Jira."""
        pass

    @abstractmethod
    async def get_pending_attachments(self, session_id: UUID) -> List[Attachment]:
        """Get attachments pending upload for a session."""
        pass
