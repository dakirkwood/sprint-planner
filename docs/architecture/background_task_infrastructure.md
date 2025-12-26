# Background Task Infrastructure Specification - Drupal Ticket Generator

## Overview

This document specifies the background task infrastructure using ARQ (async Redis queue) for the Drupal Ticket Generator. It covers worker configuration, job patterns, progress communication via Redis pub/sub, and integration with the FastAPI application.

## Architecture Overview

### Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Task Queue | ARQ | Async-native job queue for Python |
| Message Broker | Redis | Job storage and pub/sub messaging |
| Worker Process | ARQ Worker | Executes background jobs |

### Redis Dual-Role Pattern

Redis serves two distinct purposes:

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚                         REDIS                                    â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚   Role 1: Task Queue        â”‚   Role 2: Pub/Sub                 â”‚
â”‚   (ARQ job storage)         â”‚   (Progress communication)        â”‚
â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
â”‚   â€¢ Job serialization       â”‚   â€¢ Real-time progress updates    â”‚
â”‚   â€¢ Result storage          â”‚   â€¢ Worker â†’ WebSocket bridge     â”‚
â”‚   â€¢ Retry state             â”‚   â€¢ Per-session channels          â”‚
â”‚   â€¢ Deferred execution      â”‚   â€¢ Fire-and-forget messaging     â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

### Data Flow

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”     enqueue      â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”     dequeue     â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚   FastAPI    â”‚ â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â–º â”‚    Redis    â”‚ â—„â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”‚ ARQ Worker â”‚
â”‚   Endpoint   â”‚                  â”‚    Queue    â”‚                 â”‚            â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜                  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜                 â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                                        â”‚                               â”‚
                                        â”‚ pub/sub                       â”‚ publish
                                        â–¼                               â”‚
                                  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”                       â”‚
                                  â”‚   Redis     â”‚ â—„â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                                  â”‚   Pub/Sub   â”‚
                                  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                                        â”‚
                                        â”‚ subscribe
                                        â–¼
                                  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
                                  â”‚  WebSocket  â”‚
                                  â”‚   Handler   â”‚
                                  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

## Worker Structure

### Single Worker Architecture

A single ARQ worker process handles all job types. Job functions are organized by domain in separate files but registered in a unified `WorkerSettings` class.

**Rationale:**
- 9-person team with single-user-at-a-time usage pattern
- ARQ routes jobs to correct functions regardless of worker count
- Simpler deployment and monitoring
- Sufficient capacity for expected workload

### Directory Structure

```
backend/app/
â”œâ”€â”€ core/
â”‚   â””â”€â”€ redis.py                 # Redis connection factory
â””â”€â”€ workers/
    â”œâ”€â”€ __init__.py
    â”œâ”€â”€ settings.py              # ARQ WorkerSettings
    â”œâ”€â”€ processing_worker.py     # generate_tickets_job
    â”œâ”€â”€ export_worker.py         # export_session_job
    â”œâ”€â”€ validation_worker.py     # validate_adf_job
    â””â”€â”€ cleanup_worker.py        # Scheduled cleanup jobs
```

## Configuration

### Environment Variables

```python
# /backend/app/core/config.py
class Settings(BaseSettings):
    # ... existing settings ...
    
    # Redis Configuration
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # ARQ Worker Configuration
    ARQ_MAX_JOBS: int = 2          # Conservative for single-user pattern
    ARQ_JOB_TIMEOUT: int = 1800    # 30 minutes (LLM processing can be slow)
    ARQ_KEEP_RESULT: int = 3600    # Keep job results for 1 hour
    ARQ_RETRY_DELAY: int = 30      # Base delay between retries (seconds)
```

### Redis Connection Factory

```python
# /backend/app/core/redis.py
from arq.connections import RedisSettings
from app.core.config import settings

def get_redis_settings() -> RedisSettings:
    """Parse REDIS_URL into ARQ RedisSettings."""
    from urllib.parse import urlparse
    
    parsed = urlparse(settings.REDIS_URL)
    
    return RedisSettings(
        host=parsed.hostname or 'localhost',
        port=parsed.port or 6379,
        database=int(parsed.path.lstrip('/') or 0),
        password=parsed.password,
    )
```

