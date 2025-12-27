# **Comprehensive Updated Directory Structure - Drupal Ticket Generator**

## UPDATED: December 27, 2025
- Added pytest marker configuration for phase-based and component-based test selection
- Added Redis configuration and connection factory
- Added ARQ worker settings and job files
- Added progress schemas for WebSocket pub/sub
- Updated database module for async SQLAlchemy 2.0
- Note: `updated_directory_structure.md` is superseded by this document

---

```
drupal-ticket-generator/
├── README.md
├── docker-compose.yml
├── docker-compose.test.yml           # Test database + Redis setup
├── .env.example
├── .gitignore
├── .github/
│   └── workflows/
│       ├── test.yml                  # Multi-stage testing pipeline
│       └── deploy.yml
│
├── docs/                             # Project documentation
│   ├── api/                         # Auto-generated API docs
│   ├── implementation/              # Implementation-level docs
│   ├── sample_data/                 # CSV test files
│   │   ├── uwec_complete/           # Complete UWEC CSV set
│   │   └── test_cases/              # Broken CSV examples
│   └── user-guides/
│
├── backend/                          # Python FastAPI application
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── pyproject.toml
│   ├── alembic.ini                  # Database migrations
│   ├── alembic/                     # Migration files
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                  # FastAPI application entry with lifespan
│   │   │
│   │   ├── core/                    # Core configuration
│   │   │   ├── __init__.py
│   │   │   ├── config.py            # Environment variables & settings (includes Redis/ARQ)
│   │   │   ├── database.py          # Async database connection (SQLAlchemy 2.0 + asyncpg)
│   │   │   ├── redis.py             # Redis connection factory (ARQ settings)
│   │   │   ├── security.py          # Token encryption utilities (Fernet)
│   │   │   └── exceptions.py        # Base exception classes
│   │   │
│   │   ├── models/                  # SQLAlchemy models
│   │   │   ├── __init__.py
│   │   │   ├── base.py              # Base model class and common mixins
│   │   │   ├── session.py           # Session, SessionTask, SessionValidation
│   │   │   ├── upload.py            # UploadedFile
│   │   │   ├── ticket.py            # Ticket, TicketDependency, Attachment
│   │   │   ├── auth.py              # JiraAuthToken, JiraProjectContext
│   │   │   └── error.py             # SessionError, AuditLog
│   │   │
│   │   ├── schemas/                 # Pydantic models (complete set)
│   │   │   ├── __init__.py
│   │   │   ├── base.py              # Base classes, ALL enums, common patterns
│   │   │   ├── auth.py              # Authentication & session schemas
│   │   │   ├── upload.py            # Upload stage schemas
│   │   │   ├── processing.py        # Processing stage schemas
│   │   │   ├── review.py            # Review stage schemas  
│   │   │   ├── export.py            # Export/Jira stage schemas
│   │   │   ├── error.py             # Error response schemas
│   │   │   └── progress.py          # WebSocket progress message schemas
│   │   │
│   │   ├── repositories/            # Data access layer
│   │   │   ├── __init__.py
│   │   │   ├── base.py              # Async BaseRepository implementation
│   │   │   ├── exceptions.py        # Repository-specific exceptions
│   │   │   ├── interfaces/          # Abstract base classes
│   │   │   │   ├── __init__.py
│   │   │   │   ├── session_repository.py
│   │   │   │   ├── upload_repository.py
│   │   │   │   ├── ticket_repository.py
│   │   │   │   ├── auth_repository.py
│   │   │   │   └── error_repository.py
│   │   │   └── sqlalchemy/          # SQLAlchemy implementations
│   │   │       ├── __init__.py
│   │   │       ├── session_repository.py    # Session + SessionTask + SessionValidation
│   │   │       ├── upload_repository.py     # UploadedFile operations
│   │   │       ├── ticket_repository.py     # Ticket + Dependencies + Attachments
│   │   │       ├── auth_repository.py       # JiraAuthToken + JiraProjectContext
│   │   │       └── error_repository.py      # SessionError + AuditLog
│   │   │
│   │   ├── services/                # Business logic layer
│   │   │   ├── __init__.py
│   │   │   ├── session_service.py   # Session lifecycle management
│   │   │   ├── upload_service.py    # File processing & validation
│   │   │   ├── processing_service.py # Ticket generation coordination (+ ARQ enqueue)
│   │   │   ├── review_service.py    # Ticket editing & dependency management (+ ARQ enqueue)
│   │   │   ├── export_service.py    # Jira export coordination (+ ARQ enqueue)
│   │   │   └── exceptions.py        # Service-layer exceptions
│   │   │
│   │   ├── api/                     # FastAPI endpoints
│   │   │   ├── __init__.py
│   │   │   ├── dependencies/        # Dependency injection setup
│   │   │   │   ├── __init__.py
│   │   │   │   ├── auth.py          # Authentication dependencies
│   │   │   │   ├── repositories.py  # Repository dependencies (async)
│   │   │   │   ├── services.py      # Service dependencies (async)
│   │   │   │   └── external.py      # External service dependencies (Jira, LLM, ARQ pool)
│   │   │   ├── middleware/          # Custom middleware
│   │   │   │   ├── __init__.py
│   │   │   │   ├── correlation.py   # Request correlation IDs
│   │   │   │   ├── error_handler.py # Global error handling
│   │   │   │   └── session_validation.py # Session ownership validation
│   │   │   ├── v1/                  # API version 1
│   │   │   │   ├── __init__.py
│   │   │   │   ├── auth.py          # OAuth flow & session management
│   │   │   │   ├── upload.py        # File upload & validation
│   │   │   │   ├── processing.py    # Ticket generation
│   │   │   │   ├── review.py        # Ticket editing & review
│   │   │   │   ├── export.py        # Jira integration
│   │   │   │   └── health.py        # Health checks & diagnostics (includes worker health)
│   │   │   └── websockets/          # WebSocket handlers
│   │   │       ├── __init__.py
│   │   │       ├── processing.py    # Processing progress (Redis pub/sub subscriber)
│   │   │       └── export.py        # Export progress (Redis pub/sub subscriber)
│   │   │
│   │   ├── integrations/            # External services
│   │   │   ├── __init__.py
│   │   │   ├── jira/                # Jira REST API integration
│   │   │   │   ├── __init__.py
│   │   │   │   ├── client.py        # Main Jira API client
│   │   │   │   ├── auth.py          # OAuth 2.0 handling
│   │   │   │   ├── adf_converter.py # HTML to ADF conversion
│   │   │   │   ├── exceptions.py    # Jira-specific exceptions
│   │   │   │   └── models.py        # Jira API response models
│   │   │   └── llm/                 # LLM provider integration
│   │   │       ├── __init__.py
│   │   │       ├── interface.py     # LLM service interface
│   │   │       ├── service.py       # LLM service implementation
│   │   │       ├── openai_provider.py   # OpenAI implementation
│   │   │       ├── anthropic_provider.py # Anthropic implementation
│   │   │       ├── exceptions.py    # LLM-specific exceptions
│   │   │       └── prompts/         # Prompt templates
│   │   │           ├── __init__.py
│   │   │           ├── ticket_generation.py
│   │   │           └── error_explanation.py
│   │   │
│   │   └── workers/                 # ARQ background workers
│   │       ├── __init__.py
│   │       ├── settings.py          # ARQ WorkerSettings (functions, cron_jobs, redis_settings)
│   │       ├── jobs/                # Job function implementations
│   │       │   ├── __init__.py
│   │       │   ├── processing.py    # process_session_job (calls ProcessingService._execute_processing)
│   │       │   ├── export.py        # export_session_job (calls ExportService._execute_export)
│   │       │   ├── validation.py    # validate_adf_job (calls ReviewService._execute_validation)
│   │       │   └── cleanup.py       # Cleanup jobs (sessions, tokens, audit logs)
│   │       └── progress.py          # Redis pub/sub progress publisher utility
│   │
│   └── tests/                       # Test suite
│       ├── conftest.py              # Shared fixtures, factory registration
│       ├── pytest.ini               # Pytest configuration with markers
│       │
│       ├── backend/
│       │   ├── unit/                    # Pure unit tests (mocked dependencies)
│       │   │   ├── test_models/
│       │   │   │   ├── test_session_models.py
│       │   │   │   ├── test_ticket_models.py
│       │   │   │   ├── test_upload_models.py
│       │   │   │   ├── test_auth_models.py
│       │   │   │   └── test_error_models.py
│       │   │   ├── test_services/
│       │   │   │   ├── test_session_service.py
│       │   │   │   ├── test_upload_service.py
│       │   │   │   ├── test_processing_service.py
│       │   │   │   ├── test_review_service.py
│       │   │   │   └── test_export_service.py
│       │   │   ├── test_repositories/
│       │   │   │   ├── test_session_repository.py
│       │   │   │   ├── test_ticket_repository.py
│       │   │   │   ├── test_upload_repository.py
│       │   │   │   ├── test_auth_repository.py
│       │   │   │   └── test_error_repository.py
│       │   │   └── test_integrations/
│       │   │       ├── test_jira_client.py
│       │   │       └── test_llm_clients.py
│       │   │
│       │   ├── integration/             # Real database, mocked external APIs
│       │   │   ├── test_api_endpoints/  # FastAPI endpoint tests
│       │   │   │   ├── test_auth_endpoints.py
│       │   │   │   ├── test_upload_endpoints.py
│       │   │   │   ├── test_processing_endpoints.py
│       │   │   │   ├── test_review_endpoints.py
│       │   │   │   └── test_export_endpoints.py
│       │   │   ├── test_workflows/      # End-to-end workflow tests
│       │   │   │   ├── test_complete_workflow.py
│       │   │   │   ├── test_error_recovery.py
│       │   │   │   └── test_session_recovery.py
│       │   │   └── test_database/       # Database integration tests
│       │   │       ├── test_migrations.py
│       │   │       ├── test_relationships.py
│       │   │       └── test_constraints.py
│       │   │
│       │   └── fixtures/                # Test data and utilities
│       │       ├── factories/           # Factory Boy model factories
│       │       │   ├── __init__.py
│       │       │   ├── session_factory.py
│       │       │   ├── ticket_factory.py
│       │       │   ├── upload_factory.py
│       │       │   └── auth_factory.py
│       │       ├── sample_data/         # Test CSV files
│       │       │   ├── valid/           # Valid CSV test cases
│       │       │   ├── invalid/         # Invalid CSV test cases
│       │       │   └── edge_cases/      # Edge case CSV files
│       │       ├── api_responses/       # Mock API responses
│       │       │   ├── jira_responses.json
│       │       │   └── llm_responses.json
│       │       ├── database_fixtures.py # Database test data factories
│       │       └── test_builders.py     # Test data builders
│       │
│       ├── frontend/
│       │   ├── unit/                    # Component unit tests
│       │   │   ├── components/          # Component tests
│       │   │   ├── services/            # Service tests
│       │   │   └── utils/               # Utility tests
│       │   ├── integration/             # Component integration tests
│       │   │   ├── workflows/           # User workflow tests
│       │   │   └── api_integration/     # API integration tests
│       │   └── e2e/                     # End-to-end tests
│       │       ├── auth_flow.spec.js    # Authentication flow
│       │       ├── upload_flow.spec.js  # File upload flow
│       │       ├── processing_flow.spec.js # Processing flow
│       │       ├── review_flow.spec.js  # Review flow
│       │       └── export_flow.spec.js  # Export flow
│       │
│       └── shared/                      # Cross-stack test utilities
│           ├── test_helpers.py          # Python test utilities
│           ├── test_helpers.js          # JavaScript test utilities
│           └── mock_data/               # Shared mock data
│               ├── csv_samples/         # Sample CSV files
│               ├── api_responses/       # Mock API responses
│               └── database_seeds/      # Database seed data
```

