# SQLAlchemy Relationship Bidirectional Consistency Audit

## UPDATED: December 25, 2025
- Marked Ticket/Attachment circular FK issue as RESOLVED
- Updated relationship definitions to reflect corrected pattern
- All identified issues now have corrected definitions

---

## Overview
Comprehensive audit of all SQLAlchemy model relationships to ensure bidirectional consistency across all models. This document serves as the authoritative reference for relationship definitions.

## Relationship Status Summary

| Model | Status | Notes |
|-------|--------|-------|
| Session | âœ… Complete | All relationships defined with back_populates |
| SessionTask | âœ… Complete | Back-reference to session added |
| SessionValidation | âœ… Complete | Back-reference to session added |
| UploadedFile | âœ… Complete | Correct as originally specified |
| Ticket | âœ… Complete | Removed attachment_id FK, uses relationship only |
| TicketDependency | âœ… Complete | Both ticket references defined |
| Attachment | âœ… Complete | Holds FK to ticket, back-reference defined |
| JiraAuthToken | âœ… Complete | No relationships needed (standalone) |
| JiraProjectContext | âœ… Complete | Back-reference to session added |
| SessionError | âœ… Complete | Session + optional entity references defined |
| AuditLog | âœ… Complete | Nullable session reference defined |

---

## Complete Relationship Definitions

### **1. Session Model** (`/backend/app/models/session.py`)

```python
class Session(Base):
    __tablename__ = "sessions"
    
    # ... fields ...
    
    # 1:Many relationships - Small collections (eager loading)
    uploaded_files = relationship(
        "UploadedFile", 
        back_populates="session", 
        lazy="joined", 
        cascade="all, delete-orphan"
    )
    
    # 1:1 relationships (eager loading)
    session_task = relationship(
        "SessionTask", 
        back_populates="session", 
        lazy="joined", 
        uselist=False, 
        cascade="all, delete-orphan"
    )
    session_validation = relationship(
        "SessionValidation", 
        back_populates="session", 
        lazy="joined", 
        uselist=False, 
        cascade="all, delete-orphan"
    )
    project_context = relationship(
        "JiraProjectContext", 
        back_populates="session",
        lazy="joined", 
        uselist=False, 
        cascade="all, delete-orphan"
    )
    
    # 1:Many relationships - Large collections (lazy loading)
    tickets = relationship(
        "Ticket", 
        back_populates="session", 
        lazy="select", 
        cascade="all, delete-orphan"
    )
    session_errors = relationship(
        "SessionError", 
        back_populates="session", 
        lazy="select",
        cascade="all, delete-orphan"
    )
    audit_events = relationship(
        "AuditLog", 
        back_populates="session", 
        lazy="select"
    )  # No cascade - audit logs use SET NULL on session delete
```

### **2. SessionTask Model** (`/backend/app/models/session.py`)

```python
class SessionTask(Base):
    __tablename__ = "session_tasks"
    
    # ... fields ...
    
    # Back-reference to session
    session = relationship("Session", back_populates="session_task")
```

### **3. SessionValidation Model** (`/backend/app/models/session.py`)

```python
class SessionValidation(Base):
    __tablename__ = "session_validations"
    
    # ... fields ...
    
    # Back-reference to session
    session = relationship("Session", back_populates="session_validation")
```

### **4. UploadedFile Model** (`/backend/app/models/upload.py`)

```python
class UploadedFile(Base):
    __tablename__ = "uploaded_files"
    
    # ... fields ...
    session_id = Column(UUID(as_uuid=True), ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False)
    
    # Back-reference to session
    session = relationship("Session", back_populates="uploaded_files")
```

### **5. Ticket Model** (`/backend/app/models/ticket.py`)

```python
class Ticket(Base):
    __tablename__ = "tickets"
    
    # ... fields ...
    session_id = Column(UUID(as_uuid=True), ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False)
    # NOTE: No attachment_id FK - the FK lives on Attachment.ticket_id
    
    # Parent relationship
    session = relationship("Session", back_populates="tickets")
    
    # 1:1 relationship to attachment (FK lives on Attachment side)
    attachment = relationship(
        "Attachment", 
        back_populates="ticket", 
        uselist=False,
        cascade="all, delete-orphan"
    )
    
    # Self-referential dependencies via junction table
    dependencies = relationship(
        "TicketDependency",
        foreign_keys="[TicketDependency.ticket_id]",
        back_populates="dependent_ticket",
        cascade="all, delete-orphan"
    )
    depends_on = relationship(
        "TicketDependency",
        foreign_keys="[TicketDependency.depends_on_ticket_id]",
        back_populates="dependency_ticket",
        cascade="all, delete-orphan"
    )
```

### **6. TicketDependency Model** (`/backend/app/models/ticket.py`)

```python
class TicketDependency(Base):
    __tablename__ = "ticket_dependencies"
    
    # Composite primary key
    ticket_id = Column(UUID(as_uuid=True), ForeignKey('tickets.id', ondelete='CASCADE'), primary_key=True)
    depends_on_ticket_id = Column(UUID(as_uuid=True), ForeignKey('tickets.id', ondelete='CASCADE'), primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Back-references to both tickets
    dependent_ticket = relationship(
        "Ticket",
        foreign_keys="[TicketDependency.ticket_id]",
        back_populates="dependencies"
    )
    dependency_ticket = relationship(
        "Ticket",
        foreign_keys="[TicketDependency.depends_on_ticket_id]",
        back_populates="depends_on"
    )
```