### Worker Settings

```python
# /backend/app/workers/settings.py
from arq import cron
from arq.connections import RedisSettings
from datetime import timezone, datetime
import aioredis

from app.core.config import settings
from app.core.redis import get_redis_settings
from app.core.database import create_async_engine, async_sessionmaker

from .processing_worker import generate_tickets_job
from .export_worker import export_session_job
from .validation_worker import validate_adf_job
from .cleanup_worker import (
    cleanup_expired_sessions,
    cleanup_audit_logs,
    cleanup_expired_tokens,
    worker_heartbeat,
)

async def on_startup(ctx):
    """Initialize shared resources for all jobs."""
    # Database engine and session factory
    engine = create_async_engine(settings.DATABASE_URL)
    ctx['async_session'] = async_sessionmaker(engine, expire_on_commit=False)
    ctx['db_engine'] = engine
    
    # Redis for pub/sub (separate from ARQ's internal connection)
    ctx['redis'] = await aioredis.from_url(settings.REDIS_URL)
    
    # Record worker startup for health monitoring
    await ctx['redis'].set('worker:last_startup', datetime.utcnow().isoformat())

async def on_shutdown(ctx):
    """Cleanup shared resources."""
    await ctx['redis'].close()
    await ctx['db_engine'].dispose()

class WorkerSettings:
    functions = [
        generate_tickets_job,
        export_session_job,
        validate_adf_job,
    ]
    
    cron_jobs = [
        cron(cleanup_expired_sessions, hour=8, minute=0, tz=timezone.utc),
        cron(cleanup_audit_logs, hour=8, minute=30, tz=timezone.utc),
        cron(cleanup_expired_tokens, hour=9, minute=0, tz=timezone.utc),
        cron(worker_heartbeat, minute={0, 15, 30, 45}),  # Every 15 minutes
    ]
    
    on_startup = on_startup
    on_shutdown = on_shutdown
    
    redis_settings = get_redis_settings()
    
    max_jobs = settings.ARQ_MAX_JOBS
    job_timeout = settings.ARQ_JOB_TIMEOUT
    keep_result = settings.ARQ_KEEP_RESULT
```

## Dependency Injection in Jobs

ARQ jobs run outside FastAPI's request lifecycle and don't have access to `Depends()`. Dependencies are provided via the worker context.

### Context Factory Pattern

```python
async def generate_tickets_job(ctx, session_id: UUID, task_id: UUID):
    async with ctx['async_session']() as db_session:
        # Build repositories
        session_repo = SQLAlchemySessionRepository(db_session)
        ticket_repo = SQLAlchemyTicketRepository(db_session)
        upload_repo = SQLAlchemyUploadRepository(db_session)
        error_repo = SQLAlchemyErrorRepository(db_session)
        
        # Build external services
        llm_service = LLMService()
        
        # Build processing service (without arq_pool - not needed inside job)
        processing_service = ProcessingService(
            session_repo=session_repo,
            ticket_repo=ticket_repo,
            upload_repo=upload_repo,
            error_repo=error_repo,
            llm_service=llm_service,
        )
        
        # Execute the work
        await processing_service.execute_ticket_generation(
            session_id=session_id,
            task_id=task_id,
            progress_callback=lambda p, s, d: publish_progress(ctx, session_id, task_id, p, s, d)
        )
```

## Service Layer Integration

### Service Method Separation

Services have two methods per background operation:
- **Public method**: Validates, enqueues job, returns immediately (called by endpoints)
- **Internal method**: Executes actual work (called by job functions)

