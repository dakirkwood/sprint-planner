# SessionValidation Model - SQLAlchemy Implementation Specification

## UPDATED: December 25, 2025
- Renamed `ValidationStatus` enum to `AdfValidationStatus` to avoid conflict with `FileValidationStatus`
- Updated imports and references throughout

---

## 1. Class Name
**SessionValidation** - ADF validation state tracking for export readiness

## 2. Directory Path
`/backend/app/models/session.py` (keeping related models together)

## 3. Purpose & Responsibilities
- Track ADF validation status for export gate enforcement
- Store validation timestamps for invalidation logic
- Maintain validation results and failure context
- Enable export readiness queries

## 4. Methods and Properties

### Core Fields (6 total)
```python
session_id: UUID (primary key, foreign key to sessions)
validation_status: AdfValidationStatus  # enum: 'pending' | 'processing' | 'completed' | 'failed'
validation_passed: bool = False  # Export gate flag
last_validated_at: Optional[datetime]
last_invalidated_at: Optional[datetime]  # When ticket edits invalidated validation
validation_results: Optional[dict]  # JSON: passed/failed counts, error details
```

### Enum Definition
```python
# Defined in /backend/app/schemas/base_schemas.py
class AdfValidationStatus(str, Enum):
    """ADF validation task lifecycle states"""
    PENDING = "pending"        # Not yet validated
    PROCESSING = "processing"  # Validation in progress
    COMPLETED = "completed"    # Validation finished (check validation_passed for result)
    FAILED = "failed"         # Validation process failed (system error)
```

### Instance Methods
```python
def mark_validation_started(self) -> None:
    # Set status to processing, clear previous results

def mark_validation_completed(self, passed: bool, results: dict) -> None:
    # Set completion status, results, and validation_passed flag

def mark_validation_failed(self, error_context: dict) -> None:
    # Set failed status with error details

def invalidate_validation(self) -> None:
    # Mark validation as invalidated due to ticket edits
    # Sets validation_passed = False, last_invalidated_at = NOW()

@classmethod
def needs_validation(cls, session_id: UUID) -> bool:
    # True if validation required (pending, failed, or invalidated)
```

### Properties
```python
@property
def is_export_ready(self) -> bool:
    # True only if validation_status='completed' AND validation_passed=True

@property
def is_invalidated(self) -> bool:
    # True if last_invalidated_at > last_validated_at (tickets edited since validation)

@property
def validation_age_minutes(self) -> Optional[float]:
    # How long ago validation completed (for staleness checks)
```

## 5. Dependencies/Imports
```python
from sqlalchemy import Column, ForeignKey, Boolean, DateTime, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import Optional, Dict, Any

# Enum imported for type hints (actual DB storage is string)
from app.schemas.base_schemas import AdfValidationStatus
```

## 6. Database Integration

### Table Definition
```python
__tablename__ = "session_validations"
__table_args__ = (
    CheckConstraint(
        "validation_passed = false OR validation_status = 'completed'",
        name='ck_validation_passed_only_when_completed'
    ),
)
```

### Primary Key / Foreign Key
```python
session_id = Column(UUID(as_uuid=True), ForeignKey('sessions.id', ondelete='CASCADE'), primary_key=True)
```

### Relationship
```python
session = relationship("Session", back_populates="session_validation")
```

### Transaction Strategy
- Participates in repository-managed transactions
- Updated when tickets are edited (invalidation) or validation runs
- Cascading delete with parent session

## 7. Logging Events

### Validation Lifecycle
- **INFO**: Validation process start/completion with session context
- **DEBUG**: Validation timing and result details
- **AUDIT**: Validation invalidation events (when ticket edits occur)

### Specific Logging
- **INFO**: `ADF validation started for session {session_id}`
- **INFO**: `ADF validation completed for session {session_id}: {passed}/{total} tickets passed`
- **WARNING**: `ADF validation invalidated for session {session_id} due to ticket edits`
- **DEBUG**: Validation performance metrics and detailed results

## 8. Error Handling

### Error Categories
- **user_fixable**: Validation content issues (tickets need formatting fixes)
- **admin_required**: ADF service configuration, system failures
- **temporary**: Network timeouts, ADF service unavailable

### Specific Error Patterns
```python
# Validation invalidation logic
if self.last_invalidated_at and self.last_validated_at:
    if self.last_invalidated_at > self.last_validated_at:
        self.validation_passed = False

# Export readiness check
if not (self.validation_status == AdfValidationStatus.COMPLETED and self.validation_passed):
    raise ExportBlockedError(
        message="ADF validation required before export",
        category="user_fixable"
    )
```

## Key Design Decisions

### Session ID as Primary Key
- Uses session_id as primary key for true 1:1 relationship with sessions
- Simplifies queries and ensures exactly one validation record per session
- Cascading delete maintains referential integrity

### Database Constraints
- Check constraint ensures validation_passed can only be true when validation_status is 'completed'
- Prevents invalid state combinations at database level

### JSON Results Storage
- Flexible storage for validation results (passed/failed counts, error details)
- Sufficient for export gate logic without requiring structured queries
- Avoids complexity of separate validation result models

### Enum Naming Convention
- `AdfValidationStatus` clearly distinguishes from `FileValidationStatus` used in UploadedFile model
- Both enums defined centrally in `base_schemas.py` to prevent duplication
