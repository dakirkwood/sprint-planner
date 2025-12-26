# Missing Response Models - Complete Specifications

## Overview
Comprehensive definition of all missing response models referenced in endpoint specifications but not defined in existing schema files.

## Organization by Schema Files

### **Processing Stage Response Models**
**File**: `/backend/app/schemas/processing.py`

```python
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime
from uuid import UUID
from .base import BaseResponse, ErrorCategory

# Processing Initiation Responses
class ProcessingStartResponse(BaseResponse):
    task_id: UUID
    session_id: UUID
    status: str = "processing"
    estimated_duration_minutes: int
    total_files: int
    estimated_tickets: int
    llm_provider: str

class ProcessingAlreadyRunningResponse(BaseResponse):
    task_id: UUID
    session_id: UUID
    status: str = "processing"
    progress_percentage: float
    current_stage: str
    started_at: datetime

# Processing Status Responses
class ProcessingStatusResponse(BaseResponse):
    session_id: UUID
    task_id: UUID
    status: str = "processing"
    progress_percentage: float
    current_stage: str
    entity_group: Optional[str]
    entities_completed: int
    total_entities: int
    estimated_time_remaining_minutes: Optional[int]
    started_at: datetime
    llm_provider: str

class EntityGroupSummary(BaseModel):
    group_name: str
    tickets_created: int
    entities_processed: int

class ProcessingCompletedResponse(BaseResponse):
    session_id: UUID
    task_id: UUID
    status: str = "completed"
    tickets_generated: int
    entity_groups_processed: List[EntityGroupSummary]
    total_cost: float
    processing_time_minutes: float
    llm_provider: str
    model_used: str
    completed_at: datetime
    ready_for_review: bool = True
    technical_details: Optional[dict] = None

class ProcessingFailedResponse(BaseResponse):
    session_id: UUID
    task_id: UUID
    status: str = "failed"
    error_category: str
    user_message: str
    recovery_actions: List[str]
    failed_at: datetime
    progress_before_failure: float
    retry_available: bool
    technical_details: Optional[dict] = None

# Processing Recovery Responses
class ProcessingRetryResponse(BaseResponse):
    task_id: UUID
    session_id: UUID
    status: str = "processing"
    retry_attempt: int
    remaining_retries: int
    cleaned_up_tickets: int
    previous_error_preserved: bool = True
    llm_provider: str

class ProcessingCancellationResponse(BaseResponse):
    session_id: UUID
    task_id: UUID
    status: str = "cancelled"
    cancelled_at: datetime
    graceful_shutdown: bool = True
    partial_tickets_deleted: int
    entity_groups_completed: int
    entity_groups_cancelled: int
    cost_for_completed_work: float
    llm_tokens_used: int
    processing_time_minutes: float
    session_returned_to_stage: str = "upload"
    can_modify_files: bool = True

# LLM Service Health Response
class LLMServiceHealthResponse(BaseResponse):
    session_id: UUID
    provider: str
    model: str
    overall_status: str  # "healthy", "degraded", "unavailable"
    connectivity: str    # "ok", "timeout", "unreachable"
    authentication: str  # "valid", "invalid", "expired"
    quota_status: str    # "available", "low", "exceeded"
    model_availability: str  # "available", "unavailable", "deprecated"
    estimated_cost: float
    estimated_tokens: int
    quota_remaining: Optional[float]
    cost_breakdown: Dict[str, float]
    cached_at: datetime
    cache_expires_at: datetime
    checked_at: datetime

# Processing Error Responses
class ErrorGroup(BaseModel):
    group_id: UUID
    error_type: str
    error_category: str
    error_count: int
    first_occurred_at: datetime
    last_occurred_at: datetime
    summary_message: str
    affected_entities: List[str]
    retry_attempts: List[int]
    sample_error: Dict[str, any]
    all_errors: Optional[List[Dict[str, any]]]

class ProcessingErrorsResponse(BaseResponse):
    session_id: UUID
    total_errors: int
    filtered_errors: int
    retry_attempts: List[int]
    error_groups: List[ErrorGroup]
    pagination: Dict[str, any]
```

