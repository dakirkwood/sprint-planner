# Repository Patterns Implementation Decisions - Drupal Ticket Generator

## UPDATED: December 25, 2025
- Updated to async SQLAlchemy 2.0 patterns
- Changed all code examples to use `AsyncSession` and `async/await`
- Updated transaction management for async context
- Updated testing patterns for async mocking

---

## Overview
Comprehensive decisions made for implementing repository patterns in the database-driven Drupal Ticket Generator architecture using async SQLAlchemy 2.0.

## Core Repository Architecture Decisions

### 1. Repository Granularity
**Decision**: Use aggregate repositories for related models
- **SessionRepository**: Handles Session + SessionTask + SessionValidation
- **TicketRepository**: Handles Ticket + TicketDependency + Attachment operations
- **AuthRepository**: Handles JiraAuthToken + JiraProjectContext
- **ErrorRepository**: Handles SessionError + AuditLog
- **UploadRepository**: Handles UploadedFile (single model)
- **Rationale**: Groups related operations, reduces complexity, maintains business logic cohesion

### 2. Base Repository Pattern
**Decision**: Implement async base repository class with common operations
- **BaseRepositoryInterface[T]**: Generic interface for async CRUD operations
- **SQLAlchemyBaseRepository[T]**: Common async implementation with flush() pattern
- **Benefits**: Reduces redundancy, consistent patterns, bulk operations included

### 3. Transaction Management
**Decision**: Repositories accept existing async database sessions
- **Pattern**: `repository = SQLAlchemySessionRepository(async_session)`
- **Benefits**: Single transaction boundaries, coordinated commits/rollbacks, efficient connections
- **Service layer controls**: `commit()` and `rollback()` operations

### 4. Dependency Injection Strategy
**Decision**: Full DI for both repositories and services (following Symfony patterns)
- **Repository DI**: Familiar pattern from user's Symfony experience
- **Service DI**: Industry standard, improves testability
- **FastAPI integration**: Uses `Depends()` for automatic async injection

## Base Repository Implementation

### Core Async Operations (with flush() pattern)
```python
from typing import TypeVar, Generic, List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import DeclarativeBase

T = TypeVar('T', bound=DeclarativeBase)

class SQLAlchemyBaseRepository(Generic[T]):
    """Base repository with async CRUD operations."""
    
    def __init__(self, db_session: AsyncSession, model_class: type[T]):
        self.db_session = db_session
        self.model_class = model_class
    
    async def get_by_id(self, entity_id: UUID) -> Optional[T]:
        """Get entity by primary key."""
        result = await self.db_session.execute(
            select(self.model_class).where(self.model_class.id == entity_id)
        )
        return result.scalar_one_or_none()
    
    async def get_all(self) -> List[T]:
        """Get all entities."""
        result = await self.db_session.execute(select(self.model_class))
        return list(result.scalars().all())
    
    async def create(self, entity: T) -> T:
        """Create new entity with flush (not commit)."""
        self.db_session.add(entity)
        await self.db_session.flush()
        await self.db_session.refresh(entity)
        return entity
    
    async def create_batch(self, entities: List[T]) -> List[T]:
        """Create multiple entities with single flush."""
        self.db_session.add_all(entities)
        await self.db_session.flush()
        for entity in entities:
            await self.db_session.refresh(entity)
        return entities
    
    async def update(self, entity: T) -> T:
        """Update entity with flush."""
        await self.db_session.flush()
        await self.db_session.refresh(entity)
        return entity
    
    async def delete(self, entity: T) -> None:
        """Delete entity with flush."""
        await self.db_session.delete(entity)
        await self.db_session.flush()
    
    async def delete_by_id(self, entity_id: UUID) -> bool:
        """Delete entity by ID, return True if deleted."""
        result = await self.db_session.execute(
            delete(self.model_class).where(self.model_class.id == entity_id)
        )
        await self.db_session.flush()
        return result.rowcount > 0
    
    async def exists(self, entity_id: UUID) -> bool:
        """Check if entity exists."""
        result = await self.db_session.execute(
            select(self.model_class.id).where(self.model_class.id == entity_id)
        )
        return result.scalar_one_or_none() is not None
    
    async def count(self) -> int:
        """Count all entities."""
        from sqlalchemy import func
        result = await self.db_session.execute(
            select(func.count()).select_from(self.model_class)
        )
        return result.scalar_one()
    
    # Transaction control - delegated to service layer
    async def flush(self) -> None:
        """Flush pending changes to database."""
        await self.db_session.flush()
    
    async def commit(self) -> None:
        """Commit current transaction."""
        await self.db_session.commit()
    
    async def rollback(self) -> None:
        """Rollback current transaction."""
        await self.db_session.rollback()
```

