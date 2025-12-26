# FastAPI Dependency Injection Setup and Request Lifecycle Management - Implementation Decisions

## UPDATED: December 25, 2025
- Changed to async SQLAlchemy 2.0 with `create_async_engine()`
- Updated from `Session` to `AsyncSession`
- Changed database driver from `psycopg2` to `asyncpg`
- Updated all code examples to use `async with` patterns
- Added ARQ pool dependency for background task integration

---

## Overview
Comprehensive decisions for implementing dependency injection patterns, database session management, and request lifecycle in the database-driven Drupal Ticket Generator architecture.

## 1. Database Session Management

### Async Session Configuration
```python
# /backend/app/core/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from app.core.config import settings

# Create async engine
# Note: asyncpg doesn't support connection pooling with NullPool in same way
# Using default pool settings optimized for async
engine = create_async_engine(
    settings.DATABASE_URL,  # postgresql+asyncpg://user:pass@host/db
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # Validates connections before use
    echo=settings.APP_DEBUG_MODE  # SQL logging in debug mode
)

# Create async session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Prevent lazy loading issues after commit
    autocommit=False,
    autoflush=False
)

async def get_db_session() -> AsyncSession:
    """Dependency that provides a database session per request."""
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()
```

### Key Decisions Made
- **Async SQLAlchemy 2.0**: Full async support with `asyncpg` driver
- **expire_on_commit=False**: Prevents issues accessing attributes after commit in async context
- **autocommit=False, autoflush=False**: Explicit service layer control over transactions and flushes
- **Connection pooling**: pool_size=10, max_overflow=20 suitable for 9-person team
- **Automatic cleanup**: `async with` ensures session cleanup even on exceptions
- **pool_pre_ping=True**: Prevents stale connection errors
- **Request-scoped sessions**: Fresh database session per API request

### Session Lifecycle Pattern
1. Request starts â†’ New async session created via `get_db_session()`
2. Repositories use `await session.flush()` for immediate DB sync when needed
3. Services call `await session.commit()` when business transaction completes
4. Request ends â†’ `session.close()` called automatically (rollback if no commit)

### Database URL Format
```python
# .env
# Note: Use asyncpg driver for async support
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/drupal_ticket_gen
```

## 2. Repository Dependency Injection Pattern

### Repository Constructor Pattern
```python
class SQLAlchemySessionRepository(SessionRepositoryInterface):
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
```

### Dependency Functions
```python
# /backend/app/api/dependencies/repositories.py
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db_session
from app.repositories.interfaces.session_repository import SessionRepositoryInterface
from app.repositories.sqlalchemy.session_repository import SQLAlchemySessionRepository

async def get_session_repository(
    db: AsyncSession = Depends(get_db_session)
) -> SessionRepositoryInterface:
    return SQLAlchemySessionRepository(db)

async def get_ticket_repository(
    db: AsyncSession = Depends(get_db_session)
) -> TicketRepositoryInterface:
    return SQLAlchemyTicketRepository(db)

async def get_upload_repository(
    db: AsyncSession = Depends(get_db_session)
) -> UploadRepositoryInterface:
    return SQLAlchemyUploadRepository(db)

async def get_auth_repository(
    db: AsyncSession = Depends(get_db_session)
) -> AuthRepositoryInterface:
    return SQLAlchemyAuthRepository(db)

async def get_error_repository(
    db: AsyncSession = Depends(get_db_session)
) -> ErrorRepositoryInterface:
    return SQLAlchemyErrorRepository(db)
```

### Key Decisions Made
- **Async dependency functions**: All repository dependencies are async
- **New instances per injection**: Repositories tied to request-scoped database sessions
- **Return interface types**: Better testability via `SessionRepositoryInterface` vs concrete classes
- **Individual dependency functions**: Clear and maintainable over generic factory patterns
- **Separate file organization**: Repository dependencies in dedicated file for development clarity
- **Standard FastAPI patterns**: Automatic support for testing overrides

