# FastAPI Jira Integration Endpoints - Implementation Specification

## Overview

The Jira Integration stage handles the final export of validated tickets to Jira, following a sequential processing approach with fail-fast error handling and retry capabilities. This stage represents the culmination of the workflow where generated tickets become actual Jira issues.

## Architectural Decisions

### Core Principles
- **Session-level export**: All-or-nothing approach with database schema flagged for future partial export support
- **Sequential processing**: One ticket at a time with configurable delays (1.5 seconds default)
- **Fail-fast with graceful fallbacks**: Hard stops for auth/network issues, graceful fallbacks for field validation
- **On-demand ADF conversion**: Fresh conversion during export using latest user edits
- **Real-time progress tracking**: WebSocket with REST polling fallback
- **Retry from failure point**: Resume from failed ticket without recreating successful ones
- **Limited retries**: Maximum 3 retry attempts per session

### Database Schema Support
```sql
-- Future partial export support
ALTER TABLE tickets ADD COLUMN jira_export_status VARCHAR(20) DEFAULT 'pending';
-- Values: 'pending', 'exported', 'failed', 'skipped'

-- Export tracking fields
ALTER TABLE sessions ADD COLUMN export_task_id UUID;
ALTER TABLE sessions ADD COLUMN export_started_at TIMESTAMP;
ALTER TABLE sessions ADD COLUMN export_failed_at TIMESTAMP;
ALTER TABLE sessions ADD COLUMN failed_at_ticket_order INTEGER;
ALTER TABLE sessions ADD COLUMN export_retry_count INTEGER DEFAULT 0;
```

## Core Export Endpoints

### 1. Main Export Initiation
```http
POST /api/jira/export-session/{session_id}
```

**Request:**
```python
# Empty body - all context from database
{}
```

**Success Response (HTTP 202):**
```python
class ExportStartResponse(BaseModel):
    task_id: UUID
    session_id: UUID
    status: str = "exporting"
    total_tickets: int
    estimated_duration_minutes: int  # tickets × 1.5 seconds + dependency creation
    jira_project_key: str
    started_at: datetime
```

**Idempotency Response (HTTP 202):**
```python
class ExportAlreadyRunningResponse(BaseModel):
    task_id: UUID  # Existing task ID
    session_id: UUID
    status: str = "exporting"
    progress_percentage: float
    current_ticket_title: str
    started_at: datetime
```

**Export Execution Sequence:**
1. Final validation checks (project accessible, user permissions)
2. Load tickets in dependency order from database
3. Sequential processing for each ticket:
   - Convert HTML → ADF (fresh conversion)
   - Upload attachment if present
   - Create Jira ticket with graceful field fallbacks
   - Store Jira ticket key/URL in database
   - Apply 1.5 second delay
4. Create dependency links after all tickets exist
5. Final status update and completion response

**Database State Changes:**
```sql
UPDATE sessions SET 
    current_stage = 'jira_export',
    export_task_id = 'new_uuid',
    export_started_at = NOW(),
    status = 'exporting'
WHERE id = session_id;
```

### 2. Progress Tracking (WebSocket)
```
ws://localhost:8000/api/jira/export/progress/{session_id}
```

**Progress Message:**
```python
{
    "type": "export_progress",
    "session_id": "uuid",
    "status": "exporting",
    "progress_percentage": 34.5,
    "current_stage": "Creating ticket 30 of 87: Configure Product Fields",
    "tickets_completed": 29,
    "tickets_failed": 0,
    "total_tickets": 87,
    "estimated_time_remaining_minutes": 2,
    "current_jira_project": "PROJ"
}
```

**Completion Message:**
```python
{
    "type": "export_complete",
    "status": "completed",
    "tickets_created": 87,
    "dependencies_created": 12,
    "manual_fixes_needed": 3,
    "total_processing_time_minutes": 2.8
}
```

**Failure Message:**
```python
{
    "type": "export_failed",
    "status": "failed",
    "failed_at_ticket": 45,
    "error_category": "temporary",
    "retry_available": true,
    "error_message": "Network timeout connecting to Jira"
}
```

### 3. Status Polling (REST Fallback)
```http
GET /api/jira/export-status/{session_id}
```

**Rate Limiting:** 1 request per 2 seconds per session

