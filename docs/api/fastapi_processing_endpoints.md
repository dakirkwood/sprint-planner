# FastAPI Processing Stage Endpoints - Implementation Specification

## Overview

The Processing Stage handles the transition from validated CSV files to generated tickets using single-pass processing with LLM integration. This stage represents the core value generation of the application, converting structured CSV data into contextual Jira tickets.

## Architectural Decisions

### Core Principles
- **Single-pass processing**: Unified `TicketGenerator` replaces complex multi-agent coordination
- **Clean slate recovery**: Failed processing can be retried without preserving partial state
- **All-or-nothing consistency**: Complete success or clean failure with comprehensive error feedback
- **Locked LLM provider**: Provider choice made at session creation remains consistent throughout processing
- **Graceful error handling**: Comprehensive error collection with categorized recovery guidance
- **Real-time progress**: WebSocket updates with fallback to REST polling

### Processing Flow Architecture
1. **Initiation**: Empty POST request triggers processing with all context from database
2. **Progress Tracking**: Real-time WebSocket updates with entity group granularity
3. **Error Collection**: Comprehensive error reporting with grouping and technical details
4. **Recovery Options**: Retry, cancellation, and rollback capabilities
5. **Stage Transitions**: Automatic progression with manual rollback options

## Core Processing Endpoints

### 1. Processing Initiation
```python
POST /api/processing/generate-tickets/{session_id}
```

**Request:**
```python
# Empty body - all context from database
{}
```

**Success Response (HTTP 202):**
```python
class ProcessingStartResponse(BaseModel):
    task_id: UUID
    session_id: UUID
    status: str = "processing"
    estimated_duration_minutes: int  # Based on file count and LLM provider
    total_files: int
    estimated_tickets: int  # Rough estimate from entity counts
    llm_provider: str  # Confirms which provider will be used
```

**Idempotency Response (HTTP 202):**
```python
class ProcessingAlreadyRunningResponse(BaseModel):
    task_id: UUID  # Existing task ID
    session_id: UUID
    status: str = "processing" 
    progress_percentage: float
    current_stage: str  # "Processing Content entities (2 of 6 groups)"
    started_at: datetime
```

**Key Decisions:**
- **Empty request body**: All processing context stored in database from upload stage
- **Async with immediate response**: Returns task ID immediately for progress tracking
- **Idempotency handling**: Returns existing task if already running (prevents accidental double-clicks)
- **Validation delegated to service layer**: Endpoint focused on orchestration, not validation
- **LLM connectivity check**: Validates chosen provider availability before starting

**Database State Changes:**
- `sessions.current_stage = 'processing'`
- `sessions.processing_task_id = new_task_id`
- `sessions.processing_started_at = NOW()`

### 2. Progress Tracking (WebSocket)
```
ws://localhost:8000/api/processing/progress/{session_id}
```

**Connection Authentication:**
- Session ID validation against database
- Reject connection if session not found or not accessible to authenticated user

**Progress Message Types:**

*Normal Progress (entity group level):*
```python
{
    "type": "progress",
    "session_id": "uuid",
    "task_id": "uuid", 
    "status": "processing",
    "progress_percentage": 33.3,
    "current_stage": "Processing Content entities (2 of 6 groups)",
    "entity_group": "Content",
    "entities_completed": 2,
    "total_entities": 6,
    "estimated_time_remaining_minutes": 4,
    "last_updated": "2024-01-15T10:30:00Z"
}
```

*Debug Mode Progress (detailed):*
```python
{
    "type": "progress_detailed",
    "session_id": "uuid",
    "current_stage": "Processing Content entities (2 of 6 groups)",
    "current_entity": "Processing Product bundle (5 fields, 2 view modes)",
    "llm_request_status": "completed",
    "llm_tokens_used": 1250,
    "processing_time_ms": 2340,
    // ... same base fields as normal progress
}
```

*Error Message (then close):*
```python
{
    "type": "error",
    "session_id": "uuid", 
    "task_id": "uuid",
    "status": "failed",
    "error_category": "admin_required",
    "user_message": "AI service quota exceeded",
    "recovery_actions": ["Contact administrator", "Wait for quota reset"],
    "technical_details": {"provider": "openai", "error_code": "quota_exceeded"}
}
```