### Repository Lifecycle
- Each repository instance wraps a specific async database session
- FastAPI dependency caching provides request-scoped singleton behavior
- Multiple repositories share same session for coordinated transactions

## 3. Service Layer Dependency Injection

### Service Constructor Pattern
```python
class SessionService:
    def __init__(self, 
                 session_repo: SessionRepositoryInterface, 
                 auth_repo: AuthRepositoryInterface,
                 jira_service: JiraService):
        self.session_repo = session_repo
        self.auth_repo = auth_repo
        self.jira_service = jira_service
```

### Service Dependency Functions
```python
# /backend/app/api/dependencies/services.py
from arq.connections import ArqRedis

async def get_session_service(
    session_repo: SessionRepositoryInterface = Depends(get_session_repository),
    auth_repo: AuthRepositoryInterface = Depends(get_auth_repository),
    jira_service: JiraService = Depends(get_jira_service)
) -> SessionService:
    return SessionService(session_repo, auth_repo, jira_service)

async def get_upload_service(
    upload_repo: UploadRepositoryInterface = Depends(get_upload_repository),
    session_repo: SessionRepositoryInterface = Depends(get_session_repository),
    error_repo: ErrorRepositoryInterface = Depends(get_error_repository),
    llm_service: LLMService = Depends(get_llm_service)
) -> UploadService:
    return UploadService(upload_repo, session_repo, error_repo, llm_service)

async def get_processing_service(
    session_repo: SessionRepositoryInterface = Depends(get_session_repository),
    ticket_repo: TicketRepositoryInterface = Depends(get_ticket_repository),
    upload_repo: UploadRepositoryInterface = Depends(get_upload_repository),
    error_repo: ErrorRepositoryInterface = Depends(get_error_repository),
    llm_service: LLMService = Depends(get_llm_service),
    arq_pool: ArqRedis = Depends(get_arq_pool)
) -> ProcessingService:
    return ProcessingService(
        session_repo, ticket_repo, upload_repo, error_repo, llm_service, arq_pool
    )

async def get_export_service(
    session_repo: SessionRepositoryInterface = Depends(get_session_repository),
    ticket_repo: TicketRepositoryInterface = Depends(get_ticket_repository),
    error_repo: ErrorRepositoryInterface = Depends(get_error_repository),
    jira_service: JiraService = Depends(get_jira_service),
    arq_pool: ArqRedis = Depends(get_arq_pool)
) -> ExportService:
    return ExportService(
        session_repo, ticket_repo, error_repo, jira_service, arq_pool
    )

async def get_review_service(
    ticket_repo: TicketRepositoryInterface = Depends(get_ticket_repository),
    session_repo: SessionRepositoryInterface = Depends(get_session_repository),
    error_repo: ErrorRepositoryInterface = Depends(get_error_repository),
    jira_service: JiraService = Depends(get_jira_service),
    arq_pool: ArqRedis = Depends(get_arq_pool)
) -> ReviewService:
    return ReviewService(
        ticket_repo, session_repo, error_repo, jira_service, arq_pool
    )
```

### External Service Configuration
```python
# /backend/app/api/dependencies/external.py
from functools import lru_cache
from typing import Optional
from arq.connections import ArqRedis, create_pool
from app.core.redis import get_redis_settings

@lru_cache()
def get_jira_service() -> JiraService:
    return JiraService(
        base_url=settings.JIRA_INSTANCE_URL,
        client_id=settings.JIRA_OAUTH_CLIENT_ID,
        client_secret=settings.JIRA_OAUTH_CLIENT_SECRET
    )

@lru_cache()
def get_llm_service() -> LLMService:
    return LLMService(
        openai_api_key=settings.LLM_OPENAI_API_KEY,
        anthropic_api_key=settings.LLM_ANTHROPIC_API_KEY,
        default_provider=settings.LLM_DEFAULT_PROVIDER
    )

# ARQ pool for background task enqueueing
_arq_pool: Optional[ArqRedis] = None

async def get_arq_pool() -> ArqRedis:
    """Get or create ARQ connection pool for task enqueueing."""
    global _arq_pool
    if _arq_pool is None:
        _arq_pool = await create_pool(get_redis_settings())
    return _arq_pool

async def close_arq_pool():
    """Close ARQ pool on application shutdown."""
    global _arq_pool
    if _arq_pool:
        await _arq_pool.close()
        _arq_pool = None
```

