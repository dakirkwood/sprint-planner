# SessionTask Model - SQLAlchemy Implementation Specification

## 1. Class Name
**SessionTask** - Background task execution tracking for sessions

## 2. Directory Path
`/backend/app/models/session.py` (same file as Session for simplicity)

## 3. Purpose & Responsibilities
- Track background task execution (processing, export, validation)
- Store task metadata for recovery and retry logic
- Maintain task state and failure context
- Enable task status queries and progress tracking

## 4. Methods and Properties

### Core Fields (9 total)
```python
id: UUID (primary key)
session_id: UUID (foreign key to sessions)
task_type: TaskType  # enum: 'processing' | 'export' | 'adf_validation'
task_id: UUID  # Background task identifier
status: TaskStatus  # enum: 'running' | 'completed' | 'failed' | 'cancelled'
started_at: datetime
completed_at: Optional[datetime]
failed_at: Optional[datetime]
retry_count: int = 0
failure_context: Optional[dict]  # JSON field for task-specific error details
```

### Enum Definitions
```python
class TaskType(str, Enum):
    PROCESSING = "processing"
    EXPORT = "export"
    ADF_VALIDATION = "adf_validation"

class TaskStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
```

### Instance Methods
```python
def can_retry(self) -> bool:
    # Check if task can be retried based on status and retry_count
    # Max 3 retries, only for 'failed' status

def mark_started(self, task_id: UUID) -> None:
    # Set task as running with new task_id

def mark_completed(self) -> None:
    # Set task as completed with timestamp

def mark_failed(self, error_context: dict) -> None:
    # Set task as failed with error details and increment retry_count

@classmethod
def find_active_for_session(cls, session_id: UUID) -> Optional['SessionTask']:
    # Find any running task for the session

@classmethod
def find_failed_retryable(cls, session_id: UUID) -> Optional['SessionTask']:
    # Find failed task that can be retried
```

### Properties
```python
@property
def is_running(self) -> bool:
    return self.status == TaskStatus.RUNNING

@property
def duration_minutes(self) -> Optional[float]:
    # Calculate task duration if completed or failed

@property
def can_be_retried(self) -> bool:
    return self.status == TaskStatus.FAILED and self.retry_count < 3
```

## 5. Dependencies/Imports
```python
from sqlalchemy import Column, ForeignKey, DateTime, Integer, Enum as SQLEnum, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
import uuid
```

## 6. Database Integration

### Table Definition
```python
__tablename__ = "session_tasks"
__table_args__ = (
    UniqueConstraint('session_id', name='uq_session_tasks_session_id'),
)
```

### Foreign Key
```python
session_id = Column(UUID(as_uuid=True), ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False)
```

### Transaction Strategy
- Participates in repository-managed transactions
- Always updated within same transaction as Session stage changes
- Cascading delete ensures cleanup with parent session

### Update Pattern
- Single record per session (unique constraint on session_id)
- Record updated as workflow progresses through different task types
- Processing → Export → ADF Validation (overwriting same record)

## 7. Logging Events

### Task Lifecycle
- **INFO**: Task creation and status changes with session context
- **DEBUG**: Task execution details (duration, retry attempts)
- **AUDIT**: Task failures with error context for debugging

### Specific Logging
- **INFO**: `SessionTask {task_type} started for session {session_id}, task_id: {task_id}`
- **INFO**: `SessionTask {task_type} completed for session {session_id}, duration: {duration_minutes}m`
- **WARNING**: `SessionTask {task_type} failed for session {session_id}, retry #{retry_count}`
- **DEBUG**: Task timing and performance metrics

## 8. Error Handling

### Error Categories
- **user_fixable**: Task configuration issues, invalid task state transitions
- **admin_required**: Database connectivity, task system failures
- **temporary**: Background task service issues, worker unavailability

### Specific Error Patterns
```python
# Invalid task state transitions
if self.status == TaskStatus.COMPLETED:
    raise TaskValidationError(
        message="Cannot modify completed task",
        category="user_fixable"
    )

# Retry limit exceeded
if self.retry_count >= 3:
    raise TaskValidationError(
        message="Maximum retry attempts exceeded",
        category="admin_required"
    )
```

## Key Design Decisions

### Single Record Per Session
- Unique constraint on session_id ensures one task record per session
- Record gets updated as workflow progresses through different task types
- Chosen over audit trail approach due to sequential workflow nature

### JSON Failure Context
- Flexible storage for task-specific error details
- Sufficient for debugging without requiring structured queries
- Avoids complexity of separate error detail models

### Cascading Delete
- Task records automatically cleaned up with session (7-day cleanup)
- Simplifies maintenance and ensures no orphaned records