```python
# /backend/app/services/processing_service.py
class ProcessingService:
    def __init__(self, 
                 session_repo: SessionRepositoryInterface,
                 ticket_repo: TicketRepositoryInterface,
                 upload_repo: UploadRepositoryInterface,
                 error_repo: ErrorRepositoryInterface,
                 llm_service: LLMService,
                 arq_pool: ArqRedis = None):  # Optional - not needed inside jobs
        self.session_repo = session_repo
        self.ticket_repo = ticket_repo
        self.upload_repo = upload_repo
        self.error_repo = error_repo
        self.llm_service = llm_service
        self.arq_pool = arq_pool
    
    async def generate_tickets(self, session_id: UUID) -> ProcessingStartResponse:
        """Public method: Validates and enqueues job."""
        # 1. Validate session can start processing
        if not await self.session_repo.can_start_task(session_id, TaskType.PROCESSING):
            raise ProcessingError("Task already running", category="user_fixable")
        
        # 2. Validate LLM connectivity
        health = await self.llm_service.validate_connectivity()
        if health["status"] != "healthy":
            raise ProcessingError("LLM service unavailable", category="temporary")
        
        # 3. Generate task ID and record in database
        task_id = uuid4()
        await self.session_repo.start_task(session_id, TaskType.PROCESSING, task_id)
        
        # 4. Enqueue the background job
        await self.arq_pool.enqueue_job(
            'generate_tickets_job',
            session_id=session_id,
            task_id=task_id
        )
        
        # 5. Return immediately
        return ProcessingStartResponse(
            task_id=task_id,
            session_id=session_id,
            status="processing",
            # ... other fields
        )
    
    async def execute_ticket_generation(
        self, 
        session_id: UUID, 
        task_id: UUID,
        progress_callback: Callable
    ) -> None:
        """Internal method: Executes actual ticket generation."""
        # ... actual LLM calls and ticket creation
```

### Updated Service Dependencies

```python
# /backend/app/api/dependencies/services.py
from arq.connections import ArqRedis

def get_processing_service(
    session_repo: SessionRepositoryInterface = Depends(get_session_repository),
    ticket_repo: TicketRepositoryInterface = Depends(get_ticket_repository),
    upload_repo: UploadRepositoryInterface = Depends(get_upload_repository),
    error_repo: ErrorRepositoryInterface = Depends(get_error_repository),
    llm_service: LLMService = Depends(get_llm_service),
    arq_pool: ArqRedis = Depends(get_arq_pool)
) -> ProcessingService:
    return ProcessingService(
        session_repo=session_repo,
        ticket_repo=ticket_repo,
        upload_repo=upload_repo,
        error_repo=error_repo,
        llm_service=llm_service,
        arq_pool=arq_pool
    )
```

### ARQ Pool Dependency

```python
# /backend/app/api/dependencies/external.py
from arq.connections import ArqRedis, create_pool
from app.core.redis import get_redis_settings
from typing import Optional

_arq_pool: Optional[ArqRedis] = None

async def get_arq_pool() -> ArqRedis:
    global _arq_pool
    if _arq_pool is None:
        _arq_pool = await create_pool(get_redis_settings())
    return _arq_pool

# Register shutdown handler in main.py
@app.on_event("shutdown")
async def shutdown_arq_pool():
    global _arq_pool
    if _arq_pool:
        await _arq_pool.close()
        _arq_pool = None
```

## Progress Communication (Pub/Sub)

### Channel Naming Convention

```
progress:{session_id}:{task_type}
```

Examples:
- `progress:550e8400-e29b-41d4-a716-446655440000:processing`
- `progress:550e8400-e29b-41d4-a716-446655440000:export`
- `progress:550e8400-e29b-41d4-a716-446655440000:adf_validation`

### Message Schema

```python
# /backend/app/schemas/progress.py
from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import datetime

class ProgressMessage(BaseModel):
    type: str  # "progress", "completed", "error"
    session_id: UUID
    task_id: UUID
    task_type: str  # "processing", "export", "adf_validation"
    timestamp: datetime
    
    # Progress fields (when type="progress")
    status: Optional[str] = None
    progress_percentage: Optional[float] = None
    current_stage: Optional[str] = None
    details: Optional[dict] = None
    
    # Completion fields (when type="completed")
    result_summary: Optional[dict] = None
    
    # Error fields (when type="error")
    error_category: Optional[str] = None
    user_message: Optional[str] = None
    recovery_actions: Optional[List[str]] = None
```

