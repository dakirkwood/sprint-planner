# ReviewService Architecture Decisions

## UPDATED: December 26, 2025
- Added `arq_pool: ArqRedis` to constructor dependencies
- Split `validate_adf()` into public method (enqueue) and internal method (execute)
- Added ARQ job integration pattern for ADF validation
- Added ADF validation response models

---

## Method Signatures

```python
from arq.connections import ArqRedis
from typing import Optional, Callable, List
from uuid import UUID

class ReviewService:
    def __init__(self, 
                 ticket_repo: TicketRepositoryInterface,
                 session_repo: SessionRepositoryInterface,
                 error_repo: ErrorRepositoryInterface,
                 jira_service: JiraService,
                 arq_pool: ArqRedis = None):  # Optional - not needed inside worker jobs
        self.ticket_repo = ticket_repo
        self.session_repo = session_repo
        self.error_repo = error_repo
        self.jira_service = jira_service
        self.arq_pool = arq_pool

    # =========================================================================
    # TICKET OPERATIONS (No background jobs needed)
    # =========================================================================
    
    async def get_tickets_summary(self, session_id: UUID) -> TicketListResponse:
        """Get paginated ticket list with summary info."""
        pass
    
    async def get_ticket_detail(self, session_id: UUID, ticket_id: UUID) -> TicketDetailResponse:
        """Get full ticket details for editing."""
        pass
    
    async def update_ticket(self, session_id: UUID, ticket_id: UUID, 
                           request: TicketUpdateRequest) -> TicketUpdateResponse:
        """Update ticket content. Handles auto-attachment generation for oversized content."""
        pass
    
    async def bulk_assign_tickets(self, session_id: UUID, 
                                  request: BulkAssignRequest) -> BulkAssignResponse:
        """Bulk update sprint/assignee for multiple tickets."""
        pass

    # =========================================================================
    # DEPENDENCY MANAGEMENT (No background jobs needed)
    # =========================================================================
    
    async def get_dependency_graph(self, session_id: UUID) -> DependencyGraphResponse:
        """Get ticket dependency visualization data."""
        pass
    
    async def update_ticket_ordering(self, session_id: UUID, 
                                     request: TicketOrderingRequest) -> TicketOrderingResponse:
        """Update ticket order within entity groups."""
        pass
    
    async def update_cross_group_dependencies(self, session_id: UUID, 
                                              request: CrossGroupDependencyRequest) -> CrossGroupDependencyResponse:
        """Update dependencies between tickets in different groups."""
        pass

    # =========================================================================
    # ADF VALIDATION - PUBLIC METHOD (Enqueues background job)
    # =========================================================================
    
    async def validate_adf(self, session_id: UUID) -> AdfValidationStartResponse:
        """
        Validate session state and enqueue ADF validation job.
        Returns immediately with task_id for progress tracking.
        """
        pass
    
    async def get_adf_validation_status(self, session_id: UUID) -> AdfValidationStatusResponse:
        """Get current ADF validation status from database."""
        pass

    # =========================================================================
    # ADF VALIDATION - INTERNAL METHOD (Called by ARQ worker)
    # =========================================================================
    
    async def execute_adf_validation(
        self,
        session_id: UUID,
        task_id: UUID,
        progress_callback: Callable[[float, str, dict], None]
    ) -> None:
        """
        Execute actual ADF validation. Called by ARQ worker.
        
        Args:
            session_id: Session to validate
            task_id: Task ID for validation and progress tracking
            progress_callback: Function to publish progress updates
                              Signature: (percentage, stage_description, details_dict)
        """
        pass

    # =========================================================================
    # EXPORT READINESS & ROLLBACK (No background jobs needed)
    # =========================================================================
    
    async def check_export_readiness(self, session_id: UUID) -> ExportReadinessResponse:
        """Check if session is ready for Jira export."""
        pass
    
    async def get_rollback_impact(self, session_id: UUID, 
                                  target_stage: str) -> RollbackImpactResponse:
        """Analyze impact of rolling back to earlier stage."""
        pass
    
    async def rollback_to_stage(self, session_id: UUID, 
                                target_stage: str) -> RollbackResponse:
        """Execute rollback to specified stage."""
        pass
```

## Key Decisions Made

### 1. ARQ Pool Dependency
- **Decision**: Add `arq_pool: ArqRedis` as optional constructor dependency
- **Optional in workers**: Jobs create service instances without arq_pool
- **Required in endpoints**: API endpoints need arq_pool to enqueue jobs
- **Rationale**: Clean separation between enqueueing (API) and executing (worker)

### 2. Single Background Task Method
- **Decision**: Only `validate_adf()` requires public/internal split
- **Rationale**: All other methods are fast database operations; ADF validation calls Jira API per ticket

### 3. Progress Callback Pattern
- **Decision**: Pass progress callback function to `execute_adf_validation()`
- **Callback signature**: `(percentage: float, stage: str, details: dict) -> None`
- **Worker provides callback**: Publishes to Redis pub/sub
- **Rationale**: Decouples progress reporting from execution logic

