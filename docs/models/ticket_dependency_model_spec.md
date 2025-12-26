# TicketDependency Model - SQLAlchemy Implementation Specification

## 1. Class Name
**TicketDependency** - Ticket relationship tracking for implementation ordering

## 2. Directory Path
`/backend/app/models/ticket.py` (same file as Ticket for related models)

## 3. Purpose & Responsibilities
- Track dependencies between tickets for proper implementation ordering
- Support both automatic dependency detection and user-defined relationships
- Enable dependency validation and circular dependency detection
- Provide dependency graph data for review interface

## 4. Methods and Properties

### Core Fields (3 total)
```python
ticket_id: UUID (foreign key to tickets, part of composite primary key)
depends_on_ticket_id: UUID (foreign key to tickets, part of composite primary key)  
created_at: datetime
```

### Class Methods
```python
@classmethod
def get_dependencies_for_ticket(cls, ticket_id: UUID) -> List[UUID]:
    # Get list of ticket IDs that this ticket depends on

@classmethod
def get_dependents_for_ticket(cls, ticket_id: UUID) -> List[UUID]:
    # Get list of ticket IDs that depend on this ticket

@classmethod
def has_circular_dependency(cls, ticket_id: UUID, depends_on_id: UUID) -> bool:
    # Check if adding this dependency would create a circular reference

@classmethod
def get_dependency_graph_for_session(cls, session_id: UUID) -> dict:
    # Get complete dependency graph for session (for UI visualization)
```

## 5. Dependencies/Imports
```python
from sqlalchemy import Column, ForeignKey, DateTime, PrimaryKeyConstraint, CheckConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from typing import List, Dict
```

## 6. Database Integration

### Table Definition
```python
__tablename__ = "ticket_dependencies"
__table_args__ = (
    PrimaryKeyConstraint('ticket_id', 'depends_on_ticket_id'),
    CheckConstraint('ticket_id != depends_on_ticket_id', name='ck_no_self_dependency'),
    Index('idx_ticket_dependencies_ticket_id', 'ticket_id'),
    Index('idx_ticket_dependencies_depends_on', 'depends_on_ticket_id')
)
```

### Foreign Keys
```python
ticket_id = Column(UUID(as_uuid=True), ForeignKey('tickets.id', ondelete='CASCADE'), nullable=False)
depends_on_ticket_id = Column(UUID(as_uuid=True), ForeignKey('tickets.id', ondelete='CASCADE'), nullable=False)
```

### Transaction Strategy
- Participates in repository-managed transactions
- Cascading delete ensures cleanup when tickets are deleted
- Bulk operations for dependency updates during review stage

## 7. Logging Events

### Dependency Lifecycle
- **INFO**: Dependency creation and removal with ticket context
- **DEBUG**: Dependency graph analysis and circular dependency detection
- **AUDIT**: User dependency modifications during review stage

### Specific Logging
- **INFO**: `Dependency created: ticket {ticket_id} depends on {depends_on_ticket_id} (session: {session_id})`
- **WARNING**: `Circular dependency detected between tickets {ticket_a} and {ticket_b}`
- **DEBUG**: Dependency graph analysis for ordering validation

## 8. Error Handling

### Error Categories
- **user_fixable**: Circular dependencies, invalid ticket references
- **admin_required**: Database constraint violations, system issues
- **temporary**: Database lock timeouts during bulk operations

### Specific Error Patterns
```python
# Self-dependency prevention (caught by database constraint)
try:
    session.add(TicketDependency(ticket_id=id, depends_on_ticket_id=id))
except IntegrityError as e:
    if "ck_no_self_dependency" in str(e):
        raise DependencyValidationError(
            message="Ticket cannot depend on itself",
            category="user_fixable"
        )
```

## Key Design Decisions

### Composite Primary Key
- Uses ticket_id + depends_on_ticket_id as composite primary key
- Naturally prevents duplicate dependency relationships
- Simpler than UUID primary key for pure junction table
- Efficient for many-to-many relationship queries

### Database Constraints
- Check constraint prevents self-referencing dependencies at database level
- Provides data integrity defense in depth beyond application logic
- Documents business rules clearly in schema

### Index Strategy
- Indexes on both foreign keys for efficient dependency lookups
- Supports both "what does this depend on" and "what depends on this" queries
- Essential for dependency graph traversal and circular dependency detection

### Cascading Delete Strategy
- Dependencies automatically cleaned up when tickets are deleted
- Maintains referential integrity during session cleanup
- Simplifies maintenance with automatic orphan prevention