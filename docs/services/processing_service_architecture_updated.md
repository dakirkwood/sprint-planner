# ProcessingService Architecture Decisions

## UPDATED: December 25, 2025
- Added `arq_pool: ArqRedis` to constructor dependencies
- Split processing into public method (enqueue) and internal method (execute)
- Added ARQ job integration pattern
- Updated all method signatures for async
- Added progress callback pattern for Redis pub/sub

---

## Method Signatures

```python
from arq.connections import ArqRedis
from typing import Optional, Callable, Dict, List
from uuid import UUID

class ProcessingService:
    def __init__(self, 
                 session_repo: SessionRepositoryInterface,
                 ticket_repo: TicketRepositoryInterface,
                 upload_repo: UploadRepositoryInterface,
                 error_repo: ErrorRepositoryInterface,
                 llm_service: LLMService,
                 arq_pool: ArqRedis = None):  # Optional - not needed inside worker jobs
        self.session_repo = session_repo
        self.ticket_repo = ticket_repo
        self.upload_repo = upload_repo
        self.error_repo = error_repo
        self.llm_service = llm_service
        self.arq_pool = arq_pool

    # =========================================================================
    # PUBLIC METHODS (Called by API endpoints - enqueue background jobs)
    # =========================================================================
    
    # Core Processing - Enqueues background job
    async def generate_tickets(self, session_id: UUID) -> ProcessingStartResponse:
        """
        Validate session state and enqueue ticket generation job.
        Returns immediately with task_id for progress tracking.
        """
        pass
    
    # Status Retrieval (no background job needed)
    async def get_processing_status(self, session_id: UUID) -> ProcessingStatusResponse:
        """Get current processing status from database."""
        pass
    
    # Error Handling & Recovery
    async def retry_processing(self, session_id: UUID) -> ProcessingRetryResponse:
        """Clean up failed attempt and enqueue new job."""
        pass
    
    async def cancel_processing(self, session_id: UUID) -> ProcessingCancellationResponse:
        """Set cancellation flag for running job."""
        pass
    
    # LLM Health & Validation (no background job needed)
    async def validate_llm_service(self, session_id: UUID) -> LLMServiceHealthResponse:
        """Test LLM connectivity and return health status."""
        pass
    
    # Error Analysis (no background job needed)
    async def get_processing_errors(
        self, 
        session_id: UUID, 
        filters: Optional[dict] = None
    ) -> ProcessingErrorsResponse:
        """Retrieve processing errors with optional filtering."""
        pass

    # =========================================================================
    # INTERNAL METHODS (Called by ARQ worker jobs)
    # =========================================================================
    
    async def execute_ticket_generation(
        self,
        session_id: UUID,
        task_id: UUID,
        progress_callback: Callable[[float, str, dict], None]
    ) -> None:
        """
        Execute actual ticket generation. Called by ARQ worker.
        
        Args:
            session_id: Session to process
            task_id: Task ID for validation and progress tracking
            progress_callback: Function to publish progress updates
                              Signature: (percentage, stage_description, details_dict)
        """
        pass
```

## Key Decisions Made

### 1. ARQ Pool Dependency
- **Decision**: Add `arq_pool: ArqRedis` as optional constructor dependency
- **Optional in workers**: Jobs create their own service instances without arq_pool
- **Required in endpoints**: API endpoints need arq_pool to enqueue jobs
- **Rationale**: Clean separation between enqueueing (API) and executing (worker)

### 2. Split Public/Internal Methods
- **Decision**: Separate enqueueing logic from execution logic
- **Public methods**: Called by API endpoints, validate and enqueue jobs
- **Internal methods**: Called by ARQ workers, execute actual work
- **Rationale**: Clear responsibility separation, testable components

### 3. Progress Callback Pattern
- **Decision**: Pass progress callback function to internal execute methods
- **Callback signature**: `(percentage: float, stage: str, details: dict) -> None`
- **Worker provides callback**: That publishes to Redis pub/sub
- **Rationale**: Decouples progress reporting from execution logic

