# Documentation Review Session Decisions - December 26, 2025

## Overview

This document summarizes decisions made during the documentation review session focused on identifying and resolving discrepancies before Claude Code implementation handoff.

---

## Decision 1: Document Version Replacement Strategy

**Issue:** Multiple documents exist in both original and `_updated` versions, creating potential confusion.

**Decision:** Original documents should be replaced entirely by their `_updated` counterparts.

**Documents to Replace:**

| Remove (Original) | Replace With (Updated) |
|-------------------|------------------------|
| `ticket_model_spec.md` | `ticket_model_spec_updated.md` |
| `uploaded_file_model_spec.md` | `uploaded_file_model_spec_updated.md` |
| `session_validation_model_spec.md` | `session_validation_model_spec_updated.md` |
| `auth_schemas_models.py` | `auth_schemas_models_updated.py` |
| `base_schemas_models.py` | `base_schemas_models_updated.py` |
| `fastapi_di_lifecycle_decisions.md` | `fastapi_di_lifecycle_decisions_updated.md` |
| `repository_patterns_decisions.md` | `repository_patterns_decisions_updated.md` |
| `processing_service_architecture.md` | `processing_service_architecture_updated.md` |
| `export_service_architecture.md` | `export_service_architecture_updated.md` |
| `Comprehensive_Updated_Directory_Structure.md` | `Comprehensive_Updated_Directory_Structure_updated.md` |
| `SQLAlchemy_Relationship_Bidirectional_Consistency_Audit.md` | `SQLAlchemy_Relationship_Bidirectional_Consistency_Audit_updated.md` |

**Additional Removal:**
- `updated_directory_structure.md` â€” Superseded by comprehensive version

---

## Decision 2: Corrected Document Reference List for `claude_code_instructions.md`

**Issue:** The `claude_code_instructions.md` file references stale document names and omits critical specification documents.

**Decision:** Update the document reference list as follows:

### Priority 1: Core Architecture Decisions
| Document | Purpose |
|----------|---------|
| `Comprehensive_Updated_Directory_Structure_updated.md` | Authoritative file/folder structure |
| `fastapi_di_lifecycle_decisions_updated.md` | Async database config, DI patterns, request lifecycle |
| `repository_patterns_decisions_updated.md` | Async transaction patterns, repository design |
| `background_task_infrastructure.md` | ARQ + Redis configuration, worker patterns |
| `Task_Management_Architecture_Standardization.md` | SessionTask model usage, job coordination |

### Priority 2: Database Models
| Document | Purpose |
|----------|---------|
| `session_model_spec.md` | Session, SessionTask, SessionValidation models |
| `ticket_model_spec_updated.md` | Ticket model (no attachment_id FK) |
| `uploaded_file_model_spec_updated.md` | UploadedFile with FileValidationStatus |
| `session_validation_model_spec_updated.md` | SessionValidation with AdfValidationStatus |
| `attachment_model_spec.md` | Attachment model (owns ticket_id FK) |
| `ticket_dependency_model_spec.md` | TicketDependency junction table |
| `jira_auth_token_model_spec.md` | OAuth token storage |
| `jira_project_context_model_spec.md` | Cached Jira project metadata |
| `session_error_model_spec.md` | Error tracking |
| `audit_log_model_spec.md` | Audit trail |
| `SQLAlchemy_Relationship_Bidirectional_Consistency_Audit_updated.md` | Relationship definitions reference |

### Priority 3: Pydantic Schemas
| Document | Purpose |
|----------|---------|
| `base_schemas_models_updated.py` | ALL enums, base classes, common patterns |
| `auth_schemas_models_updated.py` | Auth/session schemas (imports SessionStage from base) |
| `upload_schemas_models.py` | Upload stage request/response models |
| `Missing_Response_Models_-_Complete_Specifications.md` | Processing, export, review, error response models |

### Priority 4: Repository Interfaces
| Document | Purpose |
|----------|---------|
| `Complete_Repository_Interface_Specifications.md` | All repository interface definitions |

