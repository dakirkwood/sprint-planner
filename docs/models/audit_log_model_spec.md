# AuditLog Model - SQLAlchemy Implementation Specification

## 1. Class Name
**AuditLog** - Comprehensive audit trail for user actions and system events

## 2. Directory Path
`/backend/app/models/error.py` (same file as SessionError for related audit functionality)

## 3. Purpose & Responsibilities
- Track all significant user actions and system events
- Provide detailed audit trail with 90-day retention (longer than sessions)
- Enable debugging, compliance, and user behavior analysis
- Support both basic and comprehensive audit levels
- Store performance metrics and request correlation data

## 4. Methods and Properties

### Core Fields (14 total)
```python
id: UUID (primary key)
session_id: Optional[UUID]  # Foreign key to sessions, nullable for system events
jira_user_id: Optional[str]  # User who performed action, nullable for system events
event_type: str  # 'session_created', 'file_uploaded', 'ticket_edited', etc.
event_category: EventCategory  # enum: 'session', 'upload', 'processing', 'review', 'jira_export', 'system'
audit_level: AuditLevel  # enum: 'basic', 'comprehensive' (for filtering/cleanup)
description: str  # Human-readable event description
entity_type: Optional[str]  # 'session', 'ticket', 'file', etc.
entity_id: Optional[str]  # ID of affected entity
event_data: Optional[dict]  # JSON: API responses, form data, etc. (comprehensive mode)
request_id: Optional[str]  # Link to specific HTTP request
execution_time_ms: Optional[int]  # Performance tracking
ip_address: Optional[str]  # User context
user_agent: Optional[str]  # User context
created_at: datetime
```

### Enum Definitions
```python
class EventCategory(str, Enum):
    SESSION = "session"
    UPLOAD = "upload"
    PROCESSING = "processing"
    REVIEW = "review"
    JIRA_EXPORT = "jira_export"
    SYSTEM = "system"

class AuditLevel(str, Enum):
    BASIC = "basic"
    COMPREHENSIVE = "comprehensive"
```

### Class Methods
```python
@classmethod
def log_event(cls, event_type: str, category: EventCategory, description: str, 
              session_id: Optional[UUID] = None, jira_user_id: Optional[str] = None,
              entity_type: Optional[str] = None, entity_id: Optional[str] = None,
              event_data: Optional[dict] = None) -> 'AuditLog':
    # Create audit log entry with automatic audit level detection

@classmethod
def get_session_timeline(cls, session_id: UUID) -> List['AuditLog']:
    # Get chronological audit trail for session

@classmethod
def get_user_activity(cls, jira_user_id: str, days: int = 30) -> List['AuditLog']:
    # Get user activity over specified time period

@classmethod
def cleanup_by_retention(cls, retention_days: int = 90) -> int:
    # Clean up old audit logs, return count deleted
```

### Properties
```python
@property
def is_comprehensive(self) -> bool:
    return self.audit_level == AuditLevel.COMPREHENSIVE

@property
def age_days(self) -> float:
    # How many days ago this event occurred

@property
def has_performance_data(self) -> bool:
    # True if execution_time_ms is not None
```

## 5. Dependencies/Imports
```python
from sqlalchemy import Column, String, Text, Integer, ForeignKey, DateTime, Enum as SQLEnum, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum
from typing import List, Dict, Optional
import uuid
```

## 6. Database Integration

### Table Definition
```python
__tablename__ = "audit_log"
__table_args__ = (
    Index('idx_audit_log_session_id', 'session_id'),
    Index('idx_audit_log_jira_user_id', 'jira_user_id'),
    Index('idx_audit_log_event_category', 'event_category'),
    Index('idx_audit_log_audit_level', 'audit_level'),
    Index('idx_audit_log_created_at', 'created_at')
)
```

### Relationships
```python
session = relationship("Session", back_populates="audit_events")  # Handles nullable FK gracefully
```

### Foreign Key
```python
session_id = Column(UUID(as_uuid=True), ForeignKey('sessions.id', ondelete='SET NULL'), nullable=True)
```

### Transaction Strategy
- Participates in repository-managed transactions
- Created for significant user actions and system events
- 90-day retention (independent of session cleanup)
- SET NULL preserves audit trail after session deletion

## 7. Logging Events

### Audit Lifecycle
- **INFO**: Audit log creation for major system events
- **DEBUG**: Audit log performance and data size tracking
- **WARNING**: Audit log cleanup operations and retention policy execution

### Specific Logging
- **INFO**: `AuditLog event recorded: {event_type} for session {session_id} user {jira_user_id}`
- **DEBUG**: `Audit event data size: {event_data_size}KB, execution time: {execution_time_ms}ms`
- **WARNING**: `Audit log cleanup: deleted {count} records older than {retention_days} days`

## 8. Error Handling

### Error Categories
- **user_fixable**: Generally none - audit logs are system-generated
- **admin_required**: Database storage issues, audit system failures
- **temporary**: Database connectivity during audit logging

### Specific Error Patterns
```python
# Audit data validation
if not self.description or len(self.description.strip()) == 0:
    raise AuditValidationError(
        message="Audit event must have description",
        category="admin_required"  # System bug
    )

# Event data size limits (for comprehensive mode)
if self.event_data and len(str(self.event_data)) > 100_000:  # 100KB JSON limit
    raise AuditValidationError(
        message="Audit event data too large",
        category="admin_required"
    )
```

## Key Design Decisions

### Extended Retention Strategy
- **90-day retention**: Longer than sessions for compliance and debugging
- **Independent cleanup**: Survives session deletion via SET NULL foreign key
- **Configurable levels**: Basic vs comprehensive audit based on environment variables

### Performance and Debugging Features
- **Request correlation**: Links audit events to specific HTTP requests
- **Execution timing**: Performance metrics for slow operation analysis
- **User context**: IP address and user agent for security analysis

### Flexible Event Storage
- **JSON event data**: Comprehensive mode stores full context (API responses, form data)
- **Enum categorization**: Type-safe event categories aligned with workflow stages
- **Entity linking**: Flexible entity_type/entity_id for relating events to affected resources

### Database Optimization
- **Comprehensive indexing**: Supports various audit query patterns
- **Nullable relationships**: Graceful handling of system events and session cleanup
- **Size limits**: Prevents excessive JSON storage in comprehensive mode