### Publishing Progress from Jobs

```python
# /backend/app/workers/utils.py
from app.schemas.progress import ProgressMessage
from datetime import datetime
from uuid import UUID

async def publish_progress(
    ctx: dict,
    session_id: UUID,
    task_id: UUID,
    task_type: str,
    percentage: float,
    stage: str,
    details: dict = None
):
    """Publish progress update to Redis pub/sub."""
    channel = f"progress:{session_id}:{task_type}"
    
    message = ProgressMessage(
        type="progress",
        session_id=session_id,
        task_id=task_id,
        task_type=task_type,
        timestamp=datetime.utcnow(),
        status="processing",
        progress_percentage=percentage,
        current_stage=stage,
        details=details,
    )
    
    await ctx['redis'].publish(channel, message.model_dump_json())

async def publish_completion(
    ctx: dict,
    session_id: UUID,
    task_id: UUID,
    task_type: str,
    result_summary: dict
):
    """Publish completion message to Redis pub/sub."""
    channel = f"progress:{session_id}:{task_type}"
    
    message = ProgressMessage(
        type="completed",
        session_id=session_id,
        task_id=task_id,
        task_type=task_type,
        timestamp=datetime.utcnow(),
        result_summary=result_summary,
    )
    
    await ctx['redis'].publish(channel, message.model_dump_json())

async def publish_error(
    ctx: dict,
    session_id: UUID,
    task_id: UUID,
    task_type: str,
    error  # ProcessingError type
):
    """Publish error message to Redis pub/sub."""
    channel = f"progress:{session_id}:{task_type}"
    
    message = ProgressMessage(
        type="error",
        session_id=session_id,
        task_id=task_id,
        task_type=task_type,
        timestamp=datetime.utcnow(),
        error_category=error.category,
        user_message=error.message,
        recovery_actions=error.recovery_actions,
    )
    
    await ctx['redis'].publish(channel, message.model_dump_json())
```

### WebSocket Subscription Handler

```python
# /backend/app/api/websockets/processing.py
from fastapi import WebSocket, WebSocketDisconnect, Depends
from uuid import UUID
import json

@router.websocket("/api/processing/progress/{session_id}")
async def processing_progress(
    websocket: WebSocket, 
    session_id: UUID,
    redis = Depends(get_redis)
):
    await websocket.accept()
    
    pubsub = redis.pubsub()
    channel = f"progress:{session_id}:processing"
    
    await pubsub.subscribe(channel)
    
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                await websocket.send_text(message["data"])
                
                # Check if terminal message
                data = json.loads(message["data"])
                if data["type"] in ("completed", "error"):
                    break
    except WebSocketDisconnect:
        pass
    finally:
        await pubsub.unsubscribe(channel)
        await websocket.close()
```

### Reconnection Handling

Redis pub/sub is ephemeral â€” messages are not persisted. If a WebSocket client disconnects and reconnects, it misses messages published during the gap.

**Resolution:** Clients use REST polling fallback to fetch current status on reconnect, then resume WebSocket subscription.

```python
# Client pseudocode
async def connect_with_recovery():
    # 1. Fetch current status via REST
    status = await fetch("/api/processing/status/{session_id}")
    
    # 2. If still processing, connect WebSocket
    if status.status == "processing":
        await connect_websocket(session_id)
```

## Error Handling and Retries

### Error Category Alignment

Only `temporary` errors trigger ARQ automatic retries. Other categories require human intervention.

| Category | ARQ Behavior | User Experience |
|----------|--------------|-----------------|
| `user_fixable` | No retry, job completes | Error displayed, user fixes data |
| `admin_required` | No retry, job completes | Error displayed, admin notified |
| `temporary` | ARQ retries with backoff | Transparent retry, user sees "processing" |

### Retry Coordination