*Completion Message (then close):*
```python
{
    "type": "completed",
    "session_id": "uuid",
    "task_id": "uuid", 
    "status": "completed",
    "tickets_generated": 23,
    "total_cost": 1.85,
    "processing_time_minutes": 3.2,
    "ready_for_review": true
}
```

**Key Decisions:**
- **Per-session WebSocket**: One connection handles all processing for that session
- **Entity group granularity**: Standard progress updates per entity group (Content, Media, Views, etc.)
- **Debug mode detail**: Detailed progress when `APP_DEBUG_MODE=true`
- **Error handling**: Send final error message then close connection for clean lifecycle
- **Session authentication**: Validate session ownership through database lookup

### 3. Status Polling (REST Fallback)
```python
GET /api/processing/status/{session_id}
```

**Rate Limiting:** 1 request per 2 seconds per session

**Currently Processing Response (HTTP 200):**
```python
class ProcessingStatusResponse(BaseModel):
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
```

**Processing Completed Response (HTTP 200):**
```python
class ProcessingCompletedResponse(BaseModel):
    session_id: UUID
    task_id: UUID
    status: str = "completed"
    tickets_generated: int
    entity_groups_processed: List[EntityGroupSummary]
    total_cost: float  # Overall total, no breakdown
    processing_time_minutes: float
    llm_provider: str
    model_used: str
    completed_at: datetime
    ready_for_review: bool = True
    # Include technical_details only if APP_DEBUG_MODE=true
    technical_details: Optional[dict] = None

class EntityGroupSummary(BaseModel):
    group_name: str  # "Content", "Media", etc.
    tickets_created: int
    entities_processed: int
```

**Processing Failed Response (HTTP 200):**
```python
class ProcessingFailedResponse(BaseModel):
    session_id: UUID
    task_id: UUID
    status: str = "failed"
    error_category: str
    user_message: str
    recovery_actions: List[str]
    failed_at: datetime
    progress_before_failure: float
    retry_available: bool
    # Include technical_details only if APP_DEBUG_MODE=true
    technical_details: Optional[dict] = None
```

**Key Decisions:**
- **Read-only endpoint**: No side effects, doesn't update session state
- **Rate limiting**: Prevents excessive polling (1 request per 2 seconds)
- **Overall cost totals only**: No detailed breakdown to keep response simple
- **Debug mode controlled details**: Technical information only when debugging enabled
- **Session state managed by background task**: Processing task updates session state, endpoint just reads

## Error Handling & Recovery Endpoints

### 4. Processing Retry
```python
POST /api/processing/retry/{session_id}
```

**Request:**
```python
# Empty body - all context from database
{}
```

**Success Response (HTTP 202):**
```python
class ProcessingRetryResponse(BaseModel):
    task_id: UUID  # New task ID for retry attempt
    session_id: UUID
    status: str = "processing"
    retry_attempt: int  # 1, 2, or 3
    remaining_retries: int
    cleaned_up_tickets: int  # How many partial tickets were deleted
    previous_error_preserved: bool = True
    llm_provider: str  # Confirms locked provider choice
```

**Retry Not Available (HTTP 422):**
```python
{
    "error_category": "user_fixable",
    "user_message": "Retry not available for this error type. Please return to upload stage to fix CSV issues.",
    "recovery_actions": ["Return to upload stage", "Fix CSV validation errors"],
    "last_error_category": "user_fixable",  # Why retry unavailable
    "current_session_stage": "processing_failed"
}
```

**Maximum Retries Exceeded (HTTP 422):**
```python
{
    "error_category": "admin_required", 
    "user_message": "Maximum retry attempts (3) exceeded. Please contact administrator.",
    "recovery_actions": ["Contact system administrator", "Session may need to be reset"],
    "retry_attempts_used": 3,
    "first_error_at": "2024-01-15T10:30:00Z",
    "last_error_category": "temporary"
}
```

**Key Decisions:**
- **Retry only for appropriate errors**: "temporary" and "admin_required" categories only
- **Clean slate approach**: Delete partial tickets, preserve error logs for audit
- **Maximum 3 retries per session**: Prevents infinite retry loops
- **Provider choice locked**: Cannot switch LLM providers during retry
- **Session stage remains 'processing'**: Don't force back to upload stage

