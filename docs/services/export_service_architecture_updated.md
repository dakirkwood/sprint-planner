# ExportService Architecture Decisions

## UPDATED: December 25, 2025
- Added `arq_pool: ArqRedis` to constructor dependencies
- Split export into public method (enqueue) and internal method (execute)
- Added validation staleness check before export (Decision 8 from discrepancy resolution)
- Added ARQ job integration pattern
- Updated all method signatures for async
- Added progress callback pattern for Redis pub/sub

---

## Method Signatures

```python
from arq.connections import ArqRedis
from typing import Optional, Callable, List
from uuid import UUID

class ExportService:
    def __init__(self, 
                 session_repo: SessionRepositoryInterface,
                 ticket_repo: TicketRepositoryInterface,
                 error_repo: ErrorRepositoryInterface,
                 jira_service: JiraService,
                 arq_pool: ArqRedis = None):  # Optional - not needed inside worker jobs
        self.session_repo = session_repo
        self.ticket_repo = ticket_repo
        self.error_repo = error_repo
        self.jira_service = jira_service
        self.arq_pool = arq_pool

    # =========================================================================
    # PUBLIC METHODS (Called by API endpoints - enqueue background jobs)
    # =========================================================================
    
    # Core Export - Enqueues background job
    async def export_session(self, session_id: UUID) -> ExportStartResponse:
        """
        Validate session state (including ADF validation freshness) and enqueue export job.
        Returns immediately with task_id for progress tracking.
        """
        pass
    
    # Status Retrieval (no background job needed)
    async def get_export_status(self, session_id: UUID) -> ExportStatusResponse:
        """Get current export status from database."""
        pass
    
    # Recovery - Enqueues background job
    async def retry_export(self, session_id: UUID) -> ExportRetryResponse:
        """Resume export from failure point."""
        pass
    
    # ADF Testing - Enqueues background job (called from review stage)
    async def test_adf_conversion(
        self, 
        session_id: UUID, 
        ticket_ids: Optional[List[UUID]] = None
    ) -> AdfTestResponse:
        """Test ADF conversion for specified tickets (or all)."""
        pass
    
    # Results (no background job needed)
    async def get_export_results(self, session_id: UUID) -> ExportResultsResponse:
        """Get completed export results with Jira ticket references."""
        pass

    # =========================================================================
    # INTERNAL METHODS (Called by ARQ worker jobs)
    # =========================================================================
    
    async def execute_session_export(
        self,
        session_id: UUID,
        task_id: UUID,
        progress_callback: Callable[[float, str, dict], None]
    ) -> None:
        """
        Execute actual Jira export. Called by ARQ worker.
        
        Args:
            session_id: Session to export
            task_id: Task ID for validation and progress tracking
            progress_callback: Function to publish progress updates
                              Signature: (percentage, stage_description, details_dict)
        """
        pass
    
    async def execute_adf_test(
        self,
        session_id: UUID,
        task_id: UUID,
        ticket_ids: Optional[List[UUID]],
        progress_callback: Callable[[float, str, dict], None]
    ) -> dict:
        """
        Execute ADF conversion testing. Called by ARQ worker.
        Returns test results summary.
        """
        pass
```

## Key Decisions Made

### 1. ARQ Pool Dependency
- **Decision**: Add `arq_pool: ArqRedis` as optional constructor dependency
- **Optional in workers**: Jobs create service instances without arq_pool
- **Required in endpoints**: API endpoints need arq_pool to enqueue jobs
- **Rationale**: Clean separation between enqueueing (API) and executing (worker)

### 2. Split Public/Internal Methods
- **Decision**: Separate enqueueing logic from execution logic
- **Public methods**: Called by API endpoints, validate and enqueue jobs
- **Internal methods**: Called by ARQ workers, execute actual work
- **Rationale**: Clear responsibility separation, testable components

### 3. Validation Staleness Check (Decision 8)
- **Decision**: Check ADF validation freshness before starting export
- **Implementation**: Compare `last_invalidated_at > last_validated_at`
- **Behavior**: Return error requiring re-validation if stale
- **Rationale**: Prevents exporting tickets that were edited after validation

### 4. Internal Task Management
- **Decision**: Handle export task IDs internally, following pattern from ProcessingService
- **Rationale**: Simple task_id storage/retrieval for consistency across service layer

### 5. Service-Level Sequential Processing
- **Decision**: Service orchestrates sequential ticket creation (1.5s delays, dependency order)
- **JiraService handles**: Individual ticket API calls
- **Rationale**: Export orchestration and business rules belong in service layer

### 6. Service-Level Retry from Failure Point
- **Decision**: Service handles tracking failure point and resuming from correct ticket
- **Rationale**: Business logic coordination of "failed at ticket 45, resume from 46"