- **ARQ retries**: Automatic, transparent to user (handles transient failures)
- **SessionTask.retry_count**: Tracks explicit user-initiated retries via "Retry" button

### Job Error Handling Pattern

```python
# /backend/app/workers/processing_worker.py
from arq import Retry
from uuid import UUID
import traceback

async def generate_tickets_job(ctx, session_id: UUID, task_id: UUID):
    try:
        async with ctx['async_session']() as db_session:
            # ... build services and execute
            await processing_service.execute_ticket_generation(
                session_id, 
                task_id,
                progress_callback=lambda p, s, d: publish_progress(ctx, session_id, task_id, "processing", p, s, d)
            )
            
            # Publish completion
            await publish_completion(ctx, session_id, task_id, "processing", {
                "tickets_generated": result.ticket_count,
                # ... other summary data
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

### Recording Job Failures

```python
# /backend/app/workers/utils.py
from uuid import UUID

async def record_job_failure(ctx, session_id: UUID, task_id: UUID, error):
    """Record job failure in database."""
    async with ctx['async_session']() as db_session:
        session_repo = SQLAlchemySessionRepository(db_session)
        error_repo = SQLAlchemyErrorRepository(db_session)
        
        # Update SessionTask
        await session_repo.fail_task(session_id, {
            "error_category": error.category,
            "error_message": error.message,
            "technical_details": error.technical_details,
        })
        
        # Create SessionError record
        await error_repo.create_error({
            "session_id": session_id,
            "error_category": error.category,
            "severity": "blocking",
            "operation_stage": "processing",
            "user_message": error.message,
            "recovery_actions": error.recovery_actions,
            "technical_details": error.technical_details,
        })
        
        await db_session.commit()
```

### ARQ Retry Configuration

```python
class WorkerSettings:
    max_tries = 4  # 1 initial + 3 retries (matches "Maximum 3 retries" in docs)
    retry_jobs = True
```

## Scheduled Tasks (Cron Jobs)

### Cleanup Jobs

```python
# /backend/app/workers/cleanup_worker.py
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

async def cleanup_expired_sessions(ctx):
    """Remove sessions older than 7 days that aren't completed."""
    async with ctx['async_session']() as db_session:
        session_repo = SQLAlchemySessionRepository(db_session)
        
        deleted_count = await session_repo.cleanup_expired_sessions(retention_days=7)
        
        await db_session.commit()
        
        logger.info(f"Cleanup: Deleted {deleted_count} expired sessions")
        
        return {"deleted_sessions": deleted_count}

async def cleanup_audit_logs(ctx):
    """Remove audit logs older than 90 days."""
    async with ctx['async_session']() as db_session:
        error_repo = SQLAlchemyErrorRepository(db_session)
        
        deleted_count = await error_repo.cleanup_audit_logs(retention_days=90)
        
        await db_session.commit()
        
        logger.info(f"Cleanup: Deleted {deleted_count} audit log entries")
        
        return {"deleted_audit_logs": deleted_count}

async def cleanup_expired_tokens(ctx):
    """Remove tokens that have been expired beyond grace period."""
    async with ctx['async_session']() as db_session:
        auth_repo = SQLAlchemyAuthRepository(db_session)
        
        deleted_count = await auth_repo.cleanup_expired_tokens(grace_period_days=30)
        
        await db_session.commit()
        
        logger.info(f"Cleanup: Deleted {deleted_count} expired tokens")
        
        return {"deleted_tokens": deleted_count}
```

### Health Monitoring

```python
# /backend/app/workers/cleanup_worker.py
async def worker_heartbeat(ctx):
    """Periodic heartbeat for health monitoring."""
    await ctx['redis'].set('worker:last_heartbeat', datetime.utcnow().isoformat())
    await ctx['redis'].expire('worker:last_heartbeat', 120)  # Expires if worker dies