### 4. Internal Task Management
- **Decision**: Handle background task IDs internally via SessionTask model
- **Rationale**: Simple task_id storage/retrieval doesn't warrant additional component complexity

### 5. Internal Progress Tracking
- **Decision**: Handle progress updates via callback rather than separate service
- **Rationale**: Straightforward progress messages don't require separate component

### 6. Internal Entity Grouping
- **Decision**: Handle entity grouping logic (Content, Media, Views, etc.) within the service
- **Rationale**: Predefined categories with simple classification logic

### 7. Service-Level Retry Limit Enforcement
- **Decision**: Enforce retry limits (max 3 attempts) at service level
- **Rationale**: Business logic decision belongs in service layer

### 8. Service-Level Clean Slate Recovery
- **Decision**: Service orchestrates cleanup of partial tickets during retry
- **Rationale**: Part of retry business logic flow

### 9. LLM Output Validation
- **Decision**: Implement internal helper function `_validate_llm_response()` for LLM output validation
- **Rationale**: Validates required fields (user_story, verification sections) in clean, testable function

### 10. Initial Ticket Ordering
- **Decision**: Build initial dependency ordering into `execute_ticket_generation()` method
- **Rationale**: Straightforward ordering logic doesn't warrant separate method

## Implementation Patterns

### Public Method Pattern (API Endpoint)
```python
async def generate_tickets(self, session_id: UUID) -> ProcessingStartResponse:
    """Public method: Validates and enqueues job."""
    
    # 1. Validate session can start processing
    if not await self.session_repo.can_start_task(session_id, TaskType.PROCESSING):
        existing_task = await self.session_repo.get_active_task(session_id)
        if existing_task and existing_task.status == TaskStatus.RUNNING:
            # Return idempotency response
            return ProcessingAlreadyRunningResponse(
                task_id=existing_task.task_id,
                session_id=session_id,
                status="processing",
                # ... other fields from task state
            )
        raise ProcessingError("Cannot start processing", category="user_fixable")
    
    # 2. Validate LLM connectivity before committing
    health = await self.llm_service.validate_connectivity()
    if health["status"] != "healthy":
        raise ProcessingError(
            message=f"LLM service unavailable: {health['connectivity']}",
            category="temporary"
        )
    
    # 3. Get session details for response
    session = await self.session_repo.get_session_by_id(session_id)
    total_entities = await self.upload_repo.get_total_entity_count(session_id)
    
    # 4. Generate task ID and record in database
    task_id = uuid4()
    await self.session_repo.start_task(session_id, TaskType.PROCESSING, task_id)
    await self.session_repo.transition_stage(session_id, SessionStage.PROCESSING)
    await self.session_repo.commit()
    
    # 5. Enqueue the background job
    await self.arq_pool.enqueue_job(
        'generate_tickets_job',
        session_id=session_id,
        task_id=task_id
    )
    
    # 6. Return immediately with task tracking info
    return ProcessingStartResponse(
        task_id=task_id,
        session_id=session_id,
        status="processing",
        estimated_duration_minutes=self._estimate_duration(total_entities),
        total_files=await self.upload_repo.count_files(session_id),
        estimated_tickets=total_entities,
        llm_provider=session.llm_provider_choice
    )
```