### 7. Built-in Dependency Creation
- **Decision**: Dependency creation built into main export flow as final step
- **Rationale**: Dependencies can only be created after all tickets exist

### 8. Service-Level Manual Fix Tracking
- **Decision**: Service handles tracking needed manual fixes (invalid assignees, etc.)
- **Rationale**: Business decision logic of "assignee invalid â†’ create unassigned â†’ track manual fix"

### 9. No Project Validation in ExportService
- **Decision**: Removed project validation from ExportService
- **Rationale**: Already handled in SessionService during session creation (fail-fast approach)

## Implementation Patterns

### Public Method Pattern (API Endpoint)
```python
async def export_session(self, session_id: UUID) -> ExportStartResponse:
    """Public method: Validates and enqueues export job."""
    
    # 1. Validate session can start export task
    if not await self.session_repo.can_start_task(session_id, TaskType.EXPORT):
        existing_task = await self.session_repo.get_active_task(session_id)
        if existing_task and existing_task.status == TaskStatus.RUNNING:
            # Return idempotency response
            return ExportAlreadyRunningResponse(
                task_id=existing_task.task_id,
                session_id=session_id,
                status="exporting",
                # ... other fields from current progress
            )
        raise ExportError("Cannot start export", category="user_fixable")
    
    # 2. CHECK VALIDATION FRESHNESS (Decision 8)
    validation = await self.session_repo.get_session_validation(session_id)
    if validation is None:
        raise ExportError(
            message="ADF validation required before export",
            category="user_fixable",
            recovery_actions=["Run ADF validation from the Review stage"]
        )
    
    if not validation.validation_passed:
        raise ExportError(
            message="ADF validation did not pass",
            category="user_fixable",
            recovery_actions=["Fix validation errors and re-run ADF validation"]
        )
    
    # Check for staleness: tickets edited after validation
    if (validation.last_invalidated_at and validation.last_validated_at and
        validation.last_invalidated_at > validation.last_validated_at):
        raise ExportError(
            message="Tickets were modified after validation. Re-validation required.",
            category="user_fixable",
            recovery_actions=[
                "Tickets have been edited since ADF validation passed",
                "Run ADF validation again from the Review stage",
                "Then retry export"
            ]
        )
    
    # 3. Verify export readiness
    if not await self.session_repo.is_export_ready(session_id):
        raise ExportError(
            message="Session is not ready for export",
            category="user_fixable",
            recovery_actions=["Ensure all tickets are marked ready for Jira"]
        )
    
    # 4. Get session and ticket counts for response
    session = await self.session_repo.get_session_by_id(session_id)
    tickets = await self.ticket_repo.get_export_ready_tickets(session_id)
    
    # 5. Generate task ID and record in database
    task_id = uuid4()
    await self.session_repo.start_task(session_id, TaskType.EXPORT, task_id)
    await self.session_repo.transition_stage(session_id, SessionStage.JIRA_EXPORT)
    await self.session_repo.commit()
    
    # 6. Enqueue the background job
    await self.arq_pool.enqueue_job(
        'export_session_job',
        session_id=session_id,
        task_id=task_id
    )
    
    # 7. Return immediately with task tracking info
    return ExportStartResponse(
        task_id=task_id,
        session_id=session_id,
        status="exporting",
        total_tickets=len(tickets),
        estimated_duration_minutes=self._estimate_duration(len(tickets)),
        jira_project_key=session.jira_project_key,
        started_at=datetime.utcnow()
    )
```