**Currently Exporting Response (HTTP 200):**
```python
class ExportStatusResponse(BaseModel):
    session_id: UUID
    task_id: UUID
    status: str = "exporting"
    progress_percentage: float
    tickets_completed: int
    total_tickets: int
    current_ticket_title: Optional[str]
    estimated_time_remaining_minutes: Optional[int]
```

**Export Completed Response (HTTP 200):**
```python
class ExportCompletedResponse(BaseModel):
    session_id: UUID
    task_id: UUID
    status: str = "completed"
    jira_tickets_created: int
    dependencies_created: int
    manual_fixes_needed: int
    total_processing_time_minutes: float
    completed_at: datetime
```

**Export Failed Response (HTTP 200):**
```python
class ExportFailedResponse(BaseModel):
    session_id: UUID
    task_id: UUID
    status: str = "failed"
    failed_at_ticket_order: int
    error_category: str  # "user_fixable", "admin_required", "temporary"
    user_message: str
    recovery_actions: List[str]
    retry_available: bool
    retry_attempts_used: int
```

## Error Handling & Recovery

### 4. Export Retry
```http
POST /api/jira/retry-failed/{session_id}
```

**Request:**
```python
# Empty body - all context from database
{}
```

**Success Response (HTTP 202):**
```python
class ExportRetryResponse(BaseModel):
    task_id: UUID  # New task ID for retry
    session_id: UUID
    status: str = "exporting"
    retry_attempt: int
    remaining_retries: int
    resuming_from_ticket_order: int
    preserved_successful_tickets: int
```

**Max Retries Exceeded (HTTP 422):**
```python
{
    "error_category": "admin_required",
    "user_message": "Maximum retry attempts (3) exceeded. Please contact administrator.",
    "recovery_actions": ["Contact system administrator", "Session may need manual cleanup"],
    "retry_attempts_used": 3,
    "first_error_at": "2024-01-15T10:30:00Z"
}
```

**Retry Strategy:**
- **Resume from failed ticket**: Don't recreate successful tickets
- **Preserve Jira ticket keys**: Re-use successfully created tickets
- **3 retry limit**: Prevent infinite retry loops
- **Clean slate detection**: Log orphaned tickets for manual cleanup if database update fails

### 5. Error Handling Categories

**Graceful Fallbacks (Continue Export):**
- **Field validation issues**: Invalid assignee → unassigned, invalid sprint → no sprint
- **Non-critical field problems**: Priority not available → default priority
- **Track for manual fixes**: Store guidance for post-export corrections

**Hard Stops (Immediate Failure):**
- **Authentication issues**: Token expired, permissions revoked
- **Network problems**: Jira unreachable, connection timeout
- **Critical errors**: Project deleted, issue type unavailable

**Database Consistency Handling:**
- **Log Jira keys immediately**: After successful ticket creation
- **Detection on retry**: Check for existing tickets before creating duplicates
- **Manual cleanup guidance**: Provide specific ticket keys for admin cleanup

## Validation & Testing Endpoints

### 6. Project Validation (Called During Session Setup)
```http
POST /api/jira/validate-project
```

**Request:**
```python
class ProjectValidationRequest(BaseModel):
    project_key: str
    user_requirements: ProjectRequirements

class ProjectRequirements(BaseModel):
    requires_sprint_assignment: bool  # From environment config
    requires_assignee: bool
    requires_priority_levels: bool
```

**Response:**
```python
class ProjectValidationResponse(BaseModel):
    project_key: str
    project_name: str
    validation_status: str  # "valid", "invalid"
    
    # Core permissions
    can_create_tasks: bool
    can_view_project: bool
    
    # Cached dropdown data
    available_sprints: List[SprintOption]
    team_members: List[TeamMemberOption]
    priority_levels: List[PriorityOption]
    
    # Issues
    validation_warnings: List[ValidationWarning]
    blocking_issues: List[str]

class SprintOption(BaseModel):
    id: str
    name: str
    state: str  # "active", "closed", "future"
```

### 7. Manual ADF Testing (Called from Review Stage)
```http
POST /api/jira/test-adf-conversion/{session_id}
```

**Request:**
```python
class AdfTestRequest(BaseModel):
    ticket_ids: List[UUID]  # Specific tickets, or empty for all
    include_attachments: bool = True
```