### Priority 5: Service Architecture
| Document | Purpose |
|----------|---------|
| `session_service_architecture.md` | SessionService methods |
| `upload_service_architecture.md` | UploadService methods |
| `processing_service_architecture_updated.md` | ProcessingService with ARQ integration |
| `review_service_architecture_updated.md` | ReviewService with ARQ integration |
| `export_service_architecture_updated.md` | ExportService with ARQ integration |
| `LLM_Service_Scope_and_Interface_Specification.md` | LLM interface, phased implementation |

### Priority 6: API Endpoints
| Document | Purpose |
|----------|---------|
| `updated_auth_flow_spec.md` | OAuth flow, session management endpoints |
| `fastapi_upload_endpoints.md` | File upload, validation endpoints |
| `fastapi_processing_endpoints.md` | Ticket generation endpoints |
| `fastapi_jira_integration_endpoints.md` | Export endpoints |

### Priority 7: Validation & Error Handling
| Document | Purpose |
|----------|---------|
| `CSV_Type_Registry_Structure_Specification.md` | CSV type definitions, validation rules |
| `updated_error_response_standards.md` | "Who can fix it" error patterns |

### Priority 8: Conflict Resolution Reference
| Document | Purpose |
|----------|---------|
| `documentation_review_decisions.md` | Summary of review findings |
| `discrepancy_resolution_decisions.md` | All 8 resolved discrepancies |

### Documents to REMOVE from References
| Document | Reason |
|----------|--------|
| `updated_directory_structure.md` | Superseded by comprehensive version |
| `Authentication & Session Pydantic Models.txt` | Use `.py` version |
| `Upload Stage Pydantic Models.txt` | Use `.py` version |
| `Base Pydantic Models.txt` | Use `.py` version |
| Any non-`_updated` version where `_updated` exists | Superseded |

---

## Decision 3: ReviewService ARQ Integration

**Issue:** `review_service_architecture.md` was not updated with ARQ integration patterns, despite ReviewService needing background task support for ADF validation.

**Decision:** Create `review_service_architecture_updated.md` with:

### Constructor Update
```python
def __init__(self, 
             ticket_repo: TicketRepositoryInterface,
             session_repo: SessionRepositoryInterface,
             error_repo: ErrorRepositoryInterface,
             jira_service: JiraService,
             arq_pool: ArqRedis = None):  # Added
```

### Method Classification
| Method | Background Task Required |
|--------|--------------------------|
| `get_tickets_summary()` | No |
| `get_ticket_detail()` | No |
| `update_ticket()` | No |
| `bulk_assign_tickets()` | No |
| `get_dependency_graph()` | No |
| `update_ticket_ordering()` | No |
| `update_cross_group_dependencies()` | No |
| `validate_adf()` | **Yes** â€” split into public/internal |
| `get_adf_validation_status()` | No |
| `check_export_readiness()` | No |
| `get_rollback_impact()` | No |
| `rollback_to_stage()` | No |

### New Response Models Added
- `AdfValidationStartResponse`
- `AdfValidationAlreadyRunningResponse`
- `AdfValidationStatusResponse`
- `AdfValidationError`
- `AdfValidationCompletedResponse`
- `AdfValidationFailedResponse`

### Worker Integration
- Job function: `validate_adf_job` in `/backend/app/workers/validation_worker.py`
- Registered in `WorkerSettings.functions`

---

## Documents Created This Session

| Document | Purpose |
|----------|---------|
| `review_service_architecture_updated.md` | ReviewService with ARQ integration for ADF validation |

---

## Outstanding Items

### Lightweight PRD
The `documentation_review_decisions.md` notes that business-layer context is missing:
- Problem statement
- User personas
- User stories
- Success metrics
- Explicit scope rationale
- Non-functional requirements

**Status:** To be addressed in a separate conversation.

---

## Summary

All critical discrepancies have been resolved. The documentation is now internally consistent and ready for Claude Code handoff for Phase 1 implementation.

**Total Discrepancies Resolved:**
- 8 from prior documentation review
- 3 from this session
- **11 total**
