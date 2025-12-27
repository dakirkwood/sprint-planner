# Phase 1: Foundation & Infrastructure

## Overview
Build the foundational layer including database models, repository interfaces and implementations, core configuration, and Redis/ARQ infrastructure. This phase establishes the base upon which all subsequent phases depend.

**Estimated Effort**: 2-3 days  
**Prerequisites**: None - this is the starting point  
**Deliverables**: Working database layer, repository pattern, infrastructure ready for background tasks

---

## Test-Driven Development Approach

### TDD Workflow for This Phase
1. Write model unit tests first (field definitions, relationships, enums)
2. Write migration integration tests (schema verification)
3. Write repository interface tests with mocks
4. Write repository integration tests with real database
5. Implement code to make tests pass
6. Verify coverage >80%

### Pytest Markers for Phase 1

All Phase 1 tests use the `@pytest.mark.phase1` marker combined with component markers:

| Component | Marker | Description |
|-----------|--------|-------------|
| Models | `@pytest.mark.models` | SQLAlchemy model field/relationship tests |
| Repositories | `@pytest.mark.repositories` | Repository CRUD and query tests |
| Infrastructure | `@pytest.mark.infrastructure` | Redis/ARQ connection tests |
| Migrations | `@pytest.mark.integration` | Database schema verification |

---

## Part 1: Test Infrastructure Setup

### 1.1 Test Directory Structure

Tests are organized by type (unit/integration) rather than by phase. Phase markers allow running phase-specific tests during development.

```
tests/
├── conftest.py                           # Shared fixtures
├── pytest.ini                            # Marker configuration
│
└── backend/
    ├── unit/
    │   ├── test_models/
    │   │   ├── test_session_models.py    # @pytest.mark.phase1, @pytest.mark.models
    │   │   ├── test_ticket_models.py     # @pytest.mark.phase1, @pytest.mark.models
    │   │   ├── test_upload_models.py     # @pytest.mark.phase1, @pytest.mark.models
    │   │   ├── test_auth_models.py       # @pytest.mark.phase1, @pytest.mark.models
    │   │   └── test_error_models.py      # @pytest.mark.phase1, @pytest.mark.models
    │   └── test_repositories/
    │       ├── test_session_repository.py    # @pytest.mark.phase1, @pytest.mark.repositories
    │       ├── test_ticket_repository.py     # @pytest.mark.phase1, @pytest.mark.repositories
    │       ├── test_upload_repository.py     # @pytest.mark.phase1, @pytest.mark.repositories
    │       ├── test_auth_repository.py       # @pytest.mark.phase1, @pytest.mark.repositories
    │       └── test_error_repository.py      # @pytest.mark.phase1, @pytest.mark.repositories
    │
    ├── integration/
    │   └── test_database/
    │       └── test_migrations.py        # @pytest.mark.phase1, @pytest.mark.integration
    │
    └── fixtures/
        └── factories/
            ├── __init__.py
            ├── session_factory.py
            ├── ticket_factory.py
            ├── upload_factory.py
            └── auth_factory.py
```

### 1.2 Core Test Fixtures (conftest.py)

```python
# tests/conftest.py
import pytest
import asyncio
from typing import AsyncGenerator
from uuid import uuid4
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.core.config import settings
from app.models.base import Base

# Test database URL (use separate test database)
TEST_DATABASE_URL = settings.DATABASE_URL.replace("/drupal_ticket_gen", "/drupal_ticket_gen_test")


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Drop all tables after tests
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session with transaction rollback."""
    async_session_factory = async_sessionmaker(
        test_engine, 
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with async_session_factory() as session:
        async with session.begin():
            yield session
            await session.rollback()


@pytest.fixture
def sample_session_data():
    """Sample data for creating a session."""
    return {
        "jira_user_id": "test-user-123",
        "site_name": "Test University",
        "site_description": "Test site for unit tests",
        "llm_provider_choice": "openai",
        "jira_project_key": "TEST"
    }


@pytest.fixture
def sample_ticket_data(sample_session_data):
    """Sample data for creating a ticket."""
    return {
        "title": "Configure Content Type: Article",
        "description": "## Issue\nConfigure the Article content type...",
        "entity_group": "Content",
        "user_order": 1,
        "csv_source_files": [{"filename": "bundles.csv", "rows": [1, 2]}]
    }
```