### Internal Method Pattern (ARQ Worker)
```python
async def execute_session_export(
    self,
    session_id: UUID,
    task_id: UUID,
    progress_callback: Callable[[float, str, dict], None]
) -> None:
    """Internal method: Executes actual Jira export."""
    
    # 1. Verify task is still valid
    task = await self.session_repo.get_active_task(session_id)
    if not task or task.task_id != task_id:
        return  # Task was cancelled or superseded
    
    # 2. Load tickets in dependency order
    tickets = await self.ticket_repo.get_tickets_in_dependency_order(session_id)
    total_tickets = len(tickets)
    
    # Track manual fixes needed
    manual_fixes = []
    
    # 3. Sequential ticket creation
    for index, ticket in enumerate(tickets):
        # Check for cancellation
        if await self._is_cancelled(session_id, task_id):
            await self._handle_cancellation(session_id, index)
            return
        
        # Report progress
        percentage = (index / total_tickets) * 100
        await progress_callback(
            percentage,
            f"Creating ticket {index + 1} of {total_tickets}: {ticket.title}",
            {"current_ticket_id": str(ticket.id), "ticket_title": ticket.title}
        )
        
        try:
            # Convert to ADF (fresh conversion)
            adf_content = await self.jira_service.convert_to_adf(ticket.description)
            
            # Upload attachment if present
            attachment_jira_id = None
            if ticket.attachment:
                attachment_jira_id = await self.jira_service.upload_attachment(
                    ticket.attachment.content,
                    ticket.attachment.filename
                )
                await self.ticket_repo.mark_attachment_uploaded(
                    ticket.attachment.id, 
                    attachment_jira_id
                )
            
            # Create Jira ticket with graceful fallbacks
            jira_result = await self._create_jira_ticket_with_fallbacks(
                ticket, adf_content, attachment_jira_id, manual_fixes
            )
            
            # Store Jira reference
            await self.ticket_repo.mark_ticket_exported(
                ticket.id, 
                jira_result["key"], 
                jira_result["url"]
            )
            
            # Commit after each successful ticket (can't rollback Jira)
            await self.session_repo.commit()
            
            # Rate limiting delay
            await asyncio.sleep(1.5)
            
        except JiraError as e:
            # Record failure point for retry
            await self.session_repo.fail_task(session_id, {
                "failed_at_ticket_order": index,
                "error": str(e)
            })
            await self.session_repo.commit()
            raise ExportError(
                message=f"Failed to create Jira ticket: {ticket.title}",
                category="temporary" if e.is_transient else "admin_required"
            )
    
    # 4. Create dependency links in Jira (after all tickets exist)
    await progress_callback(95.0, "Creating dependency links in Jira", {})
    dependencies_created = await self._create_jira_dependencies(session_id)
    
    # 5. Store manual fix guidance
    if manual_fixes:
        await self._store_manual_fixes(session_id, manual_fixes)
    
    # 6. Mark export complete
    await self.session_repo.complete_task(session_id)
    await self.session_repo.transition_stage(session_id, SessionStage.COMPLETED)
    await self.session_repo.commit()
```

### Graceful Fallback Pattern
```python
async def _create_jira_ticket_with_fallbacks(
    self,
    ticket: Ticket,
    adf_content: dict,
    attachment_id: Optional[str],
    manual_fixes: List[dict]
) -> dict:
    """Create Jira ticket with graceful field fallbacks."""
    
    # Start with full ticket data
    ticket_data = {
        "project": ticket.session.jira_project_key,
        "summary": ticket.title,
        "description": adf_content,
        "issuetype": "Task"
    }
    
    # Try to set assignee (fallback to unassigned)
    if ticket.assignee:
        try:
            await self.jira_service.validate_assignee(ticket.assignee)
            ticket_data["assignee"] = {"accountId": ticket.assignee}
        except JiraValidationError:
            manual_fixes.append({
                "ticket_id": ticket.id,
                "issue_type": "assignee_invalid",
                "original_value": ticket.assignee,
                "recommended_action": f"Manually assign ticket after creation"
            })
    
    # Try to set sprint (fallback to backlog)
    if ticket.sprint:
        try:
            sprint_id = await self.jira_service.get_sprint_id(ticket.sprint)
            ticket_data["sprint"] = sprint_id
        except JiraValidationError:
            manual_fixes.append({
                "ticket_id": ticket.id,
                "issue_type": "sprint_not_found",
                "original_value": ticket.sprint,
                "recommended_action": f"Manually add to sprint: {ticket.sprint}"
            })
    
    # Create ticket
    result = await self.jira_service.create_issue(ticket_data)
    
    return result
```

### ARQ Worker Job Function
```python
# /backend/app/workers/export_worker.py
from arq import Retry
from uuid import UUID
import traceback

from app.services.export_service import ExportService
from app.services.exceptions import ExportError
from app.workers.utils import publish_progress, publish_completion, publish_error, record_job_failure
from app.repositories.sqlalchemy.session_repository import SQLAlchemySessionRepository
from app.repositories.sqlalchemy.ticket_repository import SQLAlchemyTicketRepository
from app.repositories.sqlalchemy.error_repository import SQLAlchemyErrorRepository
from app.integrations.jira.client import JiraService
from app.core.config import settings

async def export_session_job(ctx, session_id: UUID, task_id: UUID):
    """ARQ job function for Jira export."""
    try:
        async with ctx['async_session']() as db_session:
            # Build repositories
            session_repo = SQLAlchemySessionRepository(db_session)
            ticket_repo = SQLAlchemyTicketRepository(db_session)
            error_repo = SQLAlchemyErrorRepository(db_session)
            
            # Build Jira service
            jira_service = JiraService()
            
            # Build export service (no arq_pool needed inside job)
            export_service = ExportService(
                session_repo=session_repo,
                ticket_repo=ticket_repo,
                error_repo=error_repo,
                jira_service=jira_service,
            )
            
            # Define progress callback
            async def progress_callback(percentage: float, stage: str, details: dict):
                await publish_progress(
                    ctx, session_id, task_id, "export",
                    percentage, stage, details
                )
            
            # Execute export
            await export_service.execute_session_export(
                session_id=session_id,
                task_id=task_id,
                progress_callback=progress_callback
            )
            
            # Get results for completion message
            results = await export_service.get_export_results(session_id)
            
            # Publish completion
            await publish_completion(ctx, session_id, task_id, "export", {
                "tickets_created": results.total_tickets_created,
                "dependencies_created": results.dependencies_created,
                "manual_fixes_needed": len(results.manual_fixes)
            })
            
    except ExportError as e:
        if e.category == "temporary":
            # Let ARQ retry
            raise Retry(defer=ctx['job_try'] * settings.ARQ_RETRY_DELAY)
        else:
            await record_job_failure(ctx, session_id, task_id, e)
            await publish_error(ctx, session_id, task_id, "export", e)
            
    except Exception as e:
        error = ExportError(
            message="Unexpected error during export",
            category="admin_required",
            technical_details={"exception": str(e), "traceback": traceback.format_exc()}
        )
        await record_job_failure(ctx, session_id, task_id, error)
        await publish_error(ctx, session_id, task_id, "export", error)
```