### Internal Method Pattern (ARQ Worker)
```python
async def execute_ticket_generation(
    self,
    session_id: UUID,
    task_id: UUID,
    progress_callback: Callable[[float, str, dict], None]
) -> None:
    """Internal method: Executes actual ticket generation."""
    
    # 1. Verify task is still valid (not cancelled)
    task = await self.session_repo.get_active_task(session_id)
    if not task or task.task_id != task_id:
        return  # Task was cancelled or superseded
    
    # 2. Load validated CSV data
    files = await self.upload_repo.get_files_by_session(session_id)
    session = await self.session_repo.get_session_by_id(session_id)
    
    # 3. Group entities by type
    entity_groups = self._group_entities_by_type(files)
    total_groups = len(entity_groups)
    
    # 4. Process each entity group
    for group_index, (group_name, entities) in enumerate(entity_groups.items()):
        # Check for cancellation before each group
        if await self._is_cancelled(session_id, task_id):
            await self._handle_cancellation(session_id)
            return
        
        # Report progress
        percentage = (group_index / total_groups) * 100
        await progress_callback(
            percentage,
            f"Processing {group_name} entities ({group_index + 1} of {total_groups} groups)",
            {"entity_group": group_name, "entities_in_group": len(entities)}
        )
        
        # Generate tickets for this group
        for entity in entities:
            ticket_content = await self.llm_service.generate_ticket_content(
                entity_data=entity,
                context={
                    "entity_type": group_name,
                    "site_context": f"{session.site_name}: {session.site_description}"
                }
            )
            
            # Validate LLM output
            self._validate_llm_response(ticket_content)
            
            # Create ticket record
            await self.ticket_repo.create_ticket({
                "session_id": session_id,
                "title": ticket_content["title"],
                "description": self._format_description(ticket_content),
                "entity_group": group_name,
                "csv_source_files": entity.get("source_info", {}),
                # ... other fields
            })
        
        # Flush after each group
        await self.ticket_repo.flush()
    
    # 5. Build initial dependency ordering
    await self._build_dependency_ordering(session_id, entity_groups)
    
    # 6. Mark task complete
    await self.session_repo.complete_task(session_id)
    await self.session_repo.transition_stage(session_id, SessionStage.REVIEW)
    await self.session_repo.commit()
```

### ARQ Worker Job Function
```python
# /backend/app/workers/processing_worker.py
from arq import Retry
from uuid import UUID
import traceback

from app.services.processing_service import ProcessingService
from app.services.exceptions import ProcessingError
from app.workers.utils import publish_progress, publish_completion, publish_error, record_job_failure
from app.repositories.sqlalchemy.session_repository import SQLAlchemySessionRepository
from app.repositories.sqlalchemy.ticket_repository import SQLAlchemyTicketRepository
from app.repositories.sqlalchemy.upload_repository import SQLAlchemyUploadRepository
from app.repositories.sqlalchemy.error_repository import SQLAlchemyErrorRepository
from app.integrations.llm.service import LLMService
from app.core.config import settings

async def generate_tickets_job(ctx, session_id: UUID, task_id: UUID):
    """ARQ job function for ticket generation."""
    try:
        async with ctx['async_session']() as db_session:
            # Build repositories
            session_repo = SQLAlchemySessionRepository(db_session)
            ticket_repo = SQLAlchemyTicketRepository(db_session)
            upload_repo = SQLAlchemyUploadRepository(db_session)
            error_repo = SQLAlchemyErrorRepository(db_session)
            
            # Build LLM service
            llm_service = LLMService()
            
            # Build processing service (no arq_pool needed inside job)
            processing_service = ProcessingService(
                session_repo=session_repo,
                ticket_repo=ticket_repo,
                upload_repo=upload_repo,
                error_repo=error_repo,
                llm_service=llm_service,
            )
            
            # Define progress callback that publishes to Redis
            async def progress_callback(percentage: float, stage: str, details: dict):
                await publish_progress(
                    ctx, session_id, task_id, "processing", 
                    percentage, stage, details
                )
            
            # Execute the work
            await processing_service.execute_ticket_generation(
                session_id=session_id,
                task_id=task_id,
                progress_callback=progress_callback
            )
            
            # Publish completion
            await publish_completion(ctx, session_id, task_id, "processing", {
                "status": "completed",
                "ready_for_review": True
            })
            
    except ProcessingError as e:
        if e.category == "temporary":
            # Let ARQ retry with exponential backoff
            raise Retry(defer=ctx['job_try'] * settings.ARQ_RETRY_DELAY)
        else:
            # Don't retry - record failure and notify
            await record_job_failure(ctx, session_id, task_id, e)
            await publish_error(ctx, session_id, task_id, "processing", e)
            # Don't re-raise - job completes (as failed business state)
            
    except Exception as e:
        # Unexpected error - treat as admin_required
        error = ProcessingError(
            message="Unexpected error during processing",
            category="admin_required",
            technical_details={"exception": str(e), "traceback": traceback.format_exc()}
        )
        await record_job_failure(ctx, session_id, task_id, error)
        await publish_error(ctx, session_id, task_id, "processing", error)
```