---

## Part 2: Model Tests (Write First)

### 2.1 Session Model Tests

```python
# tests/backend/unit/test_models/test_session_models.py
import pytest
from datetime import datetime
from uuid import uuid4
from sqlalchemy import inspect

from app.models.session import Session, SessionTask, SessionValidation
from app.schemas.base import SessionStage, SessionStatus, TaskType, TaskStatus, AdfValidationStatus


@pytest.mark.phase1
@pytest.mark.models
class TestSessionModel:
    """Test Session model field definitions and relationships."""
    
    def test_session_has_required_fields(self):
        """Session model must have all specified fields."""
        mapper = inspect(Session)
        columns = {c.key for c in mapper.columns}
        
        required_fields = {
            'id', 'jira_user_id', 'site_name', 'site_description',
            'llm_provider_choice', 'jira_project_key', 'current_stage',
            'status', 'created_at', 'updated_at'
        }
        assert required_fields.issubset(columns)
    
    def test_session_default_stage_is_upload(self, db_session, sample_session_data):
        """New sessions should default to UPLOAD stage."""
        session = Session(**sample_session_data)
        db_session.add(session)
        await db_session.flush()
        
        assert session.current_stage == SessionStage.UPLOAD
    
    def test_session_default_status_is_active(self, db_session, sample_session_data):
        """New sessions should default to ACTIVE status."""
        session = Session(**sample_session_data)
        db_session.add(session)
        await db_session.flush()
        
        assert session.status == SessionStatus.ACTIVE
    
    def test_session_generates_uuid_on_create(self, db_session, sample_session_data):
        """Session should auto-generate UUID primary key."""
        session = Session(**sample_session_data)
        db_session.add(session)
        await db_session.flush()
        
        assert session.id is not None
        assert isinstance(session.id, uuid4().__class__)
    
    def test_session_sets_timestamps_on_create(self, db_session, sample_session_data):
        """Session should set created_at and updated_at on creation."""
        session = Session(**sample_session_data)
        db_session.add(session)
        await db_session.flush()
        
        assert session.created_at is not None
        assert session.updated_at is not None
        assert isinstance(session.created_at, datetime)
    
    def test_session_has_relationship_to_session_task(self):
        """Session should have 1:1 relationship with SessionTask."""
        mapper = inspect(Session)
        relationships = {r.key for r in mapper.relationships}
        
        assert 'session_task' in relationships
    
    def test_session_has_relationship_to_session_validation(self):
        """Session should have 1:1 relationship with SessionValidation."""
        mapper = inspect(Session)
        relationships = {r.key for r in mapper.relationships}
        
        assert 'session_validation' in relationships
    
    def test_session_has_relationship_to_tickets(self):
        """Session should have 1:Many relationship with Tickets."""
        mapper = inspect(Session)
        relationships = {r.key for r in mapper.relationships}
        
        assert 'tickets' in relationships


@pytest.mark.phase1
@pytest.mark.models
class TestSessionTaskModel:
    """Test SessionTask model for background task tracking."""
    
    def test_session_task_has_required_fields(self):
        """SessionTask must have all specified fields."""
        mapper = inspect(SessionTask)
        columns = {c.key for c in mapper.columns}
        
        required_fields = {
            'session_id', 'task_id', 'task_type', 'status',
            'started_at', 'completed_at', 'retry_count', 'failure_context'
        }
        assert required_fields.issubset(columns)
    
    def test_session_task_uses_session_id_as_primary_key(self):
        """SessionTask should use session_id as primary key (1:1)."""
        mapper = inspect(SessionTask)
        pk_columns = [c.key for c in mapper.primary_key]
        
        assert pk_columns == ['session_id']
    
    def test_task_type_enum_values(self):
        """TaskType enum must have expected values."""
        expected = {'processing', 'export', 'adf_validation'}
        actual = {e.value for e in TaskType}
        
        assert expected == actual
    
    def test_task_status_enum_values(self):
        """TaskStatus enum must have expected values."""
        expected = {'running', 'completed', 'failed', 'cancelled'}
        actual = {e.value for e in TaskStatus}
        
        assert expected == actual


@pytest.mark.phase1
@pytest.mark.models
class TestSessionValidationModel:
    """Test SessionValidation model for ADF validation tracking."""
    
    def test_session_validation_has_required_fields(self):
        """SessionValidation must have all specified fields."""
        mapper = inspect(SessionValidation)
        columns = {c.key for c in mapper.columns}
        
        required_fields = {
            'session_id', 'validation_status', 'validation_passed',
            'last_validated_at', 'last_invalidated_at', 'validation_results'
        }
        assert required_fields.issubset(columns)
    
    def test_validation_passed_defaults_to_false(self, db_session):
        """validation_passed should default to False."""
        # Create session first
        session = Session(jira_user_id="test", site_name="Test", jira_project_key="TEST")
        db_session.add(session)
        await db_session.flush()
        
        validation = SessionValidation(session_id=session.id)
        db_session.add(validation)
        await db_session.flush()
        
        assert validation.validation_passed is False
    
    def test_adf_validation_status_enum_values(self):
        """AdfValidationStatus enum must have expected values."""
        expected = {'pending', 'processing', 'completed', 'failed'}
        actual = {e.value for e in AdfValidationStatus}
        
        assert expected == actual
```

