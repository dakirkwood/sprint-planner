# Task Management Architecture Standardization - Drupal Ticket Generator

## Overview
Resolution of conflicting task management approaches across specifications to establish a consistent pattern for background task tracking and coordination.

## Conflicting Specifications Identified

### **Conflict 1: Task ID Storage Location**
- **Service architecture docs**: "Handle background task IDs internally rather than separate task service"
- **Session model spec**: Session model doesn't explicitly define task ID fields
- **Endpoint specs**: Reference task IDs in responses (`ProcessingStartResponse.task_id`)
- **SessionTask model**: Defines `task_id` field for tracking background tasks

### **Conflict 2: Task Management Scope**
- **Internal approach**: Task IDs handled purely in-memory by services
- **Database approach**: Task IDs stored in database for recovery and status tracking
- **Hybrid approach**: Task coordination via database, execution details in-memory

### **Conflict 3: Task Lifecycle Tracking**
- **SessionTask model**: Designed for comprehensive task lifecycle tracking
- **Service methods**: Suggest simpler internal task management
- **API responses**: Require persistent task IDs for progress polling

## Decision: Database-Driven Task Management via SessionTask Model

### **Rationale for Database Storage**
1. **Session recovery requirements**: Users must be able to resume sessions across browser sessions
2. **Progress polling fallback**: REST endpoints need persistent task IDs when WebSocket unavailable
3. **Failure investigation**: Administrators need task failure context for debugging
4. **Clean slate recovery**: Failed tasks must be cleanly detected and retried
5. **Audit requirements**: Task execution history needed for troubleshooting

### **Rejected Alternatives**
- **Pure in-memory**: Fails session recovery requirements
- **Session model task fields**: Clutters session model with task-specific concerns
- **Separate task service**: Over-engineering for single-user application

## Standardized Task Management Architecture

### **1. SessionTask Model as Single Source of Truth**
```python
# /backend/app/models/session.py
class SessionTask(Base):
    id: UUID (primary key)
    session_id: UUID (foreign key to sessions, unique constraint)
    task_type: TaskType  # 'processing', 'export', 'adf_validation'
    task_id: UUID       # Background worker task identifier
    status: TaskStatus  # 'running', 'completed', 'failed', 'cancelled'
    started_at: datetime
    completed_at: Optional[datetime]
    failed_at: Optional[datetime]
    retry_count: int = 0
    failure_context: Optional[dict]  # JSON field
```

**Key Decisions:**
- **One record per session**: Unique constraint on session_id
- **Record gets updated**: As workflow progresses through different task types
- **Persistent task IDs**: Enable progress tracking and recovery
- **Failure context**: Store detailed error information for debugging

### **2. Service Layer Task Coordination**
```python
# Service methods coordinate with SessionTask model
class ProcessingService:
    async def generate_tickets(self, session_id: UUID) -> ProcessingStartResponse:
        # 1. Generate new task_id
        task_id = uuid4()
        
        # 2. Store task info in database
        await self.session_repo.start_task(session_id, TaskType.PROCESSING, task_id)
        
        # 3. Start background worker with task_id
        background_worker.start_processing.delay(session_id, task_id)
        
        # 4. Return response with persistent task_id
        return ProcessingStartResponse(
            task_id=task_id,
            session_id=session_id,
            status="processing"
        )
```

### **3. Background Worker Integration**
```python
# Background workers check and update task status
@app.task
def start_processing(session_id: UUID, task_id: UUID):
    try:
        # Verify task is still valid (not cancelled)
        task = session_repo.get_active_task(session_id)
        if not task or task.task_id != task_id:
            return  # Task was cancelled or superseded
            
        # Do the actual processing work
        result = perform_ticket_generation(session_id)
        
        # Mark task as completed
        session_repo.complete_task(session_id)
        
    except Exception as e:
        # Mark task as failed with context
        session_repo.fail_task(session_id, {"error": str(e), "traceback": traceback.format_exc()})
```

### **4. Progress Tracking Integration**
```python
# WebSocket and REST endpoints use same task coordination
@router.get("/api/processing/status/{session_id}")
async def get_processing_status(session_id: UUID):
    task = await session_repo.get_active_task(session_id)
    
    if not task:
        return ProcessingNotStartedResponse(session_id=session_id)
    
    if task.status == TaskStatus.RUNNING:
        return ProcessingStatusResponse(
            session_id=session_id,
            task_id=task.task_id,
            status="processing",
            started_at=task.started_at
        )
    elif task.status == TaskStatus.COMPLETED:
        return ProcessingCompletedResponse(
            session_id=session_id,
            task_id=task.task_id,
            status="completed",
            completed_at=task.completed_at
        )
    # etc.
```

## Repository Interface Updates

### **SessionRepositoryInterface Task Management Methods**
```python
class SessionRepositoryInterface(ABC):
    # Task Operations (consistent across all services)
    @abstractmethod
    async def start_task(self, session_id: UUID, task_type: TaskType, task_id: UUID) -> None:
        """Start new task, updating or creating SessionTask record"""
        pass
    
    @abstractmethod
    async def complete_task(self, session_id: UUID) -> None:
        """Mark current task as completed with timestamp"""
        pass
    
    @abstractmethod
    async def fail_task(self, session_id: UUID, error_context: dict) -> None:
        """Mark current task as failed with error details"""
        pass
    
    @abstractmethod
    async def cancel_task(self, session_id: UUID) -> None:
        """Mark current task as cancelled"""
        pass
    
    @abstractmethod
    async def get_active_task(self, session_id: UUID) -> Optional[SessionTask]:
        """Get currently running task for session"""
        pass
    
    @abstractmethod
    async def can_start_task(self, session_id: UUID, task_type: TaskType) -> bool:
        """Check if new task can be started (no running tasks)"""
        pass
```