### **Export/Jira Stage Response Models**
**File**: `/backend/app/schemas/export.py`

```python
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from uuid import UUID
from .base import BaseResponse

# Export Initiation Responses
class ExportStartResponse(BaseResponse):
    task_id: UUID
    session_id: UUID
    status: str = "exporting"
    total_tickets: int
    estimated_duration_minutes: int
    jira_project_key: str
    started_at: datetime

class ExportAlreadyRunningResponse(BaseResponse):
    task_id: UUID
    session_id: UUID
    status: str = "exporting"
    progress_percentage: float
    current_ticket_title: str
    started_at: datetime

# Export Status Responses
class ExportStatusResponse(BaseResponse):
    session_id: UUID
    task_id: UUID
    status: str = "exporting"
    progress_percentage: float
    tickets_completed: int
    total_tickets: int
    current_ticket_title: Optional[str]
    estimated_time_remaining_minutes: Optional[int]

class ExportCompletedResponse(BaseResponse):
    session_id: UUID
    task_id: UUID
    status: str = "completed"
    jira_tickets_created: int
    dependencies_created: int
    manual_fixes_needed: int
    total_processing_time_minutes: float
    completed_at: datetime

class ExportFailedResponse(BaseResponse):
    session_id: UUID
    task_id: UUID
    status: str = "failed"
    failed_at_ticket_order: int
    error_category: str
    user_message: str
    recovery_actions: List[str]
    retry_available: bool
    retry_attempts_used: int

# Export Recovery Response
class ExportRetryResponse(BaseResponse):
    task_id: UUID
    session_id: UUID
    status: str = "exporting"
    retry_attempt: int
    remaining_retries: int
    resuming_from_ticket_order: int
    preserved_successful_tickets: int

# ADF Testing Responses
class AdfTestResult(BaseModel):
    ticket_id: UUID
    ticket_title: str
    status: str  # "passed", "failed"
    adf_size_bytes: Optional[int]
    character_reduction: Optional[float]
    error_message: Optional[str]
    suggested_fix: Optional[str]
    attachment_upload_tested: bool
    attachment_upload_status: Optional[str]  # "passed", "failed", "skipped"

class AdfTestResponse(BaseResponse):
    session_id: UUID
    tickets_tested: int
    all_passed: bool
    passed: int
    failed: int
    results: List[AdfTestResult]

# Export Results Responses
class JiraTicketReference(BaseModel):
    ticket_id: UUID
    jira_key: str
    jira_url: str
    title: str

class ManualFixGuidance(BaseModel):
    jira_key: str
    title: str
    issue_type: str  # "assignee_invalid", "sprint_not_found"
    recommended_action: str
    jira_url: str

class ExportResultsResponse(BaseResponse):
    session_id: UUID
    total_tickets_created: int
    jira_tickets: List[JiraTicketReference]
    dependencies_created: int
    manual_fixes: List[ManualFixGuidance]
    total_processing_time_minutes: float

# Project Validation Response
class SprintOption(BaseModel):
    id: str
    name: str
    state: str  # "active", "closed", "future"

class TeamMemberOption(BaseModel):
    account_id: str
    display_name: str
    email: Optional[str] = None
    active: bool = True

class PriorityOption(BaseModel):
    id: str
    name: str
    description: Optional[str] = None

class ValidationWarning(BaseModel):
    warning_type: str
    message: str
    affected_items: List[str]

class ProjectValidationResponse(BaseResponse):
    project_key: str
    project_name: str
    validation_status: str  # "valid", "invalid"
    can_create_tasks: bool
    can_view_project: bool
    available_sprints: List[SprintOption]
    team_members: List[TeamMemberOption]
    priority_levels: List[PriorityOption]
    validation_warnings: List[ValidationWarning]
    blocking_issues: List[str]
```

### **Review Stage Response Models**
**File**: `/backend/app/schemas/review.py`