### 2.2 Ticket Model Tests

```python
# tests/backend/unit/test_models/test_ticket_models.py
import pytest
from sqlalchemy import inspect

from app.models.ticket import Ticket, TicketDependency, Attachment
from app.models.session import Session
from app.schemas.base import JiraUploadStatus


@pytest.mark.phase1
@pytest.mark.models
class TestTicketModel:
    """Test Ticket model field definitions."""
    
    def test_ticket_has_required_fields(self):
        """Ticket must have all 14 specified fields."""
        mapper = inspect(Ticket)
        columns = {c.key for c in mapper.columns}
        
        required_fields = {
            'id', 'session_id', 'title', 'description', 'csv_source_files',
            'entity_group', 'user_order', 'ready_for_jira', 'sprint',
            'assignee', 'user_notes', 'jira_ticket_key', 'jira_ticket_url',
            'created_at', 'updated_at'
        }
        assert required_fields.issubset(columns)
    
    def test_ticket_does_not_have_attachment_id_fk(self):
        """Ticket should NOT have attachment_id FK (circular FK fix)."""
        mapper = inspect(Ticket)
        columns = {c.key for c in mapper.columns}
        
        assert 'attachment_id' not in columns
    
    def test_ticket_has_relationship_to_attachment(self):
        """Ticket should navigate to Attachment via relationship."""
        mapper = inspect(Ticket)
        relationships = {r.key for r in mapper.relationships}
        
        assert 'attachment' in relationships
    
    def test_ticket_has_dependency_relationships(self):
        """Ticket should have dependencies and depends_on relationships."""
        mapper = inspect(Ticket)
        relationships = {r.key for r in mapper.relationships}
        
        assert 'dependencies' in relationships
        assert 'depends_on' in relationships
    
    def test_ready_for_jira_defaults_to_false(self, db_session, sample_ticket_data):
        """ready_for_jira should default to False."""
        # Create session first
        session = Session(jira_user_id="test", site_name="Test", jira_project_key="TEST")
        db_session.add(session)
        await db_session.flush()
        
        ticket = Ticket(session_id=session.id, **sample_ticket_data)
        db_session.add(ticket)
        await db_session.flush()
        
        assert ticket.ready_for_jira is False


@pytest.mark.phase1
@pytest.mark.models
class TestTicketDependencyModel:
    """Test TicketDependency junction table."""
    
    def test_ticket_dependency_has_composite_primary_key(self):
        """TicketDependency uses composite PK of both ticket IDs."""
        mapper = inspect(TicketDependency)
        pk_columns = {c.key for c in mapper.primary_key}
        
        assert pk_columns == {'ticket_id', 'depends_on_ticket_id'}
    
    def test_ticket_dependency_has_both_relationships(self):
        """TicketDependency should reference both tickets."""
        mapper = inspect(TicketDependency)
        relationships = {r.key for r in mapper.relationships}
        
        assert 'dependent_ticket' in relationships
        assert 'dependency_ticket' in relationships


@pytest.mark.phase1
@pytest.mark.models
class TestAttachmentModel:
    """Test Attachment model."""
    
    def test_attachment_has_ticket_id_fk(self):
        """Attachment should have ticket_id FK (owns the relationship)."""
        mapper = inspect(Attachment)
        columns = {c.key for c in mapper.columns}
        
        assert 'ticket_id' in columns
    
    def test_attachment_ticket_id_is_unique(self):
        """ticket_id should be unique (enforces 1:1)."""
        mapper = inspect(Attachment)
        # Check for unique constraint on ticket_id
        table = Attachment.__table__
        ticket_id_col = table.c.ticket_id
        
        assert ticket_id_col.unique is True
    
    def test_jira_upload_status_enum_values(self):
        """JiraUploadStatus enum must have expected values."""
        expected = {'pending', 'uploaded', 'failed'}
        actual = {e.value for e in JiraUploadStatus}
        
        assert expected == actual
```