**Database State Changes:**
- Increment `sessions.retry_count`
- Delete any `tickets` records from previous failed attempt
- Preserve `session_errors` from previous attempts (audit trail)
- Generate new `processing_task_id`
- Update `sessions.processing_started_at = NOW()`

### 5. Processing Cancellation
```python
POST /api/processing/cancel/{session_id}
```

**Request:**
```python
# Empty body
{}
```

**Success Response (HTTP 200):**
```python
class ProcessingCancellationResponse(BaseModel):
    session_id: UUID
    task_id: UUID  # The cancelled task
    status: str = "cancelled"
    cancelled_at: datetime
    graceful_shutdown: bool = True
    
    # Cleanup summary
    partial_tickets_deleted: int
    entity_groups_completed: int
    entity_groups_cancelled: int
    
    # Cost tracking for completed work
    cost_for_completed_work: float
    llm_tokens_used: int
    processing_time_minutes: float
    
    # Session state
    session_returned_to_stage: str = "upload"
    can_modify_files: bool = True
```

**Key Decisions:**
- **Graceful cancellation**: Complete current LLM request then stop
- **Clean slate approach**: Delete partial tickets, preserve completed work costs
- **Return to upload stage**: Allows file modifications after cancellation
- **Cost tracking**: Report costs for completed work before cancellation

**Graceful Shutdown Process:**
1. Set cancellation flag in background task
2. Complete current LLM request if in progress
3. Stop before starting next entity group
4. Clean up partial results
5. Return success response with summary

### 6. Error Detail Reporting
```python
GET /api/processing/errors/{session_id}
```

**Query Parameters:**
```python
category: Optional[str] = None      # "user_fixable", "admin_required", "temporary"
retry_attempt: Optional[int] = None # Filter by specific retry attempt (1, 2, 3)
group_similar: bool = True          # Group similar errors together
include_technical: bool = False     # Include full technical details (auto-true if debug mode)
page: int = 1
limit: int = 50
```

**Response:**
```python
class ProcessingErrorsResponse(BaseModel):
    session_id: UUID
    total_errors: int
    filtered_errors: int
    retry_attempts: List[int]  # [1, 2, 3] - which attempts had errors
    error_groups: List[ErrorGroup]
    pagination: PaginationInfo

class ErrorGroup(BaseModel):
    group_id: UUID
    error_type: str           # "llm_timeout", "entity_processing_failed", etc.
    error_category: str       # "user_fixable", "admin_required", "temporary"
    error_count: int          # How many similar errors in this group
    first_occurred_at: datetime
    last_occurred_at: datetime
    
    # Summary information
    summary_message: str      # "5 LLM timeout errors during Content entity processing"
    affected_entities: List[str]  # ["Product bundle", "Event bundle", ...]
    retry_attempts: List[int] # Which retry attempts had this error
    
    # Sample error for preview
    sample_error: ProcessingError
    
    # Full details (if requested or debug mode)
    all_errors: Optional[List[ProcessingError]]
```

**Individual Error Detail:**
```python
GET /api/processing/errors/{session_id}/{error_id}
```

**Error Export:**
```python
GET /api/processing/errors/{session_id}/export?format=json|text|csv
```

**Key Decisions:**
- **All errors from current session**: Full history across retry attempts
- **Filtering options**: By category, retry attempt, with pagination
- **Error grouping**: Similar errors grouped with expansion capability
- **Technical details controlled by debug mode**: Full context when debugging
- **Export functionality**: Multiple formats for admin troubleshooting

## Stage Management Endpoints

### 7. Session Transitions
```python
POST /api/processing/transition-to-review/{session_id}
```

**Key Decision:** Automatic transition when processing completes, manual endpoint for edge case recovery only.

### 8. Rollback Capabilities
```python
POST /api/processing/rollback-to-processing/{session_id}
POST /api/processing/rollback-to-upload/{session_id}
```

**Key Decisions:**
- **Rollback to processing**: From review stage only, requires explicit confirmation
- **Rollback to upload**: From review or processing stages, option to preserve CSV files
- **Data integrity**: All rollbacks clean up dependent data (tickets, attachments, dependencies)
- **Audit trail**: All transitions logged for tracking