### Key Decisions Made
- **Async service dependencies**: All service dependency functions are async
- **Request-scoped services**: Services coordinate request-scoped repositories
- **Direct cross-service injection**: SessionService can depend on JiraService directly
- **Application-level external services**: JiraService and LLMService are application singletons
- **@lru_cache() for singletons**: External services configured once at application startup
- **ARQ pool integration**: Background task enqueueing available via dependency injection

## 4. FastAPI Endpoint Integration

### Endpoint Dependency Pattern
```python
@router.post("/sessions", response_model=SessionResponse)
async def create_session(
    request: SessionCreateRequest,
    current_user: UserInfo = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service)
) -> SessionResponse:
    return await session_service.create_session(request, current_user.jira_user_id)
```

### Authentication Integration
```python
async def get_current_user(
    authorization: str = Header(...),
    auth_repo: AuthRepositoryInterface = Depends(get_auth_repository)
) -> UserInfo:
    token = extract_bearer_token(authorization)
    
    # Automatic token refresh within 5 minutes of expiry
    if await auth_repo.token_needs_refresh(token):
        token = await auth_repo.refresh_token(token)
    
    return await auth_repo.get_user_info(token)
```

### Error Handling Integration
```python
from fastapi import Request
from fastapi.responses import JSONResponse

@app.exception_handler(ServiceError)
async def service_error_handler(request: Request, exc: ServiceError):
    status_map = {
        'user_fixable': 422,
        'admin_required': 403, 
        'temporary': 503
    }
    return JSONResponse(
        status_code=status_map[exc.category],
        content=exc.to_dict()
    )
```

### Request Correlation
```python
from uuid import uuid4

@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
    correlation_id = str(uuid4())
    request.state.correlation_id = correlation_id
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
    return response
```

### Session Ownership Validation
```python
async def get_user_session(
    session_id: UUID,
    current_user: UserInfo = Depends(get_current_user),
    session_repo: SessionRepositoryInterface = Depends(get_session_repository)
) -> Session:
    session = await session_repo.get_by_id(session_id)
    if session is None:
        raise HTTPException(404, "Session not found")
    if session.jira_user_id != current_user.jira_user_id:
        raise HTTPException(403, "Access denied")
    return session
```

### Key Decisions Made
- **Automatic token refresh**: Handled transparently in `get_current_user` dependency
- **Automatic error conversion**: Service errors mapped to appropriate HTTP status codes
- **Request correlation IDs**: Middleware-based injection for audit trails
- **Session ownership validation**: Dependency-level security for reusable patterns

## 5. Transaction Boundaries and Commit Strategy

### Service-Level Transaction Control
```python
# Standard pattern (all-or-nothing)
async def create_session(self, request: SessionCreateRequest) -> SessionResponse:
    # Multiple repository operations
    session = await self.session_repo.create(session_data)  # flush() internally
    context = await self.auth_repo.cache_project_context(project_data)  # flush() internally
    
    # Single commit for entire business transaction
    await self.session_repo.commit()
    return session_response
```

### Long-Running Operations Strategy
```python
# Processing workflow - uses background task
async def generate_tickets(self, session_id: UUID) -> ProcessingStartResponse:
    # Validate and enqueue - quick operation
    task_id = uuid4()
    await self.session_repo.start_task(session_id, TaskType.PROCESSING, task_id)
    await self.session_repo.commit()
    
    # Enqueue background job (actual work happens in worker)
    await self.arq_pool.enqueue_job('generate_tickets_job', session_id, task_id)
    
    return ProcessingStartResponse(task_id=task_id, ...)
```

