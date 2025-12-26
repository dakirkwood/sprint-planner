# SessionError Model - SQLAlchemy Implementation Specification

## 1. Class Name
**SessionError** - Error tracking and storage for session workflow issues

## 2. Directory Path
`/backend/app/models/error.py` (new file for error and audit models)

## 3. Purpose & Responsibilities
- Store detailed error information with full context for debugging
- Track error categories using "who can fix it" classification
- Link errors to specific workflow stages, files, and tickets
- Enable error analysis and recovery guidance
- Provide audit trail for troubleshooting

## 4. Methods and Properties

### Core Fields (12 total)
```python
id: UUID (primary key)
session_id: UUID (foreign key to sessions)
error_category: ErrorCategory  # enum: 'user_fixable', 'admin_required', 'temporary'
severity: ErrorSeverity  # enum: 'blocking', 'warning', 'info'
operation_stage: str  # 'upload', 'processing', 'review', 'jira_export'
related_file_id: Optional[UUID]  # Foreign key to uploaded_files
related_ticket_id: Optional[UUID]  # Foreign key to tickets
user_message: str  # User-friendly error description
recovery_actions: dict  # JSON: Array of action steps
technical_details: dict  # JSON: Stack traces, API responses, etc.
error_code: Optional[str]  # Application-specific error codes
created_at: datetime
```

### Enum Definitions
```python
class ErrorCategory(str, Enum):
    USER_FIXABLE = "user_fixable"
    ADMIN_REQUIRED = "admin_required"
    TEMPORARY = "temporary"

class ErrorSeverity(str, Enum):
    BLOCKING = "blocking"
    WARNING = "warning"
    INFO = "info"
```

### Instance Methods
```python
def is_blocking(self) -> bool:
    # True if severity is 'blocking'

def get_recovery_action_list(self) -> List[str]:
    # Extract recovery actions from JSON field

@classmethod
def find_by_category(cls, session_id: UUID, category: ErrorCategory) -> List['SessionError']:
    # Get errors of specific category for session

@classmethod
def has_blocking_errors(cls, session_id: UUID) -> bool:
    # Check if session has any blocking errors
```

### Properties
```python
@property
def is_user_fixable(self) -> bool:
    return self.error_category == ErrorCategory.USER_FIXABLE

@property
def requires_admin(self) -> bool:
    return self.error_category == ErrorCategory.ADMIN_REQUIRED

@property
def age_minutes(self) -> float:
    # How long ago this error occurred
```

## 5. Dependencies/Imports
```python
from sqlalchemy import Column, String, Text, ForeignKey, DateTime, Enum as SQLEnum, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum
from typing import List, Dict, Optional
import uuid
```

## 6. Database Integration

### Table Definition
```python
__tablename__ = "session_errors"
__table_args__ = (
    Index('idx_session_errors_session_id', 'session_id'),
    Index('idx_session_errors_category', 'error_category'),
    Index('idx_session_errors_severity', 'severity')
)
```

### Relationships
```python
session = relationship("Session", back_populates="session_errors")
```

### Foreign Keys
```python
session_id = Column(UUID(as_uuid=True), ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False)
related_file_id = Column(UUID(as_uuid=True), ForeignKey('uploaded_files.id', ondelete='SET NULL'), nullable=True)
related_ticket_id = Column(UUID(as_uuid=True), ForeignKey('tickets.id', ondelete='SET NULL'), nullable=True)
```

### Transaction Strategy
- Participates in repository-managed transactions
- Created during error conditions across all workflow stages
- Preserved across session recovery and entity cleanup (audit trail)
- Cascading delete only with parent session (7-day cleanup)

## 7. Logging Events

### Error Lifecycle
- **INFO**: Error creation with session and operation context
- **DEBUG**: Error categorization and recovery action determination
- **AUDIT**: Error resolution attempts and user actions taken

### Specific Logging
- **INFO**: `SessionError created for session {session_id}: {error_category} - {user_message}`
- **DEBUG**: `Error linked to {operation_stage} stage, file: {related_file_id}, ticket: {related_ticket_id}`
- **AUDIT**: Error pattern analysis and recovery tracking

## 8. Error Handling

### Error Categories (Meta-level)
- **user_fixable**: Invalid error data, malformed recovery actions
- **admin_required**: Database connectivity, storage failures
- **temporary**: Database timeouts during error logging

### Specific Error Patterns
```python
# Error data validation
if not self.user_message or len(self.user_message.strip()) == 0:
    raise ErrorDataValidationError(
        message="Error must have user-friendly message",
        category="admin_required"  # Likely a bug in error handling
    )

# Recovery actions validation
if not isinstance(self.recovery_actions, dict) or 'actions' not in self.recovery_actions:
    raise ErrorDataValidationError(
        message="Invalid recovery actions format",
        category="admin_required"
    )
```

## Key Design Decisions

### Error Classification Strategy
- **Enum-based categorization**: Consistent with "who can fix it" approach throughout application
- **Multiple severity levels**: Blocking vs warning vs info for appropriate user experience
- **Stage-specific context**: Links errors to specific workflow operations for debugging

### Audit Trail Preservation
- **SET NULL for related entities**: Preserves error context even when files/tickets cleaned up
- **JSON for flexible data**: Recovery actions and technical details stored flexibly
- **Extended retention**: Errors preserved longer than sessions for troubleshooting patterns

### Relationship Strategy
- **Back-reference to Session**: Enables convenient access via session.session_errors
- **Optional entity links**: Errors can be linked to specific files or tickets when relevant
- **Cascading delete with session**: Clean 7-day cleanup while preserving audit context during workflow