### 4. ADF Validation Invalidation (within update_ticket)
- **Decision**: Any ticket edit invalidates ADF validation
- **Implementation**: Sets `session_validation.validation_passed = False` and `last_invalidated_at = NOW()`
- **Rationale**: Ensures export only proceeds with validated content

### 5. Automatic Attachment Generation (within update_ticket)
- **Decision**: Service handles attachment generation when content exceeds 30,000 characters
- **Rationale**: Business rule enforcement belongs in service layer

### 6. Service-Level Dependency Validation
- **Decision**: Circular dependency detection handled in service layer
- **Rationale**: Requires business logic understanding of valid relationships

### 7. Service-Level Export Readiness
- **Decision**: `check_export_readiness()` coordinates multiple conditions
- **Checks**: `validation_passed = True`, no blocking errors, all tickets ready
- **Rationale**: Business logic coordination across multiple repository checks

## Internal Implementation Notes

### ADF Validation Flow (within execute_adf_validation)
```python
# 1. Get all tickets for session
# 2. For each ticket:
#    - Call jira_service.validate_adf_conversion(ticket.description)
#    - Track passed/failed counts
#    - Collect error details for failed tickets
#    - Publish progress via callback
# 3. Update session_validation record with results
# 4. Complete the task
```

### Automatic Attachment Generation (within update_ticket)
```python
# When content exceeds 30,000 characters:
# 1. Generate markdown attachment with full content
# 2. Replace description with "See attached file: [filename] for complete details"
# 3. Store original content for recovery
# 4. Create/update Attachment record
```

### Circular Dependency Detection (within dependency methods)
- Validates dependency chains don't create circular references
- Checks both within-group ordering and cross-group dependencies
- Returns validation warnings rather than blocking errors

### Export Readiness Coordination (within check_export_readiness)
- Validates: `adf_validation_passed = True`
- Checks: `last_invalidated_at` is not newer than `last_validated_at`
- Checks: No blocking errors in session_errors
- Verifies: All tickets meet minimum requirements
- Coordinates: Multiple repository checks into single business decision

## Response Models

### ADF Validation Response Models

```python
# /backend/app/schemas/review.py

class AdfValidationStartResponse(BaseResponse):
    """Returned when ADF validation job is enqueued."""
    task_id: UUID
    session_id: UUID
    status: str = "validating"
    total_tickets: int
    estimated_duration_seconds: int


class AdfValidationAlreadyRunningResponse(BaseResponse):
    """Returned when validation is already in progress (idempotency)."""
    task_id: UUID
    session_id: UUID
    status: str = "validating"
    progress_percentage: float
    tickets_validated: int
    total_tickets: int
    started_at: datetime


class AdfValidationStatusResponse(BaseResponse):
    """Returned when polling for validation progress."""
    session_id: UUID
    task_id: UUID
    status: str  # "validating", "completed", "failed"
    progress_percentage: float
    tickets_validated: int
    total_tickets: int
    passed_count: int
    failed_count: int
    started_at: datetime
    estimated_time_remaining_seconds: Optional[int] = None


class AdfValidationError(BaseModel):
    """Individual ticket ADF validation error."""
    ticket_id: UUID
    title: str
    error: str


class AdfValidationCompletedResponse(BaseResponse):
    """Returned when validation has finished."""
    session_id: UUID
    task_id: UUID
    status: str = "completed"
    validation_passed: bool
    passed_count: int
    failed_count: int
    total_tickets: int
    errors: List[AdfValidationError]
    validated_at: datetime
    export_ready: bool  # True if validation_passed and no other blockers


class AdfValidationFailedResponse(BaseResponse):
    """Returned when validation process itself failed."""
    session_id: UUID
    task_id: UUID
    status: str = "failed"
    error_category: str  # "temporary" or "admin_required"
    user_message: str
    recovery_actions: List[str]
    failed_at: datetime
    progress_before_failure: float
    retry_available: bool = True
```

## Worker Integration

### Job Function Registration

```python
# /backend/app/workers/validation_worker.py
async def validate_adf_job(ctx: dict, session_id: UUID, task_id: UUID) -> None:
    """ARQ job function for ADF validation."""
    # Build dependencies from worker context
    # Delegate to ReviewService.execute_adf_validation()
```

### Worker Settings Update

```python
# /backend/app/workers/settings.py
from .validation_worker import validate_adf_job

class WorkerSettings:
    functions = [
        generate_tickets_job,
        export_session_job,
        validate_adf_job,  # Added
    ]
```

## Dependencies

- **TicketRepositoryInterface**: Ticket CRUD, dependency management, bulk operations
- **SessionRepositoryInterface**: Session state updates, task management, stage transitions
- **ErrorRepositoryInterface**: Error tracking and validation state
- **JiraService**: ADF validation API calls
- **ArqRedis**: Background job enqueueing (optional, not needed in workers)