**Response:**
```python
class AdfTestResponse(BaseModel):
    session_id: UUID
    tickets_tested: int
    all_passed: bool
    passed: int
    failed: int
    results: List[AdfTestResult]

class AdfTestResult(BaseModel):
    ticket_id: UUID
    ticket_title: str
    status: str  # "passed", "failed"
    
    # Success info
    adf_size_bytes: Optional[int]
    character_reduction: Optional[float]
    
    # Failure info
    error_message: Optional[str]
    suggested_fix: Optional[str]
    
    # Attachment validation
    attachment_upload_tested: bool
    attachment_upload_status: Optional[str]  # "passed", "failed", "skipped"
```

**Testing Approach:**
- **Fresh tests every time**: No caching due to user edits
- **Validate attachment upload**: Test uploadability without actually uploading
- **Selective testing**: Users can test specific tickets they're concerned about

## Final Results & Cleanup

### 8. Export Results
```http
GET /api/jira/export-results/{session_id}
```

**Response:**
```python
class ExportResultsResponse(BaseModel):
    session_id: UUID
    total_tickets_created: int
    jira_tickets: List[JiraTicketReference]
    dependencies_created: int
    manual_fixes: List[ManualFixGuidance]
    total_processing_time_minutes: float

class JiraTicketReference(BaseModel):
    ticket_id: UUID  # Internal ID
    jira_key: str    # "PROJ-123"
    jira_url: str    # Direct link
    title: str

class ManualFixGuidance(BaseModel):
    jira_key: str
    title: str
    issue_type: str  # "assignee_invalid", "sprint_not_found"
    recommended_action: str
    jira_url: str
```

## Database State Management

### Real-Time Updates During Export
```sql
-- Per-ticket updates (as we go)
UPDATE tickets SET 
    jira_ticket_key = 'PROJ-123',
    jira_ticket_url = 'https://ecitizen.atlassian.net/browse/PROJ-123',
    jira_export_status = 'exported',
    exported_at = NOW()
WHERE id = ticket_id;

-- Completion
UPDATE sessions SET 
    current_stage = 'completed',
    status = 'completed',
    completed_at = NOW(),
    export_task_id = NULL
WHERE id = session_id;

-- Failure
UPDATE sessions SET 
    status = 'export_failed',
    export_failed_at = NOW(),
    failed_at_ticket_order = 45,
    export_retry_count = export_retry_count + 1
WHERE id = session_id;
```

### State Preservation Strategy
- **Preserve successful progress**: Keep Jira ticket keys from successful creations
- **Track failure context**: Store exact failure point for retry resume
- **Maintain audit trail**: All state changes logged for debugging
- **Clean completion**: Clear task IDs when export fully complete

## HTTP Status Code Strategy

**Standard Patterns:**
- **202 Accepted**: Long-running async operations (export, retry)
- **200 OK**: Successful data retrieval (status, results)
- **422 Unprocessable Entity**: Business rule violations (max retries, invalid session state)
- **403 Forbidden**: Permission issues (Jira permissions revoked)
- **503 Service Unavailable**: Temporary external service issues
- **409 Conflict**: Timing issues (retry while export running)

## Implementation Priority

### Core Export Workflow (MVP 1)
1. Main export endpoint with sequential processing
2. WebSocket progress tracking with REST fallback
3. Basic retry mechanism from failure point
4. Project validation during session setup

### Enhanced Error Handling (MVP 2)
1. Comprehensive error categorization and recovery guidance
2. Manual ADF testing endpoint
3. Database consistency handling for orphaned tickets
4. Complete manual fix guidance system

### Complete Export Management (MVP 3)
1. Advanced retry strategies and cleanup
2. Enhanced progress tracking with detailed timing
3. Complete audit trail and debugging capabilities
4. Future partial export preparation

## Success Criteria

- ✅ Sequential export creates tickets reliably with appropriate delays and rate limiting
- ✅ Fail-fast approach with graceful fallbacks provides optimal user experience
- ✅ WebSocket progress tracking keeps users informed during long-running exports
- ✅ Retry mechanism preserves progress and resumes from exact failure point
- ✅ Project validation prevents export failures through early permission checking
- ✅ Database state management maintains consistency and enables reliable session recovery
- ✅ Error handling provides clear categorization and actionable recovery guidance
- ✅ Manual fix tracking helps users complete setup in Jira after export
- ✅ Real-time database updates provide complete audit trail for debugging
- ✅ HTTP status codes follow standard patterns for predictable client behavior