---

## **Pytest Marker Configuration**

### pytest.ini

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# Marker definitions for phase-based and component-based test selection
markers =
    # Phase markers - run tests by implementation phase
    phase1: Phase 1 - Foundation & Infrastructure (models, repositories, Redis/ARQ)
    phase2: Phase 2 - Authentication & Session Management
    phase3: Phase 3 - File Upload & CSV Validation
    phase4: Phase 4 - Processing & Ticket Generation
    phase5: Phase 5 - Review Stage
    phase6: Phase 6 - Jira Export
    
    # Component markers - run tests by component type
    models: SQLAlchemy model tests
    repositories: Repository layer tests
    services: Service layer tests
    api: API endpoint tests
    integrations: External integration tests (Jira, LLM)
    workers: ARQ worker/job tests
    infrastructure: Infrastructure tests (Redis, database connections)
    
    # Test type markers
    unit: Unit tests (mocked dependencies)
    integration: Integration tests (real database, mocked external APIs)
    e2e: End-to-end tests
    slow: Tests that take longer to run
```

### Marker Usage Examples

```bash
# Run all Phase 1 tests
pytest -m phase1

# Run all model tests across all phases
pytest -m models

# Run Phase 1 model tests only
pytest -m "phase1 and models"

# Run all unit tests
pytest -m unit