### 2.3 Migration Tests

```python
# tests/backend/integration/test_database/test_migrations.py
import pytest
from sqlalchemy import inspect, text


@pytest.mark.phase1
@pytest.mark.integration
class TestMigrations:
    """Test that migrations create expected database schema."""
    
    async def test_all_tables_created(self, test_engine):
        """Verify all expected tables exist after migrations."""
        expected_tables = {
            'sessions', 'session_tasks', 'session_validations',
            'uploaded_files', 'tickets', 'ticket_dependencies', 'attachments',
            'jira_auth_tokens', 'jira_project_context',
            'session_errors', 'audit_log'
        }
        
        async with test_engine.connect() as conn:
            def get_tables(connection):
                inspector = inspect(connection)
                return set(inspector.get_table_names())
            
            actual_tables = await conn.run_sync(get_tables)
        
        assert expected_tables.issubset(actual_tables)
    
    async def test_sessions_table_has_indexes(self, test_engine):
        """Verify sessions table has expected indexes."""
        async with test_engine.connect() as conn:
            def get_indexes(connection):
                inspector = inspect(connection)
                return inspector.get_indexes('sessions')
            
            indexes = await conn.run_sync(get_indexes)
        
        index_names = {idx['name'] for idx in indexes}
        assert 'idx_sessions_jira_user_id' in index_names
        assert 'idx_sessions_current_stage' in index_names
    
    async def test_tickets_table_has_indexes(self, test_engine):
        """Verify tickets table has expected indexes."""
        async with test_engine.connect() as conn:
            def get_indexes(connection):
                inspector = inspect(connection)
                return inspector.get_indexes('tickets')
            
            indexes = await conn.run_sync(get_indexes)
        
        index_names = {idx['name'] for idx in indexes}
        assert 'idx_tickets_session_id' in index_names
        assert 'idx_tickets_entity_group' in index_names
    
    async def test_foreign_key_cascades(self, test_engine):
        """Verify CASCADE delete is configured on FKs."""
        async with test_engine.connect() as conn:
            def get_fks(connection):
                inspector = inspect(connection)
                return inspector.get_foreign_keys('tickets')
            
            fks = await conn.run_sync(get_fks)
        
        session_fk = next(fk for fk in fks if fk['referred_table'] == 'sessions')
        assert session_fk['options'].get('ondelete') == 'CASCADE'
```

---

## Part 3: Repository Tests (Write First)

### 3.1 Session Repository Tests