## Retry from Failure Point
```python
async def retry_export(self, session_id: UUID) -> ExportRetryResponse:
    """Resume export from failure point."""
    
    # 1. Get failed task info
    task = await self.session_repo.get_active_task(session_id)
    if not task or task.status != TaskStatus.FAILED:
        raise ExportError("No failed export to retry", category="user_fixable")
    
    # 2. Check retry limit
    if task.retry_count >= 3:
        raise ExportError(
            message="Maximum retry attempts (3) exceeded",
            category="admin_required",
            recovery_actions=["Contact administrator for manual intervention"]
        )
    
    # 3. Find already-exported tickets (don't recreate)
    exported_tickets = await self.ticket_repo.get_exported_tickets(session_id)
    failure_point = task.failure_context.get("failed_at_ticket_order", 0)
    
    # 4. Generate new task ID
    new_task_id = uuid4()
    await self.session_repo.start_task(session_id, TaskType.EXPORT, new_task_id)
    await self.session_repo.commit()
    
    # 5. Enqueue retry job with resume info
    await self.arq_pool.enqueue_job(
        'export_session_job',
        session_id=session_id,
        task_id=new_task_id,
        resume_from_order=failure_point
    )
    
    return ExportRetryResponse(
        task_id=new_task_id,
        session_id=session_id,
        status="exporting",
        retry_attempt=task.retry_count + 1,
        remaining_retries=3 - (task.retry_count + 1),
        resuming_from_ticket_order=failure_point,
        preserved_successful_tickets=len(exported_tickets)
    )
```

## Dependencies
- **SessionRepositoryInterface**: Session state and export task management
- **TicketRepositoryInterface**: Ticket ordering, Jira key storage, progress tracking
- **ErrorRepositoryInterface**: Manual fix tracking and export error storage
- **JiraService**: Individual ticket creation, ADF conversion, dependency linking
- **ArqRedis** (optional): Background job enqueueing (only needed in API context)

## Testing Patterns

### Unit Test (Mocked Dependencies)
```python
import pytest
from unittest.mock import AsyncMock
from uuid import uuid4
from datetime import datetime

@pytest.fixture
def mock_validation_passed():
    """Mock session validation that passed and is fresh."""
    validation = AsyncMock()
    validation.validation_passed = True
    validation.last_validated_at = datetime.utcnow()
    validation.last_invalidated_at = None
    return validation

@pytest.mark.asyncio
async def test_export_checks_validation_freshness(export_service, mock_session_repo):
    session_id = uuid4()
    
    # Set up stale validation (edited after validation)
    stale_validation = AsyncMock()
    stale_validation.validation_passed = True
    stale_validation.last_validated_at = datetime(2024, 1, 1, 10, 0, 0)
    stale_validation.last_invalidated_at = datetime(2024, 1, 1, 11, 0, 0)  # After validation
    mock_session_repo.get_session_validation.return_value = stale_validation
    
    with pytest.raises(ExportError) as exc_info:
        await export_service.export_session(session_id)
    
    assert "Re-validation required" in str(exc_info.value.message)
    assert exc_info.value.category == "user_fixable"
```

### Integration Test
```python
@pytest.mark.asyncio
async def test_export_creates_jira_tickets(export_service, mock_jira_service):
    session_id = uuid4()
    task_id = uuid4()
    
    progress_calls = []
    async def mock_progress(pct, stage, details):
        progress_calls.append((pct, stage))
    
    await export_service.execute_session_export(session_id, task_id, mock_progress)
    
    # Verify Jira service was called
    assert mock_jira_service.create_issue.called
    assert len(progress_calls) > 0
```
