# Discrepancy Resolution Decisions - Drupal Ticket Generator

## Resolution Date
December 25, 2025

## Overview

This document records decisions made to resolve discrepancies identified during the documentation review prior to Claude Code handoff for Phase 1 implementation.

---

## Critical Priority Decisions

### Decision 1: Async/Sync Database Approach

**Discrepancy:** Repository interfaces defined as `async` but database configuration was synchronous.

**Decision:** **Async Everywhere**

**Implementation Requirements:**
- Use SQLAlchemy 2.0 `create_async_engine()` instead of `create_engine()`
- Use `AsyncSession` instead of `Session`
- Use `asyncpg` driver instead of `psycopg2`
- Use `async with` for session context management
- All repository methods remain `async def`

**Rationale:**
- LLM API calls are inherently async
- FastAPI is async-native
- SQLAlchemy 2.0 async is mature and production-ready
- Better concurrency for I/O-heavy operations

**Documents to Update:**
- `fastapi_di_lifecycle_decisions.md` - Update database configuration examples
- `repository_patterns_decisions.md` - Update transaction pattern examples

---

### Decision 2: Background Task Infrastructure

**Discrepancy:** Worker files referenced but no task queue system specified.

**Decision:** **ARQ with Redis**

**Implementation Requirements:**
- ARQ as the async task queue library
- Redis as message broker
- Redis pub/sub for WebSocket progress communication
- Worker files: `processing_worker.py`, `export_worker.py`, `validation_worker.py`, `cleanup_worker.py`

**Architecture Pattern:**
```
FastAPI (enqueue) â†’ Redis (queue) â†’ ARQ Worker (processing)
                                          â†“
                                    Redis PubSub (progress)
                                          â†“
                                    WebSocket (FastAPI)
```

**Rationale:**
- ARQ is async-native (aligns with Decision 1)
- Lightweight, single-purpose library
- Created by Pydantic author (consistent design philosophy)
- Redis serves dual purpose: task queue + WebSocket pub/sub

**Documents to Create:**
- `background_task_infrastructure.md` - Full specification of task queue patterns

**Documents to Update:**
- `Comprehensive_Updated_Directory_Structure.md` - Add Redis/ARQ configuration files
- `processing_service_architecture.md` - Reference ARQ integration
- `export_service_architecture.md` - Reference ARQ integration

---

## High Priority Decisions

### Decision 3: Duplicate SessionStage Enum

**Discrepancy:** `SessionStage` enum defined identically in both `auth_schemas_models.py` and `base_schemas_models.py`.

**Decision:** **Keep only in `base_schemas_models.py`**

**Implementation Requirements:**
- Remove `SessionStage` definition from `auth_schemas_models.py`
- Add import: `from .base_schemas import SessionStage`

**Documents to Update:**
- `auth_schemas_models.py` - Remove duplicate, add import

---

### Decision 4: Conflicting ValidationStatus Enums

**Discrepancy:** Same enum name used for different concepts (ADF validation task state vs. file validation result).

**Decision:** **Rename both enums**

**New Enum Definitions:**
```python
class AdfValidationStatus(str, Enum):
    """ADF validation task lifecycle states"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class FileValidationStatus(str, Enum):
    """CSV file validation result states"""
    PENDING = "pending"
    VALID = "valid"
    INVALID = "invalid"
```

**Documents to Update:**
- `base_schemas_models.py` - Add both new enum definitions
- `session_validation_model_spec.md` - Reference `AdfValidationStatus`
- `uploaded_file_model_spec.md` - Reference `FileValidationStatus`

---

### Decision 5: Missing Enum Definitions

**Discrepancy:** Several enums referenced in model specs not defined in `base_schemas_models.py`.

**Decision:** **Add all missing enums to `base_schemas_models.py`**

**Enums to Add:**
```python
class TaskType(str, Enum):
    """Background task types"""
    PROCESSING = "processing"
    EXPORT = "export"
    ADF_VALIDATION = "adf_validation"

class TaskStatus(str, Enum):
    """Background task lifecycle states"""
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class JiraUploadStatus(str, Enum):
    """Attachment upload status to Jira"""
    PENDING = "pending"
    UPLOADED = "uploaded"
    FAILED = "failed"

class EventCategory(str, Enum):
    """Audit log event categories"""
    SESSION = "session"
    UPLOAD = "upload"
    PROCESSING = "processing"
    REVIEW = "review"
    JIRA_EXPORT = "jira_export"
    SYSTEM = "system"

class AuditLevel(str, Enum):
    """Audit log detail levels"""
    BASIC = "basic"
    COMPREHENSIVE = "comprehensive"
```

