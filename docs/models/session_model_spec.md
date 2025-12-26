# Session Model - SQLAlchemy Implementation Specification

## 1. Class Name
**Session** - Core workflow state tracking model

## 2. Directory Path
`/backend/app/models/session.py`

## 3. Purpose & Responsibilities
- Track user workflow progression through defined stages
- Store session context (site details, LLM provider choice, Jira project)
- Enable session recovery via jira_user_id lookup
- Maintain workflow metadata and completion tracking

## 4. Methods and Properties

### Core Fields (13 total)
```python
id: UUID (primary key)
jira_user_id: str
jira_display_name: str
site_name: Optional[str]  # NULL until user provides
site_description: Optional[str]
jira_project_key: Optional[str]  # NULL until review phase
llm_provider_choice: Optional[str]  # 'openai'|'anthropic', NULL until chosen
current_stage: SessionStage  # enum
status: SessionStatus  # enum
total_tickets_generated: int = 0
created_at: datetime
updated_at: datetime
completed_at: Optional[datetime]
```

### Enum Definitions
```python
class SessionStage(str, Enum):
    SITE_INFO_COLLECTION = "site_info_collection"
    UPLOAD = "upload" 
    PROCESSING = "processing"
    REVIEW = "review"
    JIRA_EXPORT = "jira_export"
    COMPLETED = "completed"

class SessionStatus(str, Enum):
    ACTIVE = "active"
    EXPORTING = "exporting" 
    FAILED = "failed"
    COMPLETED = "completed"
```

### Instance Methods
```python
def can_transition_to(self, new_stage: SessionStage) -> bool:
    # Hard-coded sequential stage progression validation
    # site_info → upload → processing → review → jira_export → completed

def to_dict(self) -> dict:
    # Serialization for direct columns only (no relationships)

@classmethod
def find_incomplete_for_user(cls, jira_user_id: str) -> List['Session']:
    # Recovery query for incomplete sessions (status != 'completed')
```

### Properties
```python
@property
def is_recoverable(self) -> bool:
    # True if session can be recovered (not completed, within 7-day window)

@property
def stage_display_name(self) -> str:
    # Human-readable stage names for UI display
```

## 5. Dependencies/Imports
```python
from sqlalchemy import Column, String, Integer, DateTime, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum
from typing import List, Optional
import uuid
```

## 6. Database Integration

### Table Definition
```python
__tablename__ = "sessions"
__table_args__ = (
    Index('idx_sessions_jira_user_id', 'jira_user_id'),
    Index('idx_sessions_status', 'status'),
    Index('idx_sessions_created_at', 'created_at')
)
```

### Relationships
```python
# Small collections - eager loading for recovery scenarios
uploaded_files = relationship("UploadedFile", back_populates="session", 
                            lazy="joined", cascade="all, delete-orphan")
session_task = relationship("SessionTask", back_populates="session", 
                          lazy="joined", uselist=False)
session_validation = relationship("SessionValidation", back_populates="session", 
                                lazy="joined", uselist=False)

# Large collections - lazy loading
tickets = relationship("Ticket", back_populates="session", lazy="select")
session_errors = relationship("SessionError", back_populates="session", lazy="select")
```

### Transaction Strategy
- Participates in repository-managed transactions
- Never creates own database connections
- Uses cascading deletes for dependent records

## 7. Logging Events

### Session Lifecycle
- **INFO**: Session creation with jira_user_id and stage transitions
- **DEBUG**: Stage validation checks and transition attempts
- **AUDIT**: Session recovery events with previous session context

### Stage Transitions
- **INFO**: `Session {session_id} transitioned from {old_stage} to {new_stage} for user {jira_user_id}`
- **WARNING**: Invalid transition attempts with current state context

### Recovery Operations
- **INFO**: `Session recovery initiated for user {jira_user_id}, found {count} incomplete sessions`
- **AUDIT**: `Session {session_id} recovered from stage {current_stage}, created {days_ago} days ago`

## 8. Error Handling

### Error Categories
- **user_fixable**: Invalid stage transitions, business rule violations
- **admin_required**: Database connectivity issues, constraint violations
- **temporary**: Database lock timeouts, connection pool exhaustion

### Specific Error Patterns
```python
# Invalid stage transition
if not self.can_transition_to(new_stage):
    raise SessionValidationError(
        message=f"Cannot transition from {self.current_stage} to {new_stage}",
        category="user_fixable"
    )

# Constraint violations
try:
    session.commit()
except IntegrityError as e:
    if "unique_constraint" in str(e):
        raise SessionValidationError(
            message="Session already exists for this context",
            category="user_fixable"
        )
```

## Key Design Decisions

### Functional Separation Approach
- Session model focuses on core workflow state only
- Task execution tracking moved to separate SessionTask model
- ADF validation state moved to separate SessionValidation model
- Reduces Session model from 23 potential fields to 13 manageable fields

### Stage Transition Strategy
- Hard-coded sequential progression validation
- Chosen over transition matrix for simplicity and clarity
- Sufficient for linear workflow that's unlikely to change dramatically

### Relationship Loading Strategy
- Eager loading (`lazy="joined"`) for small, frequently needed objects
- Lazy loading (`lazy="select"`) for potentially large collections
- Optimized for session recovery scenarios