### Exception Pattern (Jira Export)
```python
# Jira export - partial success required (can't undo Jira ticket creation)
async def execute_session_export(self, session_id: UUID, task_id: UUID):
    tickets = await self.ticket_repo.get_tickets_in_dependency_order(session_id)
    
    for i, ticket in enumerate(tickets):
        try:
            jira_key = await self.jira_service.create_ticket(ticket)
            # Immediate commit - can't rollback external Jira creation
            await self.ticket_repo.mark_exported(ticket.id, jira_key)
            await self.ticket_repo.commit()
        except JiraError:
            # Store failure point for retry
            await self.session_repo.mark_export_failed_at(session_id, ticket_order=i)
            await self.session_repo.commit()
            raise
```

### Key Decisions Made
- **Service-level commits**: Services understand business transaction boundaries
- **Background tasks for long operations**: Processing and export use ARQ workers
- **All-or-nothing standard**: Consistent pattern across most operations
- **Jira export exception**: Partial success only where external systems require it
- **Automatic rollback integration**: Clean slate recovery works seamlessly with transaction boundaries

## 6. Testing and Mock Configuration

### Unit Test Strategy (Fast, Mocked Dependencies)
```python
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def mock_session_repo():
    repo = AsyncMock(spec=SessionRepositoryInterface)
    repo.create.return_value = MagicMock(id=uuid4())
    return repo

async def test_session_creation_logic(mock_session_repo):
    # Mock repositories directly
    mock_auth_repo = AsyncMock(spec=AuthRepositoryInterface)
    mock_jira_service = AsyncMock(spec=JiraService)
    
    # Test service logic
    service = SessionService(mock_session_repo, mock_auth_repo, mock_jira_service)
    result = await service.create_session(request, "user123")
    
    # Verify repository calls
    mock_session_repo.create.assert_called_once()
```

### Integration Test Strategy (Real Database)
```python
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

@pytest.fixture
async def test_db_session():
    """Create a test database session with transaction rollback."""
    engine = create_async_engine(TEST_DATABASE_URL)
    async_session = async_sessionmaker(engine, class_=AsyncSession)
    
    async with async_session() as session:
        async with session.begin():
            yield session
            await session.rollback()  # All changes undone automatically
    
    await engine.dispose()

@pytest.fixture
async def integration_client(test_db_session):
    """Test client with real database session."""
    app.dependency_overrides[get_db_session] = lambda: test_db_session
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
    
    app.dependency_overrides.clear()
```

### API Test Strategy (Endpoint Integration)
```python
@pytest.fixture
async def client_with_mocks():
    # Override service with mock
    mock_session_service = AsyncMock(spec=SessionService)
    app.dependency_overrides[get_session_service] = lambda: mock_session_service
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client, mock_session_service
    
    app.dependency_overrides.clear()
```

### Authentication Testing
```python
@pytest.fixture
def mock_user():
    return UserInfo(jira_user_id="test_user", display_name="Test User", email="test@example.com")

async def test_with_auth(client, mock_user):
    app.dependency_overrides[get_current_user] = lambda: mock_user
    # Test business logic without OAuth complexity
```

### Key Decisions Made
- **AsyncMock for async code**: All mocks use `AsyncMock` for async method mocking
- **Both repository and service-level mocks**: Different test granularities for comprehensive coverage
- **Interface mocking for external services**: Simpler than HTTP-level mocking
- **Mock user objects**: Avoid OAuth complexity while testing business logic
- **Transaction rollback for database tests**: Faster and cleaner than database cleanup
- **FastAPI dependency overrides**: Clean test isolation with automatic cleanup

## 7. Environment-Specific Configuration