```python
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime
from uuid import UUID
from .base import BaseResponse

# Ticket Management Responses
class TicketSummary(BaseModel):
    ticket_id: UUID
    title: str
    entity_group: str
    ready_for_jira: bool
    user_order: int
    character_count: int
    has_attachment: bool
    sprint: Optional[str]
    assignee: Optional[str]

class TicketListResponse(BaseResponse):
    session_id: UUID
    total_tickets: int
    entity_groups: Dict[str, List[TicketSummary]]
    ready_for_export_count: int
    tickets_with_attachments: int

class TicketDetailResponse(BaseResponse):
    ticket_id: UUID
    session_id: UUID
    title: str
    description: str
    csv_source_files: List[Dict[str, any]]
    entity_group: str
    user_order: int
    ready_for_jira: bool
    sprint: Optional[str]
    assignee: Optional[str]
    user_notes: Optional[str]
    attachment_id: Optional[UUID]
    character_count: int
    needs_attachment: bool
    dependencies: List[UUID]
    dependents: List[UUID]
    created_at: datetime
    updated_at: datetime

class TicketUpdateResponse(BaseResponse):
    ticket_id: UUID
    updated_fields: List[str]
    attachment_generated: bool
    attachment_id: Optional[UUID]
    validation_invalidated: bool
    character_count: int
    updated_at: datetime

# Bulk Operations Responses
class BulkAssignResponse(BaseResponse):
    session_id: UUID
    tickets_updated: int
    assignments_applied: Dict[str, any]
    validation_invalidated: bool

# Dependency Management Responses
class DependencyNode(BaseModel):
    ticket_id: UUID
    title: str
    entity_group: str
    dependencies: List[UUID]
    dependents: List[UUID]
    user_order: int

class DependencyGraphResponse(BaseResponse):
    session_id: UUID
    nodes: List[DependencyNode]
    edges: List[Dict[str, UUID]]
    circular_dependencies: List[List[UUID]]
    entity_group_ordering: List[str]

class TicketOrderingResponse(BaseResponse):
    session_id: UUID
    tickets_reordered: int
    entity_group: str
    new_ordering: List[UUID]
    validation_invalidated: bool

class CrossGroupDependencyResponse(BaseResponse):
    session_id: UUID
    dependencies_created: int
    dependencies_removed: int
    circular_dependencies_detected: List[List[UUID]]
    validation_invalidated: bool

# ADF Validation Responses
class AdfValidationStartResponse(BaseResponse):
    task_id: UUID
    session_id: UUID
    status: str = "validating"
    tickets_to_validate: int
    estimated_duration_minutes: int

class AdfValidationCompletedResponse(BaseResponse):
    session_id: UUID
    task_id: UUID
    status: str = "completed"
    validation_passed: bool
    tickets_validated: int
    tickets_passed: int
    tickets_failed: int
    export_ready: bool
    validation_results: Dict[str, any]
    completed_at: datetime

# Export Readiness Response
class ExportReadinessResponse(BaseResponse):
    session_id: UUID
    export_ready: bool
    adf_validation_passed: bool
    tickets_ready: int
    total_tickets: int
    blocking_issues: List[str]
    warnings: List[str]
    ready_message: Optional[str]

# Rollback Responses
class RollbackImpact(BaseModel):
    tickets_to_delete: int
    attachments_to_delete: int
    dependencies_to_delete: int
    validation_to_reset: bool

class RollbackImpactResponse(BaseResponse):
    session_id: UUID
    current_stage: str
    target_stage: str
    impact: RollbackImpact
    data_loss_warning: str
    confirmation_required: bool

class RollbackResponse(BaseResponse):
    session_id: UUID
    previous_stage: str
    new_stage: str
    tickets_deleted: int
    attachments_deleted: int
    files_preserved: bool
    can_modify_files: bool
    rollback_completed_at: datetime
```

### **Error and Audit Response Models**
**File**: `/backend/app/schemas/error.py`