## Internal Helper Methods

### LLM Validation Helper
```python
def _validate_llm_response(self, response: dict) -> None:
    """Validates required fields in LLM response."""
    required_fields = ["title", "user_story", "analysis", "verification"]
    
    for field in required_fields:
        if field not in response or not response[field]:
            raise ProcessingError(
                message=f"LLM response missing required field: {field}",
                category="admin_required"  # LLM misconfiguration
            )
    
    # Validate title length
    if len(response["title"]) > 255:
        raise ProcessingError(
            message="LLM generated title exceeds maximum length",
            category="admin_required"
        )
```

### Entity Grouping Logic
```python
def _group_entities_by_type(self, files: List[UploadedFile]) -> Dict[str, List[dict]]:
    """Group entities by predefined entity groups."""
    # Standard group ordering
    GROUP_ORDER = [
        "Content",      # Bundles, Fields
        "Media",        # Image styles, responsive styles
        "Views",        # Views, view displays
        "Migration",    # Migrations, mappings
        "Workflow",     # Workflows, states, transitions
        "User Roles",   # User roles
        "Custom"        # Custom entities
    ]
    
    # Map CSV types to groups
    CSV_TYPE_TO_GROUP = {
        "bundles": "Content",
        "fields": "Content",
        "views": "Views",
        "view_displays": "Views",
        "image_styles": "Media",
        "user_roles": "User Roles",
        "workflows": "Workflow",
        "workflow_states": "Workflow",
        "migrations": "Migration",
        "custom": "Custom"
    }
    
    # ... grouping logic
```

### Cancellation Check
```python
async def _is_cancelled(self, session_id: UUID, task_id: UUID) -> bool:
    """Check if task has been cancelled."""
    task = await self.session_repo.get_active_task(session_id)
    return task is None or task.task_id != task_id or task.status == TaskStatus.CANCELLED
```

## Dependencies
- **SessionRepositoryInterface**: Session state and task ID management
- **TicketRepositoryInterface**: Ticket creation and cleanup operations
- **UploadRepositoryInterface**: Access to validated CSV data for processing
- **ErrorRepositoryInterface**: Error storage and retrieval for retry analysis
- **LLMService**: AI-powered ticket content generation
- **ArqRedis** (optional): Background job enqueueing (only needed in API context)

## Testing Patterns

### Unit Test (Mocked Dependencies)
```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

@pytest.fixture
def processing_service(mock_repos, mock_llm, mock_arq):
    return ProcessingService(
        session_repo=mock_repos['session'],
        ticket_repo=mock_repos['ticket'],
        upload_repo=mock_repos['upload'],
        error_repo=mock_repos['error'],
        llm_service=mock_llm,
        arq_pool=mock_arq
    )

@pytest.mark.asyncio
async def test_generate_tickets_enqueues_job(processing_service, mock_arq):
    session_id = uuid4()
    
    result = await processing_service.generate_tickets(session_id)
    
    mock_arq.enqueue_job.assert_called_once_with(
        'generate_tickets_job',
        session_id=session_id,
        task_id=result.task_id
    )
    assert result.status == "processing"
```

### Internal Method Test (No ARQ)
```python
@pytest.mark.asyncio
async def test_execute_ticket_generation(processing_service_no_arq):
    session_id = uuid4()
    task_id = uuid4()
    progress_calls = []
    
    async def mock_progress(pct, stage, details):
        progress_calls.append((pct, stage, details))
    
    await processing_service_no_arq.execute_ticket_generation(
        session_id, task_id, mock_progress
    )
    
    assert len(progress_calls) > 0
    assert progress_calls[-1][0] == 100.0  # Final progress
```