### Generic Type Support
- **Type safety**: `BaseRepositoryInterface[T]` for model-specific operations
- **Inheritance**: Domain repositories extend base functionality
- **Consistent patterns**: Same async CRUD interface across all repositories

## Domain Repository Interfaces

### SessionRepositoryInterface
```python
from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID
from app.schemas.base import SessionStage, TaskType

class SessionRepositoryInterface(ABC):
    """Interface for session aggregate operations."""
    
    # Session CRUD
    @abstractmethod
    async def create_session(self, session_data: dict) -> Session:
        pass
    
    @abstractmethod
    async def get_session_by_id(self, session_id: UUID) -> Optional[Session]:
        pass
    
    @abstractmethod
    async def update_session(self, session_id: UUID, updates: dict) -> Session:
        pass
    
    @abstractmethod
    async def find_incomplete_sessions_by_user(self, jira_user_id: str) -> List[Session]:
        pass
    
    # Stage Transitions
    @abstractmethod
    async def transition_stage(self, session_id: UUID, new_stage: SessionStage) -> None:
        pass
    
    @abstractmethod
    async def can_transition_to_stage(self, session_id: UUID, target_stage: SessionStage) -> bool:
        pass
    
    # Session Task Operations (aggregate)
    @abstractmethod
    async def start_task(self, session_id: UUID, task_type: TaskType, task_id: UUID) -> None:
        pass
    
    @abstractmethod
    async def complete_task(self, session_id: UUID) -> None:
        pass
    
    @abstractmethod
    async def fail_task(self, session_id: UUID, error_context: dict) -> None:
        pass
    
    @abstractmethod
    async def get_active_task(self, session_id: UUID) -> Optional[SessionTask]:
        pass
    
    # Session Validation Operations (aggregate)
    @abstractmethod
    async def start_validation(self, session_id: UUID) -> None:
        pass
    
    @abstractmethod
    async def complete_validation(self, session_id: UUID, passed: bool, results: dict) -> None:
        pass
    
    @abstractmethod
    async def invalidate_validation(self, session_id: UUID) -> None:
        pass
    
    @abstractmethod
    async def is_export_ready(self, session_id: UUID) -> bool:
        pass
    
    # Cleanup
    @abstractmethod
    async def cleanup_expired_sessions(self, retention_days: int = 7) -> int:
        pass
    
    # Transaction Control
    @abstractmethod
    async def flush(self) -> None:
        pass
    
    @abstractmethod
    async def commit(self) -> None:
        pass
    
    @abstractmethod
    async def rollback(self) -> None:
        pass
```

### TicketRepositoryInterface
- **Review interface**: Entity group queries, summaries, dependencies
- **Bulk operations**: Assignment updates, status changes
- **Export operations**: Dependency ordering, Jira integration
- **Attachment handling**: Through ticket relationships (1:1)

### Supporting Repositories
- **UploadRepository**: File management, CSV processing
- **ErrorRepository**: Error tracking, audit logging, pattern detection
- **AuthRepository**: Token management, project context caching

## Query Optimization Strategy

### Eager vs Lazy Loading with Async
**Decision**: Explicit eager loading for predictable performance
- **Pattern**: `selectinload()` or `joinedload()` for known relationship needs
- **Benefits**: Single queries, predictable testing, better async performance
- **Usage**: Repository methods specify loading strategy explicitly

```python
from sqlalchemy.orm import selectinload, joinedload

async def get_session_with_files(self, session_id: UUID) -> Optional[Session]:
    """Get session with uploaded files eagerly loaded."""
    result = await self.db_session.execute(
        select(Session)
        .options(selectinload(Session.uploaded_files))
        .where(Session.id == session_id)
    )
    return result.scalar_one_or_none()

async def get_session_with_task(self, session_id: UUID) -> Optional[Session]:
    """Get session with task info eagerly loaded (1:1 relationship)."""
    result = await self.db_session.execute(
        select(Session)
        .options(joinedload(Session.session_task))
        .where(Session.id == session_id)
    )
    return result.unique().scalar_one_or_none()
```

### Error Handling Strategy
**Decision**: Convert SQLAlchemy exceptions to domain exceptions
- **Exception hierarchy**: RepositoryError base class with categorization
- **Error categories**: Automatic mapping to "who can fix it" system
- **Original error preservation**: Debugging information maintained

## Custom Exception Classes

