# Ticket Model - SQLAlchemy Implementation Specification

## UPDATED: December 25, 2025
- Removed `attachment_id` foreign key field to eliminate circular FK with Attachment model
- Attachment is now accessed only via SQLAlchemy relationship (Attachment.ticket_id is the FK)
- Updated field count from 15 to 14

---

## 1. Class Name
**Ticket** - Generated ticket content and metadata for Jira export

## 2. Directory Path
`/backend/app/models/ticket.py` (new file for ticket-related models)

## 3. Purpose & Responsibilities
- Store generated ticket content (title, description, user notes)
- Track CSV source references for debugging and audit
- Maintain project management assignments (sprint, assignee)
- Handle export state and Jira integration data
- Manage entity grouping and ordering for review interface

## 4. Methods and Properties

### Core Fields (14 total)
```python
id: UUID (primary key)
session_id: UUID (foreign key to sessions)
title: str
description: str  # Combined Issue/Analysis/Verification sections
csv_source_files: dict  # JSON: [{filename: "bundles.csv", rows: [1,2,3]}]
entity_group: str  # 'Content', 'Media', 'Views', 'Migration', 'Workflow', 'User Roles', 'Custom'
user_order: int  # Within entity group
ready_for_jira: bool = False
sprint: Optional[str]
assignee: Optional[str]
user_notes: Optional[str]
jira_ticket_key: Optional[str]  # Set after export
jira_ticket_url: Optional[str]  # Set after export
created_at: datetime
updated_at: datetime
```

**Note:** `attachment_id` is NOT stored on Ticket. The 1:1 relationship is navigated via `ticket.attachment` using SQLAlchemy relationship, with the FK living on the Attachment model (`Attachment.ticket_id`).

### Instance Methods
```python
def mark_ready_for_jira(self) -> None:
    # Set ready_for_jira flag and update timestamp

def add_csv_source_reference(self, filename: str, rows: List[int]) -> None:
    # Add or update CSV source tracking

def set_jira_export_data(self, jira_key: str, jira_url: str) -> None:
    # Store Jira ticket information after successful export

@classmethod
def find_by_entity_group(cls, session_id: UUID, entity_group: str) -> List['Ticket']:
    # Get tickets for specific entity group, ordered by user_order

@classmethod
def get_export_ready_count(cls, session_id: UUID) -> int:
    # Count tickets marked ready for export
```

### Properties
```python
@property
def character_count(self) -> int:
    # Description length for attachment threshold checking

@property
def is_exported(self) -> bool:
    # True if jira_ticket_key is not None

@property
def needs_attachment(self) -> bool:
    # True if description exceeds Jira character limits (~30k)

@property
def has_attachment(self) -> bool:
    # True if self.attachment is not None

@property
def csv_source_summary(self) -> str:
    # Human-readable CSV source description for UI
```

## 5. Dependencies/Imports
```python
from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import List, Dict, Optional
import uuid
```

## 6. Database Integration

### Table Definition
```python
__tablename__ = "tickets"
__table_args__ = (
    Index('idx_tickets_session_id', 'session_id'),
    Index('idx_tickets_entity_group', 'entity_group'),
    Index('idx_tickets_ready_for_jira', 'ready_for_jira')
)
```

### Relationships
```python
# Parent relationship
session = relationship("Session", back_populates="tickets")

# 1:1 relationship to attachment (FK lives on Attachment side)
attachment = relationship("Attachment", back_populates="ticket", uselist=False)

# Self-referential dependencies via junction table
dependencies = relationship(
    "TicketDependency",
    foreign_keys="TicketDependency.ticket_id",
    back_populates="dependent_ticket",
    cascade="all, delete-orphan"
)
depends_on = relationship(
    "TicketDependency",
    foreign_keys="TicketDependency.depends_on_ticket_id",
    back_populates="dependency_ticket",
    cascade="all, delete-orphan"
)
```

### Foreign Keys
```python
session_id = Column(UUID(as_uuid=True), ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False)
# NOTE: No attachment_id FK here - the FK lives on Attachment.ticket_id
```

### Transaction Strategy
- Participates in repository-managed transactions
- Updated frequently during review stage (auto-save)
- Cascading delete with parent session and any attachments

## 7. Logging Events

### Ticket Lifecycle
- **INFO**: Ticket creation and major updates with session context
- **DEBUG**: Content changes, CSV source tracking updates  
- **AUDIT**: Export state changes, Jira integration success/failure

### Specific Logging
- **INFO**: `Ticket created for session {session_id}: {title} (entity_group: {entity_group})`
- **INFO**: `Ticket exported to Jira: {title} â†’ {jira_key} (session: {session_id})`
- **DEBUG**: Character count changes, attachment generation events
- **AUDIT**: Ready-for-jira status changes, user order modifications

## 8. Error Handling

### Error Categories
- **user_fixable**: Content validation issues, invalid assignments
- **admin_required**: Jira integration failures, system issues
- **temporary**: Export timeouts, service unavailable

### Specific Error Patterns
```python
# Content size validation
if len(self.description) > 32000:  # Approaching Jira limit
    raise TicketValidationError(
        message=f"Ticket content too large: {len(self.description)} characters",
        category="user_fixable"
    )

# Export state validation
if not self.ready_for_jira and attempting_export:
    raise TicketValidationError(
        message="Ticket not marked ready for Jira export",
        category="user_fixable"
    )
```

## Key Design Decisions

### Single Description Field
- Combined Issue/Analysis/Verification sections in one TEXT field
- Simplifies ticket management - from ticket perspective, it's just content for Jira
- Internal sectioning is generation detail, not storage concern

### Entity Group as String
- Flexible accommodation of custom entity groups
- New groups added through code updates, no database migrations
- Standard groups: 'Content', 'Media', 'Views', 'Migration', 'Workflow', 'User Roles', 'Custom'

### 1:1 Attachment Relationship Pattern
- **No `attachment_id` on Ticket**: Avoids circular FK between Ticket and Attachment
- **FK lives on Attachment**: `Attachment.ticket_id` references `tickets.id`
- **Navigation via relationship**: Access attachment as `ticket.attachment`
- **Simpler inserts**: Create Ticket first, then Attachment referencing it
- **Standard pattern**: Child (Attachment) references parent (Ticket)

### Index Strategy
- Session and entity group indexes for review interface queries
- Ready-for-jira index for export readiness queries
- No user_order index - sorting small result sets in memory is sufficient for expected volumes

### Cascading Delete Strategy
- Session deletion removes all tickets (7-day cleanup)
- Ticket deletion cascades to attachment (via Attachment.ticket_id FK with ondelete='CASCADE')
- Clean automated cleanup with comprehensive audit trail preservation