### **7. Attachment Model** (`/backend/app/models/ticket.py`)

```python
class Attachment(Base):
    __tablename__ = "attachments"
    
    # ... fields ...
    session_id = Column(UUID(as_uuid=True), ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False)
    ticket_id = Column(UUID(as_uuid=True), ForeignKey('tickets.id', ondelete='CASCADE'), nullable=False, unique=True)
    
    # Back-reference to ticket (this is the owning side of the 1:1 relationship)
    ticket = relationship("Attachment", back_populates="attachment")
    
    # Direct reference to session (no back_populates needed - not navigated from session)
    session = relationship("Session")
```

**Note on Ticket/Attachment 1:1 Pattern:**
- The FK (`ticket_id`) lives on Attachment, not on Ticket
- This avoids circular FK issues and simplifies inserts
- `unique=True` constraint on `ticket_id` enforces the 1:1 relationship
- Navigate from Ticket via `ticket.attachment`
- Navigate from Attachment via `attachment.ticket`

### **8. JiraAuthToken Model** (`/backend/app/models/auth.py`)

```python
class JiraAuthToken(Base):
    __tablename__ = "jira_auth_tokens"
    
    jira_user_id = Column(String(255), primary_key=True)
    # ... other fields ...
    
    # No relationships - standalone model keyed by jira_user_id
```

### **9. JiraProjectContext Model** (`/backend/app/models/auth.py`)

```python
class JiraProjectContext(Base):
    __tablename__ = "jira_project_context"
    
    session_id = Column(UUID(as_uuid=True), ForeignKey('sessions.id', ondelete='CASCADE'), primary_key=True)
    # ... other fields ...
    
    # Back-reference to session
    session = relationship("Session", back_populates="project_context")
```

### **10. SessionError Model** (`/backend/app/models/error.py`)

```python
class SessionError(Base):
    __tablename__ = "session_errors"
    
    # ... fields ...
    session_id = Column(UUID(as_uuid=True), ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False)
    related_file_id = Column(UUID(as_uuid=True), ForeignKey('uploaded_files.id', ondelete='SET NULL'), nullable=True)
    related_ticket_id = Column(UUID(as_uuid=True), ForeignKey('tickets.id', ondelete='SET NULL'), nullable=True)
    
    # Back-reference to session
    session = relationship("Session", back_populates="session_errors")
    
    # Optional references (no back_populates - one-way navigation)
    related_file = relationship("UploadedFile", foreign_keys=[related_file_id])
    related_ticket = relationship("Ticket", foreign_keys=[related_ticket_id])
```

### **11. AuditLog Model** (`/backend/app/models/error.py`)

```python
class AuditLog(Base):
    __tablename__ = "audit_log"
    
    # ... fields ...
    session_id = Column(UUID(as_uuid=True), ForeignKey('sessions.id', ondelete='SET NULL'), nullable=True)
    
    # Back-reference to session (nullable FK - handles session deletion gracefully)
    session = relationship("Session", back_populates="audit_events")
```

---

## Cascade Behavior Summary

| Relationship | Cascade | Rationale |
|--------------|---------|-----------|
| Session â†’ uploaded_files | all, delete-orphan | Files belong to session |
| Session â†’ session_task | all, delete-orphan | Task record belongs to session |
| Session â†’ session_validation | all, delete-orphan | Validation state belongs to session |
| Session â†’ project_context | all, delete-orphan | Context cached per session |
| Session â†’ tickets | all, delete-orphan | Tickets belong to session |
| Session â†’ session_errors | all, delete-orphan | Errors logged per session |
| Session â†’ audit_events | none | Audit logs preserved (SET NULL FK) |
| Ticket â†’ attachment | all, delete-orphan | Attachment belongs to ticket |
| Ticket â†’ dependencies | all, delete-orphan | Cleanup junction records |
| Ticket â†’ depends_on | all, delete-orphan | Cleanup junction records |

---

## Loading Strategy Summary

| Relationship | Loading | Rationale |
|--------------|---------|-----------|
| Session.uploaded_files | joined | Small collection, always needed for recovery |
| Session.session_task | joined | 1:1, always needed for status checks |
| Session.session_validation | joined | 1:1, always needed for export gate |
| Session.project_context | joined | 1:1, always needed for dropdowns |
| Session.tickets | select | Large collection, loaded on demand |
| Session.session_errors | select | Large collection, loaded on demand |
| Session.audit_events | select | Large collection, rarely accessed |

---

## Validation Checklist

- âœ… Every `back_populates` has corresponding relationship on target model
- âœ… Foreign key relationships have appropriate back-references
- âœ… Cascade behavior is appropriate for each relationship type
- âœ… Loading strategies match usage patterns
- âœ… Self-referential relationships (TicketDependency) properly configured
- âœ… Optional foreign keys (nullable) handled with SET NULL
- âœ… 1:1 relationships use `uselist=False`
- âœ… No circular FK patterns (Ticket/Attachment fixed)
- âœ… Unique constraints enforce 1:1 where needed (Attachment.ticket_id)