### Exception Hierarchy
```python
from app.schemas.base import ErrorCategory

class RepositoryError(Exception):
    """Base repository exception with error categorization."""
    
    def __init__(self, message: str, category: ErrorCategory, original_error: Exception = None):
        self.message = message
        self.category = category
        self.original_error = original_error
        super().__init__(message)

class EntityNotFoundError(RepositoryError):
    """Entity not found - user_fixable (bad IDs from user input)."""
    
    def __init__(self, entity_type: str, entity_id: UUID):
        super().__init__(
            message=f"{entity_type} with ID {entity_id} not found",
            category=ErrorCategory.USER_FIXABLE
        )

class EntityValidationError(RepositoryError):
    """Constraint violation - user_fixable."""
    
    def __init__(self, message: str, original_error: Exception = None):
        super().__init__(
            message=message,
            category=ErrorCategory.USER_FIXABLE,
            original_error=original_error
        )

class DatabaseConnectionError(RepositoryError):
    """Infrastructure issue - admin_required."""
    
    def __init__(self, message: str, original_error: Exception = None):
        super().__init__(
            message=message,
            category=ErrorCategory.ADMIN_REQUIRED,
            original_error=original_error
        )

class TransactionError(RepositoryError):
    """Transaction failure - temporary (retry-able)."""
    
    def __init__(self, message: str, original_error: Exception = None):
        super().__init__(
            message=message,
            category=ErrorCategory.TEMPORARY,
            original_error=original_error
        )
```

### Integration Benefits
- **Automatic categorization**: Maps to existing error response system
- **Service layer simplicity**: Catch RepositoryError, get category automatically
- **Debugging support**: Preserves original SQLAlchemy exception details

## FastAPI Dependency Injection

### Async Repository Dependencies
```python
# /backend/app/api/dependencies/repositories.py
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db_session

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

### Async Service Dependencies
```python
# /backend/app/api/dependencies/services.py
from arq.connections import ArqRedis

async def get_session_service(
    session_repo: SessionRepositoryInterface = Depends(get_session_repository),
    auth_repo: AuthRepositoryInterface = Depends(get_auth_repository),
    jira_service: JiraService = Depends(get_jira_service)
) -> SessionService:
    return SessionService(session_repo, auth_repo, jira_service)

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
```

### Key Benefits
- **Request-scoped sessions**: Fresh async database session per API request
- **Automatic cleanup**: FastAPI handles session lifecycle
- **Transaction coordination**: Multiple repositories share same session
- **Testing support**: Easy mock injection for unit tests

## Async Testing Patterns

### Unit Tests with AsyncMock
```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

@pytest.fixture
def mock_session_repo():
    """Create mock session repository."""
    repo = AsyncMock(spec=SessionRepositoryInterface)
    repo.get_session_by_id.return_value = MagicMock(
        id=uuid4(),
        current_stage=SessionStage.UPLOAD
    )
    return repo

@pytest.mark.asyncio
async def test_session_creation(mock_session_repo):
    mock_auth_repo = AsyncMock(spec=AuthRepositoryInterface)
    mock_jira_service = AsyncMock(spec=JiraService)
    
    service = SessionService(mock_session_repo, mock_auth_repo, mock_jira_service)
    result = await service.create_session(request_data, "user123")
    
    mock_session_repo.create_session.assert_called_once()
    mock_session_repo.commit.assert_called_once()
```

### Integration Tests with Real Async Database
```python
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

@pytest.fixture
async def test_db_session():
    """Create test database session with transaction rollback."""
    engine = create_async_engine(TEST_DATABASE_URL)
    async_session_factory = async_sessionmaker(engine, class_=AsyncSession)
    
    async with async_session_factory() as session:
        async with session.begin():
            yield session
            await session.rollback()
    
    await engine.dispose()

@pytest.fixture
def session_repository(test_db_session):
    """Create real repository with test session."""
    return SQLAlchemySessionRepository(test_db_session)

@pytest.mark.asyncio
async def test_session_persistence(session_repository):
    # Create session
    session = await session_repository.create_session({
        "jira_user_id": "test_user",
        "site_name": "Test Site"
    })
    
    # Verify it can be retrieved
    retrieved = await session_repository.get_session_by_id(session.id)
    assert retrieved is not None
    assert retrieved.site_name == "Test Site"
```

## Implementation Priorities

### Phase 1: Core Repositories
- SessionRepository (complex aggregate)
- TicketRepository (review interface support)
- Base repository implementation and testing

### Phase 2: Supporting Repositories
- UploadRepository
- ErrorRepository
- AuthRepository

### Phase 3: Integration & Testing
- FastAPI dependency injection setup
- Unit test infrastructure with async mocked repositories
- Integration test infrastructure with real async database

## Success Criteria
- âœ… Clean separation between data access and business logic
- âœ… Full async support with SQLAlchemy 2.0 and asyncpg
- âœ… Consistent error handling with automatic categorization
- âœ… Testable architecture with async mock-friendly interfaces
- âœ… Performance optimization through explicit eager loading
- âœ… Transaction coordination across multiple repositories
- âœ… Industry-standard dependency injection patterns
- âœ… Familiar patterns for developers with Symfony/Drupal experience