### Configuration Management
```python
# app/core/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database (async driver)
    DATABASE_URL: str  # postgresql+asyncpg://user:pass@host/db
    
    # Redis (for ARQ and pub/sub)
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # External Services
    JIRA_INSTANCE_URL: str = "https://ecitizen.atlassian.net"
    JIRA_OAUTH_CLIENT_ID: str
    JIRA_OAUTH_CLIENT_SECRET: str
    
    LLM_OPENAI_API_KEY: str
    LLM_ANTHROPIC_API_KEY: str
    LLM_DEFAULT_PROVIDER: str = "openai"
    
    # Environment
    APP_ENVIRONMENT: str = "development"
    APP_DEBUG_MODE: bool = False
    
    # ARQ Worker Configuration
    ARQ_MAX_JOBS: int = 2
    ARQ_JOB_TIMEOUT: int = 1800  # 30 minutes
    ARQ_KEEP_RESULT: int = 3600  # 1 hour

settings = Settings()
```

### Application Startup/Shutdown
```python
# /backend/app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.api.dependencies.external import close_arq_pool
from app.core.database import engine

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    yield
    # Shutdown
    await close_arq_pool()
    await engine.dispose()

app = FastAPI(lifespan=lifespan)
```

### Service Validation Timing Strategy
```python
# Startup validation (fail-fast for critical services)
def validate_startup_requirements():
    assert settings.DATABASE_URL, "Database URL required"
    assert settings.LLM_OPENAI_API_KEY, "OpenAI key required"
    assert settings.REDIS_URL, "Redis URL required"
    # Don't test connectivity - just config completeness

# Session creation (immediate user feedback)
async def create_session(self, request: SessionCreateRequest):
    # Validate Jira OAuth + project access immediately
    await self.jira_service.validate_project(request.jira_project_key)

# Just-in-time validation (when user actually needs service)
async def validate_llm_before_processing(session_id):
    session = await self.session_repo.get_session_by_id(session_id)
    provider = session.llm_provider_choice
    # Test actual connectivity to chosen provider
    await self.llm_service.validate_connectivity(provider)
```

### Key Decisions Made
- **Async database driver**: `asyncpg` for full async support
- **Redis for background tasks**: ARQ + Redis for task queue and pub/sub
- **Startup config validation**: Fail-fast for critical configuration, defer connectivity testing
- **Jira validation at session creation**: Immediate user feedback for project access
- **LLM validation just-in-time**: Test chosen provider when user starts processing
- **Lifespan context manager**: Modern FastAPI pattern for startup/shutdown

## Implementation Benefits

### Architectural Advantages
- **Clean separation of concerns**: Database â†’ Repository â†’ Service â†’ Endpoint layers
- **Full async support**: Non-blocking I/O throughout the stack
- **Testable architecture**: Easy mocking at any dependency level
- **Predictable transaction behavior**: Clear commit/rollback patterns
- **Request lifecycle management**: Automatic session cleanup and correlation tracking

### Development Efficiency
- **Familiar patterns**: Standard FastAPI dependency injection throughout
- **Environment consistency**: Same patterns across development and production
- **Error handling integration**: Automatic conversion to appropriate HTTP responses
- **Testing flexibility**: Multiple test strategies for different scenarios

### Operational Characteristics
- **Database connection efficiency**: Async connection pooling with appropriate sizing
- **Transaction safety**: Automatic rollback prevents partial state corruption
- **Audit trail support**: Request correlation IDs for debugging
- **Security enforcement**: Dependency-level session ownership validation
- **Background task support**: ARQ integration for long-running operations

## Success Criteria
- âœ… Async request-scoped database sessions with automatic cleanup
- âœ… Repository and service dependency injection with interface-based testing
- âœ… Automatic error categorization and HTTP status code mapping
- âœ… Transaction boundaries aligned with business operations
- âœ… Clean slate recovery through automatic rollback
- âœ… Multiple testing strategies with appropriate mock granularity
- âœ… Environment-specific configuration with validation timing
- âœ… External service integration with application singleton pattern
- âœ… ARQ background task integration via dependency injection