# Run Phase 2 service tests
pytest -m "phase2 and services"

# Run integration tests excluding slow tests
pytest -m "integration and not slow"

# Run all repository tests with coverage
pytest -m repositories --cov=app/repositories --cov-report=term-missing

# Run Phase 4 worker tests
pytest -m "phase4 and workers"
```

### Applying Markers to Test Classes

Each test class should have both a phase marker and a component marker:

```python
import pytest

@pytest.mark.phase1
@pytest.mark.models
class TestSessionModel:
    """Test Session model field definitions and relationships."""
    
    def test_session_has_required_fields(self):
        ...

@pytest.mark.phase1
@pytest.mark.repositories
class TestSessionRepositoryCRUD:
    """Test basic CRUD operations."""
    
    async def test_create_session(self, repo, sample_session_data):
        ...

@pytest.mark.phase2
@pytest.mark.services
class TestSessionServiceCreation:
    """Test session creation operations."""
    
    async def test_create_session_stores_in_database(self):
        ...
```

---

## **Key Architectural Decisions Resolved**

### **1. Async Database Layer**
- **SQLAlchemy 2.0**: Full async support with `create_async_engine()`
- **asyncpg driver**: PostgreSQL async driver for non-blocking I/O
- **AsyncSession**: All repository operations are async

### **2. Background Task Infrastructure**
- **ARQ + Redis**: Async-native task queue with Redis as broker
- **Redis dual-role**: Task queue storage + pub/sub for WebSocket progress
- **Single worker process**: Handles all job types (processing, export, validation, cleanup)
- **Cron jobs**: Scheduled cleanup tasks for sessions, audit logs, tokens

### **3. Model Organization**
- **Logical grouping**: Related models in same files (Session + SessionTask + SessionValidation)
- **Clear separation**: Upload models separate from session models
- **Relationship clarity**: Models grouped by business domain

### **4. Repository Pattern Implementation**
- **Interface-first design**: Abstract interfaces define contracts
- **SQLAlchemy implementations**: Concrete async implementations in dedicated directory
- **Aggregate repositories**: Handle related models together (Session + SessionTask + SessionValidation)

### **5. Service Layer Organization**
- **One service per workflow stage**: Clear responsibility boundaries
- **ARQ integration**: Services that start background tasks receive `arq_pool` dependency
- **Two methods per async operation**: Public (enqueue) + Internal (execute)

### **6. Schema Organization**
- **Centralized enums**: ALL enums defined in `schemas/base.py`
- **Stage-based organization**: Schemas grouped by workflow stage
- **Progress schemas**: Dedicated file for WebSocket pub/sub messages

### **7. External Integration**
- **Provider-agnostic design**: LLM interface with multiple implementations
- **Jira integration**: Complete OAuth and API integration
- **Error handling**: Integration-specific exception handling

### **8. Testing Strategy**
- **Async-first**: All tests use `@pytest.mark.asyncio` and `AsyncMock`
- **Type-based organization**: Tests organized by type (unit/integration/e2e)
- **Phase markers**: Run tests by implementation phase during development
- **Component markers**: Run tests by component type for targeted testing
- **Worker tests**: Dedicated tests for ARQ job functions
- **Fixture organization**: Reusable test data and utilities

## **Configuration Files Reference**

### **Core Configuration Files**
| File | Purpose |
|------|---------|
| `core/config.py` | All environment settings (DB, Redis, ARQ, Jira, LLM) |
| `core/database.py` | Async SQLAlchemy engine and session factory |
| `core/redis.py` | Redis connection factory for ARQ |
| `workers/settings.py` | ARQ WorkerSettings with all jobs and cron tasks |

### **Docker Compose Services**
| Service | Purpose |
|---------|---------|
| `db` | PostgreSQL database |
| `redis` | Redis for task queue + pub/sub |
| `api` | FastAPI application |
| `worker` | ARQ worker process |

## **Superseded Documents**

The following documents are superseded by this comprehensive structure:
- `updated_directory_structure.md` - Remove from project

## **Implementation Benefits**

### **Discrepancy Resolution**
- ✅ **Consistent file locations**: All models in appropriate files
- ✅ **Unified enum definitions**: All enums in `schemas/base.py`
- ✅ **Clear repository interfaces**: Complete interface definitions
- ✅ **Comprehensive response models**: All missing models included
- ✅ **Consistent naming**: Repository and service naming aligned
- ✅ **Async throughout**: Full async support from database to endpoints
- ✅ **Test organization**: Type-based structure with phase/component markers

### **Development Efficiency**
- **Clear module boundaries**: Easy to understand and navigate
- **Dependency injection**: Testable and maintainable architecture
- **Separation of concerns**: Business logic separated from infrastructure
- **Comprehensive testing**: Multiple testing strategies for reliability
- **Flexible test selection**: Run by phase during development, by component for targeted testing

### **Operational Characteristics**
- **Standard patterns**: Familiar web application structure
- **Database migrations**: Proper schema evolution support
- **Background processing**: ARQ for scalable task processing
- **Real-time updates**: Redis pub/sub for WebSocket progress
- **External service integration**: Robust integration patterns

This structure resolves all identified discrepancies and provides a solid foundation for async-first implementation.