```

### Schedule Configuration

All scheduled jobs use UTC timezone for consistency across deployment environments.

| Job | Schedule (UTC) | Purpose |
|-----|----------------|---------|
| `cleanup_expired_sessions` | 08:00 | Remove 7-day-old incomplete sessions |
| `cleanup_audit_logs` | 08:30 | Remove 90-day-old audit entries |
| `cleanup_expired_tokens` | 09:00 | Remove expired OAuth tokens |
| `worker_heartbeat` | Every 15 min | Health monitoring |

## Deployment

### Development

```bash
# Terminal 1: Redis
redis-server

# Terminal 2: FastAPI
uvicorn app.main:app --reload

# Terminal 3: ARQ Worker
arq app.workers.settings.WorkerSettings
```

### Production (Docker Compose)

```yaml
# docker-compose.yml
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  api:
    build: ./backend
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      redis:
        condition: service_healthy
      db:
        condition: service_healthy

  worker:
    build: ./backend
    command: arq app.workers.settings.WorkerSettings
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      redis:
        condition: service_healthy
      db:
        condition: service_healthy

volumes:
  redis_data:
```

### Health Check Endpoint

```python
# /backend/app/api/v1/health.py
from fastapi import APIRouter, Depends

router = APIRouter()

@router.get("/health")
async def health_check(redis = Depends(get_redis)):
    worker_heartbeat = await redis.get('worker:last_heartbeat')
    
    return {
        "api": "healthy",
        "worker": "healthy" if worker_heartbeat else "unhealthy",
        "worker_last_seen": worker_heartbeat.decode() if worker_heartbeat else None,
    }
```

## Testing Patterns

### Layer 1: Service Unit Tests (Mocked ARQ)

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

@pytest.fixture
def mock_arq_pool():
    pool = AsyncMock()
    pool.enqueue_job = AsyncMock(return_value=MagicMock(job_id="test-job-id"))
    return pool

async def test_generate_tickets_enqueues_job(processing_service, mock_arq_pool):
    session_id = uuid4()
    
    result = await processing_service.generate_tickets(session_id)
    
    mock_arq_pool.enqueue_job.assert_called_once()
    assert result.status == "processing"
```

### Layer 2: Job Function Unit Tests (Mocked Context)

```python
import pytest
from unittest.mock import MagicMock, AsyncMock
from uuid import uuid4

@pytest.fixture
def mock_worker_context(test_db_session):
    return {
        'async_session': MagicMock(return_value=test_db_session),
        'redis': AsyncMock(),
    }

async def test_job_publishes_progress(mock_worker_context):
    session_id = uuid4()
    task_id = uuid4()
    
    await generate_tickets_job(mock_worker_context, session_id, task_id)
    
    # Verify progress was published
    assert mock_worker_context['redis'].publish.called
```

### Layer 3: Integration Tests

Use `fakeredis` for CI (fast, no Docker) and real Redis for local integration tests.

```python
import pytest

@pytest.fixture
async def fake_redis():
    import fakeredis.aioredis
    redis = fakeredis.aioredis.FakeRedis()
    yield redis
    await redis.close()
```

## Summary

### Key Decisions

| Decision | Choice |
|----------|--------|
| Task queue library | ARQ (async-native) |
| Message broker | Redis (dual-role: queue + pub/sub) |
| Worker architecture | Single worker, multiple job functions |
| Dependency injection | Factory in context (async_sessionmaker) |
| Job enqueueing location | Service layer |
| Progress throttling | None (export has built-in 1.5s delay) |
| Retry strategy | ARQ for automatic; SessionTask for user-initiated |
| Scheduled task timezone | UTC |
| Redis persistence | Default RDB snapshots |

### Service Signature Updates Required

| Service | Changes |
|---------|---------|
| `ProcessingService` | Add `arq_pool: ArqRedis` dependency; add `execute_ticket_generation()` method |
| `ExportService` | Add `arq_pool: ArqRedis` dependency; add `execute_session_export()` method |
| `ReviewService` | Add `arq_pool: ArqRedis` dependency; add `execute_adf_validation()` method |

## Document History

| Date | Author | Changes |
|------|--------|---------|
| December 25, 2025 | dK | Initial specification |