## Service Integration Pattern

### **All Services Follow Same Pattern**
```python
# ProcessingService
async def generate_tickets(self, session_id: UUID) -> ProcessingStartResponse:
    if not await self.session_repo.can_start_task(session_id, TaskType.PROCESSING):
        raise ProcessingError("Task already running", category="user_fixable")
    
    task_id = uuid4()
    await self.session_repo.start_task(session_id, TaskType.PROCESSING, task_id)
    # Start background work...
    return ProcessingStartResponse(task_id=task_id, ...)

# ExportService  
async def export_session(self, session_id: UUID) -> ExportStartResponse:
    if not await self.session_repo.can_start_task(session_id, TaskType.EXPORT):
        raise ExportError("Task already running", category="user_fixable")
    
    task_id = uuid4()
    await self.session_repo.start_task(session_id, TaskType.EXPORT, task_id)
    # Start background work...
    return ExportStartResponse(task_id=task_id, ...)

# ReviewService (for ADF validation)
async def validate_adf(self, session_id: UUID) -> AdfValidationStartResponse:
    if not await self.session_repo.can_start_task(session_id, TaskType.ADF_VALIDATION):
        raise ValidationError("Task already running", category="user_fixable")
    
    task_id = uuid4()
    await self.session_repo.start_task(session_id, TaskType.ADF_VALIDATION, task_id)
    # Start background work...
    return AdfValidationStartResponse(task_id=task_id, ...)
```

## Task State Management

### **Task Lifecycle States**
```python
class TaskStatus(str, Enum):
    RUNNING = "running"      # Task actively executing
    COMPLETED = "completed"  # Task finished successfully
    FAILED = "failed"        # Task failed with error context
    CANCELLED = "cancelled"  # Task stopped by user request
```

### **Task Transition Rules**
- **RUNNING** → **COMPLETED**: Normal successful completion
- **RUNNING** → **FAILED**: Error occurred during execution
- **RUNNING** → **CANCELLED**: User requested cancellation
- **FAILED** → **RUNNING**: Retry after failure (increment retry_count)
- **CANCELLED** → **RUNNING**: New task started after cancellation

### **Concurrency Control**
- **One task per session**: Unique constraint on session_id prevents multiple concurrent tasks
- **Task validation**: Background workers verify task_id matches before starting work
- **Cancellation handling**: Workers check for cancellation flags during execution

## Database Schema Impact

### **SessionTask Table Definition**
```sql
CREATE TABLE session_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    task_type VARCHAR(50) NOT NULL,
    task_id UUID NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'running',
    started_at TIMESTAMP NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP,
    failed_at TIMESTAMP, 
    retry_count INTEGER NOT NULL DEFAULT 0,
    failure_context JSONB,
    
    CONSTRAINT uq_session_tasks_session_id UNIQUE (session_id),
    CONSTRAINT ck_session_tasks_status CHECK (status IN ('running', 'completed', 'failed', 'cancelled'))
);

CREATE INDEX idx_session_tasks_task_id ON session_tasks(task_id);
CREATE INDEX idx_session_tasks_status ON session_tasks(status);
```

### **Session Model Cleanup**
Remove any task ID fields from main Session model:
```python
# Remove these fields if they exist in Session model:
# - export_task_id 
# - processing_task_id
# - task_id
# All task tracking goes through SessionTask relationship
```

## Benefits of Standardized Approach

### **1. Consistency**
- **Same pattern across all services**: Processing, Export, ADF validation
- **Predictable API responses**: All include task_id for progress tracking
- **Unified error handling**: Task failures handled consistently

### **2. Reliability**
- **Session recovery**: Task state survives application restarts
- **Progress tracking**: REST polling always has persistent task IDs
- **Clean failure detection**: Clear distinction between running/failed/cancelled states

### **3. Debuggability**
- **Failure context**: Detailed error information stored for investigation
- **Task history**: Audit trail of all task attempts and outcomes
- **Retry tracking**: Clear visibility into retry attempts and patterns

### **4. Simplicity**
- **Single source of truth**: SessionTask model handles all task coordination
- **No additional infrastructure**: Uses existing database and repository patterns
- **Clear ownership**: Each service owns its task lifecycle

## Migration Steps

### **1. Update Model Specifications**
- ✅ SessionTask model already correctly specified
- ❌ Remove any task ID fields from Session model if present
- ✅ Ensure foreign key relationships are properly defined

### **2. Update Repository Interfaces**
- ✅ Add task management methods to SessionRepositoryInterface
- ✅ Update SQLAlchemy implementation to use SessionTask model
- ✅ Remove any task ID handling from other repositories

### **3. Update Service Implementations**
- ✅ All services follow same task coordination pattern
- ✅ Background workers check task validity before starting
- ✅ Consistent error handling and retry logic

### **4. Update API Responses**
- ✅ All task-starting endpoints return task_id from SessionTask
- ✅ Progress endpoints query SessionTask for current status
- ✅ Consistent response schemas across all stages

## Success Criteria

- ✅ All background tasks tracked through SessionTask model
- ✅ Services use consistent task coordination patterns  
- ✅ Progress tracking works for both WebSocket and REST polling
- ✅ Session recovery preserves task state across restarts
- ✅ Task failures provide detailed context for debugging
- ✅ Concurrent task prevention works reliably
- ✅ Retry logic handles failure cases gracefully
- ✅ No task-related data stored in main Session model

This standardization provides a robust foundation for task management that supports all the application's requirements while maintaining consistency across all workflow stages.