```python
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from uuid import UUID
from .base import BaseResponse, ErrorCategory, ErrorSeverity

# Error Detail Responses
class ErrorDetailResponse(BaseResponse):
    error_id: UUID
    session_id: UUID
    error_category: ErrorCategory
    severity: ErrorSeverity
    operation_stage: str
    user_message: str
    recovery_actions: List[str]
    technical_details: Optional[Dict[str, any]]
    related_file_id: Optional[UUID]
    related_ticket_id: Optional[UUID]
    error_code: Optional[str]
    created_at: datetime

class ErrorExplanationResponse(BaseResponse):
    error_id: UUID
    llm_explanation: str
    suggested_actions: List[str]
    processing_time_ms: int

# Session Timeline Response
class AuditEvent(BaseModel):
    event_id: UUID
    event_type: str
    event_category: str
    description: str
    entity_type: Optional[str]
    entity_id: Optional[str]
    execution_time_ms: Optional[int]
    created_at: datetime

class SessionTimelineResponse(BaseResponse):
    session_id: UUID
    jira_user_id: str
    events: List[AuditEvent]
    total_events: int
    timeline_start: datetime
    timeline_end: Optional[datetime]
```

### **Upload Stage Additional Response Models**
**File**: `/backend/app/schemas/upload.py` (additions to existing file)

```python
# Add these to the existing upload.py file

class CustomDependencyResponse(BaseResponse):
    success: bool
    relationships_configured: int
    ready_for_validation: bool

class RelationshipError(BaseModel):
    relationship_type: str
    description: str
    affected_files: List[str]
    specific_errors: List['RelationshipErrorDetail']

class RelationshipErrorDetail(BaseModel):
    source_file: str
    row_number: int
    column_name: str
    invalid_reference: str
    available_options: List[str]

# Update ValidationResponse to include relationship errors
class ValidationResponse(BaseResponse):
    success: bool
    ready_for_processing: bool
    summary: 'ValidationSummary'
    errors: List['ValidationError']  # Schema/content errors
    relationship_errors: List[RelationshipError]  # Cross-file errors
```

## Import Updates Required

### **Base Schema Imports**
Each schema file needs to import from base:

```python
# /backend/app/schemas/processing.py
from .base import BaseResponse, ErrorCategory, ErrorSeverity

# /backend/app/schemas/export.py  
from .base import BaseResponse, ValidationStatus

# /backend/app/schemas/review.py
from .base import BaseResponse, SessionStage

# /backend/app/schemas/error.py
from .base import BaseResponse, ErrorCategory, ErrorSeverity, EventCategory, AuditLevel
```

### **Cross-Schema References**
Some response models reference models from other schema files:

```python
# In review.py - reference upload models
from .upload import UploadedFileInfo

# In processing.py - reference error models  
from .error import ErrorDetailResponse

# In export.py - reference auth models
from .auth import ProjectContextData
```

## Endpoint Integration

### **Update Endpoint Return Types**
All endpoint specifications can now reference these models:

```python
# Processing endpoints
@router.post("/api/processing/generate-tickets/{session_id}", response_model=ProcessingStartResponse)
@router.get("/api/processing/status/{session_id}", response_model=ProcessingStatusResponse)

# Export endpoints  
@router.post("/api/jira/export-session/{session_id}", response_model=ExportStartResponse)
@router.get("/api/jira/export-results/{session_id}", response_model=ExportResultsResponse)

# Review endpoints
@router.get("/api/review/tickets/{session_id}", response_model=TicketListResponse)
@router.put("/api/review/ticket/{ticket_id}", response_model=TicketUpdateResponse)
```

## Success Criteria

- ✅ All response models referenced in endpoint specifications are defined
- ✅ Models are organized by workflow stage in appropriate schema files
- ✅ All models inherit from BaseResponse for consistency
- ✅ Cross-file imports are properly documented
- ✅ Models include all fields referenced in endpoint specifications
- ✅ Type hints are comprehensive and accurate
- ✅ Optional fields are clearly marked
- ✅ Enum usage is consistent with base schema definitions

This comprehensive set of response models eliminates the missing model discrepancies and provides complete API contracts for all endpoints.