```python
# tests/backend/unit/test_repositories/test_session_repository.py
import pytest
from uuid import uuid4
from datetime import datetime

from app.repositories.sqlalchemy.session_repository import SQLAlchemySessionRepository
from app.schemas.base import SessionStage, TaskType, TaskStatus


@pytest.mark.phase1
@pytest.mark.repositories
class TestSessionRepositoryCRUD:
    """Test basic CRUD operations."""
    
    @pytest.fixture
    def repo(self, db_session):
        return SQLAlchemySessionRepository(db_session)
    
    async def test_create_session(self, repo, sample_session_data):
        """Should create a session and return it with ID."""
        session = await repo.create_session(sample_session_data)
        
        assert session.id is not None
        assert session.site_name == sample_session_data['site_name']
        assert session.current_stage == SessionStage.UPLOAD
    
    async def test_get_session_by_id(self, repo, sample_session_data):
        """Should retrieve session by ID."""
        created = await repo.create_session(sample_session_data)
        
        retrieved = await repo.get_session_by_id(created.id)
        
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.site_name == created.site_name
    
    async def test_get_session_by_id_not_found(self, repo):
        """Should return None for non-existent session."""
        result = await repo.get_session_by_id(uuid4())
        
        assert result is None
    
    async def test_update_session(self, repo, sample_session_data):
        """Should update session fields."""
        session = await repo.create_session(sample_session_data)
        
        updated = await repo.update_session(session.id, {'site_name': 'Updated Name'})
        
        assert updated.site_name == 'Updated Name'
    
    async def test_find_incomplete_sessions_by_user(self, repo, sample_session_data):
        """Should find all non-completed sessions for a user."""
        # Create multiple sessions
        await repo.create_session(sample_session_data)
        await repo.create_session({**sample_session_data, 'site_name': 'Site 2'})
        
        sessions = await repo.find_incomplete_sessions_by_user(sample_session_data['jira_user_id'])
        
        assert len(sessions) == 2


@pytest.mark.phase1
@pytest.mark.repositories
class TestSessionRepositoryStageTransitions:
    """Test stage transition operations."""
    
    @pytest.fixture
    def repo(self, db_session):
        return SQLAlchemySessionRepository(db_session)
    
    async def test_transition_stage(self, repo, sample_session_data):
        """Should transition session to new stage."""
        session = await repo.create_session(sample_session_data)
        
        await repo.transition_stage(session.id, SessionStage.PROCESSING)
        
        updated = await repo.get_session_by_id(session.id)
        assert updated.current_stage == SessionStage.PROCESSING
    
    async def test_can_transition_to_valid_stage(self, repo, sample_session_data):
        """Should allow valid stage transitions."""
        session = await repo.create_session(sample_session_data)
        
        # UPLOAD -> PROCESSING is valid
        can_transition = await repo.can_transition_to_stage(session.id, SessionStage.PROCESSING)
        
        assert can_transition is True
    
    async def test_cannot_skip_stages(self, repo, sample_session_data):
        """Should not allow skipping stages."""
        session = await repo.create_session(sample_session_data)
        
        # UPLOAD -> JIRA_EXPORT is not valid (skips PROCESSING and REVIEW)
        can_transition = await repo.can_transition_to_stage(session.id, SessionStage.JIRA_EXPORT)
        
        assert can_transition is False


@pytest.mark.phase1
@pytest.mark.repositories
class TestSessionRepositoryTaskOperations:
    """Test SessionTask aggregate operations."""
    
    @pytest.fixture
    def repo(self, db_session):
        return SQLAlchemySessionRepository(db_session)
    
    async def test_start_task_creates_task_record(self, repo, sample_session_data):
        """Should create SessionTask when starting a task."""
        session = await repo.create_session(sample_session_data)
        task_id = uuid4()
        
        await repo.start_task(session.id, TaskType.PROCESSING, task_id)
        
        task = await repo.get_active_task(session.id)
        assert task is not None
        assert task.task_id == task_id
        assert task.task_type == TaskType.PROCESSING
        assert task.status == TaskStatus.RUNNING
    
    async def test_complete_task_updates_status(self, repo, sample_session_data):
        """Should mark task as completed."""
        session = await repo.create_session(sample_session_data)
        await repo.start_task(session.id, TaskType.PROCESSING, uuid4())
        
        await repo.complete_task(session.id)
        
        task = await repo.get_active_task(session.id)
        assert task.status == TaskStatus.COMPLETED
        assert task.completed_at is not None
    
    async def test_fail_task_stores_error_context(self, repo, sample_session_data):
        """Should store failure context when task fails."""
        session = await repo.create_session(sample_session_data)
        await repo.start_task(session.id, TaskType.PROCESSING, uuid4())
        
        error_context = {'error': 'LLM timeout', 'failed_at_entity': 15}
        await repo.fail_task(session.id, error_context)
        
        task = await repo.get_active_task(session.id)
        assert task.status == TaskStatus.FAILED
        assert task.failure_context == error_context


@pytest.mark.phase1
@pytest.mark.repositories
class TestSessionRepositoryValidationOperations:
    """Test SessionValidation aggregate operations."""
    
    @pytest.fixture
    def repo(self, db_session):
        return SQLAlchemySessionRepository(db_session)
    
    async def test_start_validation(self, repo, sample_session_data):
        """Should create/update validation record."""
        session = await repo.create_session(sample_session_data)
        
        await repo.start_validation(session.id)
        
        # Validation record should exist and be in processing state
        updated = await repo.get_session_by_id(session.id)
        assert updated.session_validation is not None
        assert updated.session_validation.validation_status == 'processing'
    
    async def test_complete_validation_passed(self, repo, sample_session_data):
        """Should mark validation as passed."""
        session = await repo.create_session(sample_session_data)
        await repo.start_validation(session.id)
        
        results = {'passed': 50, 'failed': 0}
        await repo.complete_validation(session.id, passed=True, results=results)
        
        updated = await repo.get_session_by_id(session.id)
        assert updated.session_validation.validation_passed is True
        assert updated.session_validation.last_validated_at is not None
    
    async def test_invalidate_validation(self, repo, sample_session_data):
        """Should invalidate previous validation."""
        session = await repo.create_session(sample_session_data)
        await repo.start_validation(session.id)
        await repo.complete_validation(session.id, passed=True, results={})
        
        await repo.invalidate_validation(session.id)
        
        updated = await repo.get_session_by_id(session.id)
        assert updated.session_validation.validation_passed is False
        assert updated.session_validation.last_invalidated_at is not None
    
    async def test_is_export_ready_requires_passed_validation(self, repo, sample_session_data):
        """Export ready only when validation passed and not invalidated."""
        session = await repo.create_session(sample_session_data)
        
        # No validation yet
        assert await repo.is_export_ready(session.id) is False
        
        # Validation passed
        await repo.start_validation(session.id)
        await repo.complete_validation(session.id, passed=True, results={})
        assert await repo.is_export_ready(session.id) is True
        
        # Validation invalidated
        await repo.invalidate_validation(session.id)
        assert await repo.is_export_ready(session.id) is False
```