## Service Integration Endpoints

### 9. LLM Service Health Check
```python
GET /api/processing/validate-llm-service/{session_id}?force_refresh=false
```

**Response:**
```python
class LLMServiceHealthResponse(BaseModel):
    session_id: UUID
    provider: str  # "openai" or "anthropic"
    model: str     # "gpt-4o" or "claude-3-sonnet-20240229"
    
    # Health status
    overall_status: str  # "healthy", "degraded", "unavailable"
    connectivity: str    # "ok", "timeout", "unreachable"
    authentication: str  # "valid", "invalid", "expired"
    quota_status: str    # "available", "low", "exceeded"
    model_availability: str  # "available", "unavailable", "deprecated"
    
    # Cost estimation
    estimated_cost: float
    estimated_tokens: int
    quota_remaining: Optional[float]
    cost_breakdown: CostBreakdown
    
    # Cache info
    cached_at: datetime
    cache_expires_at: datetime
    checked_at: datetime
```

**Key Decisions:**
- **Both automatic and manual checks**: Before processing starts + user-requested
- **Full validation scope**: Connectivity + auth + quota + model availability
- **Detailed response with cost estimates**: Help users understand processing costs
- **5-minute cache with manual refresh**: Balance between accuracy and API usage

**Integration with Processing Flow:**
- Automatic health check called by `generate-tickets` endpoint before starting
- If health check fails, processing blocked with clear error message
- Manual check available via "Test AI Service" button in UI

## Error Handling Strategy

### Error Categories
All processing errors follow the "who can fix it" categorization:

- **user_fixable (HTTP 422)**: Business rule violations, validation failures
- **admin_required (HTTP 403/500)**: External service configuration, quota issues  
- **temporary (HTTP 503)**: Network timeouts, external service unavailable

### Error Response Patterns
- **Comprehensive error collection**: All-or-nothing approach with complete error feedback
- **Pattern detection**: Group similar errors for cleaner user experience
- **Technical details in debug mode**: Full context when `APP_DEBUG_MODE=true`
- **Recovery guidance**: Specific, actionable steps for each error category

### Database Integration
- All errors stored in `session_errors` table with full context
- Linked to specific files, entities, or operations for debugging
- Preserved across session recovery for comprehensive audit trail

## Database State Management

### Key Table Updates
- **sessions**: `current_stage`, `processing_task_id`, `retry_count`, `processing_started_at`
- **tickets**: Generated ticket records with entity grouping and dependencies
- **session_errors**: Comprehensive error logging with categorization
- **attachments**: Auto-generated attachments for oversized content

### State Transition Rules
- Users cannot skip required workflow steps
- Database `sessions.current_stage` enforces progression rules
- Clean slate recovery maintains data integrity
- Automatic stage progression on successful completion

## Implementation Priority

### Core Processing Workflow (MVP 1)
1. Processing initiation with idempotency handling
2. WebSocket progress tracking with entity group granularity  
3. Status polling endpoint with rate limiting
4. Basic error handling and retry capabilities

### Enhanced Error Handling (MVP 2)
1. Comprehensive error detail reporting with grouping
2. Error export functionality for debugging
3. LLM service health checking and validation
4. Advanced retry and cancellation capabilities

### Complete Stage Management (MVP 3)
1. Full rollback capabilities to processing and upload stages
2. Advanced error recovery workflows
3. Session transition edge case handling
4. Complete audit trail and debugging capabilities

## Success Criteria

- ✅ Single-pass processing generates same quality tickets as complex multi-agent system
- ✅ Real-time progress tracking provides appropriate user feedback during processing
- ✅ Comprehensive error handling follows "who can fix it" categorization consistently
- ✅ Clean slate recovery prevents partial/corrupted data states
- ✅ LLM service validation prevents expensive processing attempts when services unavailable
- ✅ Retry and cancellation capabilities handle failures gracefully
- ✅ Stage transitions maintain data integrity while providing user flexibility
- ✅ Database integration enables standard operational patterns and session recovery
- ✅ Error reporting provides sufficient detail for debugging without overwhelming users
- ✅ Processing costs are tracked and reported transparently to users