**Documents to Update:**
- `base_schemas_models.py` - Add all five enums

---

### Decision 6: Circular Foreign Key on Ticket/Attachment

**Discrepancy:** Both Ticket and Attachment models defined FKs pointing to each other.

**Decision:** **Remove `attachment_id` from Ticket model**

**Implementation Requirements:**
- Remove `attachment_id` field from Ticket model
- Keep `ticket_id` FK on Attachment model (child references parent)
- Navigate via SQLAlchemy relationship: `ticket.attachment`

**Correct Relationship Pattern:**
```python
# Ticket model
attachment = relationship("Attachment", back_populates="ticket", uselist=False)

# Attachment model
ticket_id = Column(UUID, ForeignKey('tickets.id', ondelete='CASCADE'), nullable=False)
ticket = relationship("Ticket", back_populates="attachment")
```

**Documents to Update:**
- `ticket_model_spec.md` - Remove `attachment_id` from field list
- `SQLAlchemy_Relationship_Bidirectional_Consistency_Audit.md` - Verify relationship definitions

---

## Medium Priority Decisions

### Decision 7: Directory Structure Document Duplication

**Discrepancy:** Two directory structure documents with conflicting information.

**Decision:** **Remove `updated_directory_structure.md`**

**Implementation Requirements:**
- Remove `updated_directory_structure.md` from project files
- `Comprehensive_Updated_Directory_Structure.md` is the authoritative source

**Rationale:**
- Comprehensive version was created as part of conflict resolution
- Aligns with all other specification documents
- Includes resolved architectural decisions

---

## Open Question Resolution

### Decision 8: ADF Validation Race Condition

**Risk:** User could edit tickets between validation pass and export start.

**Decision:** **Re-validate on export start**

**Implementation Requirements:**
- Export endpoint checks `session_validation.last_invalidated_at > session_validation.last_validated_at`
- If stale, return error with "Validation required" message
- No editing restrictions imposed on users

**Rationale:**
- Better UX than locking editing
- Simple timestamp comparison (no full re-validation needed)
- `SessionValidation` model already has `last_invalidated_at` field for this purpose
- Clear error messaging guides user to re-validate

**Documents to Update:**
- `export_service_architecture.md` - Document validation check in export flow
- `fastapi_jira_integration_endpoints.md` - Add validation check to export endpoint spec

---

## Complete List of Documents Requiring Updates

| Document | Updates Required |
|----------|------------------|
| `fastapi_di_lifecycle_decisions.md` | Async database configuration |
| `repository_patterns_decisions.md` | Async transaction patterns |
| `Comprehensive_Updated_Directory_Structure.md` | Add Redis/ARQ config files |
| `processing_service_architecture.md` | ARQ integration reference |
| `export_service_architecture.md` | ARQ integration, validation check |
| `auth_schemas_models.py` | Remove duplicate SessionStage, add import |
| `base_schemas_models.py` | Add 7 enums (2 renamed + 5 new) |
| `session_validation_model_spec.md` | Reference AdfValidationStatus |
| `uploaded_file_model_spec.md` | Reference FileValidationStatus |
| `ticket_model_spec.md` | Remove attachment_id field |
| `SQLAlchemy_Relationship_Bidirectional_Consistency_Audit.md` | Verify Ticket/Attachment relationship |
| `fastapi_jira_integration_endpoints.md` | Add validation check to export |

## Documents to Create

| Document | Purpose |
|----------|---------|
| `background_task_infrastructure.md` | ARQ + Redis configuration, worker patterns, pub/sub for WebSocket progress |

## Documents to Remove

| Document | Reason |
|----------|--------|
| `updated_directory_structure.md` | Superseded by comprehensive version |

---

## Summary

All 7 discrepancies and 1 open question have been resolved. The documentation is now internally consistent and ready for handoff to Claude Code for Phase 1 implementation.

**Key Architectural Decisions:**
1. Async everywhere (SQLAlchemy 2.0 + asyncpg)
2. ARQ + Redis for background tasks and WebSocket progress
3. Centralized enums in `base_schemas_models.py`
4. Standard 1:1 FK pattern for Ticket/Attachment
5. Re-validate on export start (no edit locking)