---

## Part 4: Infrastructure Tests

### 4.1 Redis/ARQ Connection Tests

```python
# tests/backend/unit/test_infrastructure/test_redis_arq.py
import pytest
from arq.connections import ArqRedis

from app.core.redis import get_redis_settings, create_arq_pool


@pytest.mark.phase1
@pytest.mark.infrastructure
class TestRedisConnection:
    """Test Redis connectivity and ARQ pool creation."""
    
    async def test_redis_settings_from_config(self):
        """Should create valid Redis settings from config."""
        settings = get_redis_settings()
        
        assert settings.host is not None
        assert settings.port is not None
    
    async def test_arq_pool_connects(self):
        """Should successfully create ARQ connection pool."""
        pool = await create_arq_pool()
        
        assert pool is not None
        assert isinstance(pool, ArqRedis)
        
        # Verify connection works
        await pool.ping()
        
        await pool.close()
    
    async def test_arq_pool_can_enqueue_job(self):
        """Should be able to enqueue a test job."""
        pool = await create_arq_pool()
        
        # Enqueue a dummy job (won't execute without worker)
        job = await pool.enqueue_job('test_job', _job_id='test-123')
        
        assert job is not None
        
        await pool.close()
```

---

## Part 5: Implementation Specifications

After tests are written, implement the following components:

### 5.1 SQLAlchemy Models

**Files to create:**
- `/backend/app/models/__init__.py`
- `/backend/app/models/base.py` - Base class with common mixins
- `/backend/app/models/session.py` - Session, SessionTask, SessionValidation
- `/backend/app/models/upload.py` - UploadedFile
- `/backend/app/models/ticket.py` - Ticket, TicketDependency, Attachment
- `/backend/app/models/auth.py` - JiraAuthToken, JiraProjectContext
- `/backend/app/models/error.py` - SessionError, AuditLog

### 5.2 Repository Layer

**Files to create:**
- `/backend/app/repositories/__init__.py`
- `/backend/app/repositories/interfaces/` - All interface definitions
- `/backend/app/repositories/sqlalchemy/` - All SQLAlchemy implementations

### 5.3 Core Infrastructure

**Files to create:**
- `/backend/app/core/config.py` - Settings with Redis/ARQ config
- `/backend/app/core/database.py` - Async SQLAlchemy 2.0 setup
- `/backend/app/core/redis.py` - Redis connection factory
- `/backend/app/core/exceptions.py` - Base exception classes

### 5.4 Alembic Migrations

**Commands:**
```bash
# Initialize Alembic (if not done)
alembic init alembic

# Generate migration from models
alembic revision --autogenerate -m "Initial schema"

# Apply migration
alembic upgrade head
```

---

## Document References

### Primary References (in project knowledge)
- `Comprehensive_Updated_Directory_Structure_updated.md` - Directory layout
- `SQLAlchemy_Relationship_Bidirectional_Consistency_Audit_updated.md` - All relationships
- `Complete_Repository_Interface_Specifications.md` - Repository method signatures
- `repository_patterns_decisions_updated.md` - Repository patterns
- `fastapi_di_lifecycle_decisions_updated.md` - Database session management
- `background_task_infrastructure.md` - Redis/ARQ setup
- `base_schemas_models_updated.py` - All enum definitions

### Model Specifications
- `session_model_spec.md`
- `session_task_model_spec.md`
- `session_validation_model_spec_updated.md`
- `ticket_model_spec_updated.md`
- `ticket_dependency_model_spec.md`
- `attachment_model_spec.md`
- `uploaded_file_model_spec_updated.md`
- `jira_auth_token_model_spec.md`
- `jira_project_context_model_spec.md`
- `session_error_model_spec.md`
- `audit_log_model_spec.md`

---

## Success Criteria

### All Tests Pass
```bash
# Run all Phase 1 tests
pytest -m phase1 -v --cov=app/models --cov=app/repositories --cov-report=term-missing
```

### Coverage Requirements
- Models: >90% coverage
- Repositories: >80% coverage
- Infrastructure: >70% coverage

### Verification Checklist
- [ ] All 11 SQLAlchemy models created with correct fields
- [ ] All relationships are bidirectional and consistent
- [ ] Alembic migrations apply cleanly
- [ ] All repository interfaces defined
- [ ] All SQLAlchemy repository implementations complete
- [ ] Redis connection factory works
- [ ] ARQ pool can be created and used
- [ ] All Phase 1 tests pass
- [ ] No circular import issues

---

## Commands to Run

```bash
# Install dependencies
pip install pytest pytest-asyncio pytest-cov factory-boy httpx

# Run all Phase 1 tests
pytest -m phase1 -v

# Run Phase 1 tests with coverage
pytest -m phase1 -v --cov=app --cov-report=html

# Run only Phase 1 model tests
pytest -m "phase1 and models" -v

# Run only Phase 1 repository tests
pytest -m "phase1 and repositories" -v

# Run only Phase 1 infrastructure tests
pytest -m "phase1 and infrastructure" -v

# Run Phase 1 integration tests (migrations)
pytest -m "phase1 and integration" -v

# Apply migrations
alembic upgrade head

# Verify database schema
alembic current
```
