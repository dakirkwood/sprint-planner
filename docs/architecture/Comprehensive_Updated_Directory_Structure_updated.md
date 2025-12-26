# **Comprehensive Updated Directory Structure - Drupal Ticket Generator**

## UPDATED: December 25, 2025
- Added Redis configuration and connection factory
- Added ARQ worker settings and job files
- Added progress schemas for WebSocket pub/sub
- Updated database module for async SQLAlchemy 2.0
- Note: `updated_directory_structure.md` is superseded by this document

---

```
drupal-ticket-generator/
â”œâ”€â”€ README.md
â”œâ”€â”€ docker-compose.yml
â”œâ”€â”€ docker-compose.test.yml           # Test database + Redis setup
â”œâ”€â”€ .env.example
â”œâ”€â”€ .gitignore
â”œâ”€â”€ .github/
â”‚   â””â”€â”€ workflows/
â”‚       â”œâ”€â”€ test.yml                  # Multi-stage testing pipeline
â”‚       â””â”€â”€ deploy.yml
â”‚
â”œâ”€â”€ docs/                             # Project documentation
â”‚   â”œâ”€â”€ api/                         # Auto-generated API docs
â”‚   â”œâ”€â”€ implementation/              # Implementation-level docs
â”‚   â”œâ”€â”€ sample_data/                 # CSV test files
â”‚   â”‚   â”œâ”€â”€ uwec_complete/           # Complete UWEC CSV set
â”‚   â”‚   â””â”€â”€ test_cases/              # Broken CSV examples
â”‚   â””â”€â”€ user-guides/
â”‚
â”œâ”€â”€ backend/                          # Python FastAPI application
â”‚   â”œâ”€â”€ Dockerfile
â”‚   â”œâ”€â”€ requirements.txt
â”‚   â”œâ”€â”€ pyproject.toml
â”‚   â”œâ”€â”€ alembic.ini                  # Database migrations
â”‚   â”œâ”€â”€ alembic/                     # Migration files
â”‚   â”œâ”€â”€ app/
â”‚   â”‚   â”œâ”€â”€ __init__.py
â”‚   â”‚   â”œâ”€â”€ main.py                  # FastAPI application entry with lifespan
â”‚   â”‚   â”‚
â”‚   â”‚   â”œâ”€â”€ core/                    # Core configuration
â”‚   â”‚   â”‚   â”œâ”€â”€ __init__.py
â”‚   â”‚   â”‚   â”œâ”€â”€ config.py            # Environment variables & settings (includes Redis/ARQ)
â”‚   â”‚   â”‚   â”œâ”€â”€ database.py          # Async database connection (SQLAlchemy 2.0 + asyncpg)
â”‚   â”‚   â”‚   â”œâ”€â”€ redis.py             # Redis connection factory (ARQ settings)
â”‚   â”‚   â”‚   â”œâ”€â”€ security.py          # Token encryption utilities (Fernet)
â”‚   â”‚   â”‚   â””â”€â”€ exceptions.py        # Base exception classes
â”‚   â”‚   â”‚
â”‚   â”‚   â”œâ”€â”€ models/                  # SQLAlchemy models
â”‚   â”‚   â”‚   â”œâ”€â”€ __init__.py
â”‚   â”‚   â”‚   â”œâ”€â”€ base.py              # Base model class and common mixins
â”‚   â”‚   â”‚   â”œâ”€â”€ session.py           # Session, SessionTask, SessionValidation
â”‚   â”‚   â”‚   â”œâ”€â”€ upload.py            # UploadedFile
â”‚   â”‚   â”‚   â”œâ”€â”€ ticket.py            # Ticket, TicketDependency, Attachment
â”‚   â”‚   â”‚   â”œâ”€â”€ auth.py              # JiraAuthToken, JiraProjectContext
â”‚   â”‚   â”‚   â””â”€â”€ error.py             # SessionError, AuditLog
â”‚   â”‚   â”‚
â”‚   â”‚   â”œâ”€â”€ schemas/                 # Pydantic models (complete set)
â”‚   â”‚   â”‚   â”œâ”€â”€ __init__.py
â”‚   â”‚   â”‚   â”œâ”€â”€ base.py              # Base classes, ALL enums, common patterns
â”‚   â”‚   â”‚   â”œâ”€â”€ auth.py              # Authentication & session schemas
â”‚   â”‚   â”‚   â”œâ”€â”€ upload.py            # Upload stage schemas
â”‚   â”‚   â”‚   â”œâ”€â”€ processing.py        # Processing stage schemas
â”‚   â”‚   â”‚   â”œâ”€â”€ review.py            # Review stage schemas  
â”‚   â”‚   â”‚   â”œâ”€â”€ export.py            # Export/Jira stage schemas
â”‚   â”‚   â”‚   â”œâ”€â”€ error.py             # Error response schemas
â”‚   â”‚   â”‚   â””â”€â”€ progress.py          # WebSocket progress message schemas
â”‚   â”‚   â”‚
â”‚   â”‚   â”œâ”€â”€ repositories/            # Data access layer
â”‚   â”‚   â”‚   â”œâ”€â”€ __init__.py
â”‚   â”‚   â”‚   â”œâ”€â”€ base.py              # Async BaseRepository implementation
â”‚   â”‚   â”‚   â”œâ”€â”€ exceptions.py        # Repository-specific exceptions
â”‚   â”‚   â”‚   â”œâ”€â”€ interfaces/          # Abstract base classes
â”‚   â”‚   â”‚   â”‚   â”œâ”€â”€ __init__.py
â”‚   â”‚   â”‚   â”‚   â”œâ”€â”€ session_repository.py
â”‚   â”‚   â”‚   â”‚   â”œâ”€â”€ upload_repository.py
â”‚   â”‚   â”‚   â”‚   â”œâ”€â”€ ticket_repository.py
â”‚   â”‚   â”‚   â”‚   â”œâ”€â”€ auth_repository.py
â”‚   â”‚   â”‚   â”‚   â””â”€â”€ error_repository.py
â”‚   â”‚   â”‚   â””â”€â”€ sqlalchemy/          # SQLAlchemy implementations
â”‚   â”‚   â”‚       â”œâ”€â”€ __init__.py
â”‚   â”‚   â”‚       â”œâ”€â”€ session_repository.py    # Session + SessionTask + SessionValidation
â”‚   â”‚   â”‚       â”œâ”€â”€ upload_repository.py     # UploadedFile operations
â”‚   â”‚   â”‚       â”œâ”€â”€ ticket_repository.py     # Ticket + Dependencies + Attachments
â”‚   â”‚   â”‚       â”œâ”€â”€ auth_repository.py       # JiraAuthToken + JiraProjectContext
â”‚   â”‚   â”‚       â””â”€â”€ error_repository.py      # SessionError + AuditLog
â”‚   â”‚   â”‚
â”‚   â”‚   â”œâ”€â”€ services/                # Business logic layer
â”‚   â”‚   â”‚   â”œâ”€â”€ __init__.py
â”‚   â”‚   â”‚   â”œâ”€â”€ session_service.py   # Session lifecycle management
â”‚   â”‚   â”‚   â”œâ”€â”€ upload_service.py    # File processing & validation
â”‚   â”‚   â”‚   â”œâ”€â”€ processing_service.py # Ticket generation coordination (+ ARQ enqueue)
â”‚   â”‚   â”‚   â”œâ”€â”€ review_service.py    # Ticket editing & dependency management (+ ARQ enqueue)
â”‚   â”‚   â”‚   â”œâ”€â”€ export_service.py    # Jira export coordination (+ ARQ enqueue)
â”‚   â”‚   â”‚   â””â”€â”€ exceptions.py        # Service-layer exceptions
â”‚   â”‚   â”‚
â”‚   â”‚   â”œâ”€â”€ api/                     # FastAPI endpoints
â”‚   â”‚   â”‚   â”œâ”€â”€ __init__.py
â”‚   â”‚   â”‚   â”œâ”€â”€ dependencies/        # Dependency injection setup
â”‚   â”‚   â”‚   â”‚   â”œâ”€â”€ __init__.py
â”‚   â”‚   â”‚   â”‚   â”œâ”€â”€ auth.py          # Authentication dependencies
â”‚   â”‚   â”‚   â”‚   â”œâ”€â”€ repositories.py  # Repository dependencies (async)
â”‚   â”‚   â”‚   â”‚   â”œâ”€â”€ services.py      # Service dependencies (async)
â”‚   â”‚   â”‚   â”‚   â””â”€â”€ external.py      # External service dependencies (Jira, LLM, ARQ pool)
â”‚   â”‚   â”‚   â”œâ”€â”€ middleware/          # Custom middleware
â”‚   â”‚   â”‚   â”‚   â”œâ”€â”€ __init__.py
â”‚   â”‚   â”‚   â”‚   â”œâ”€â”€ correlation.py   # Request correlation IDs
â”‚   â”‚   â”‚   â”‚   â”œâ”€â”€ error_handler.py # Global error handling
â”‚   â”‚   â”‚   â”‚   â””â”€â”€ session_validation.py # Session ownership validation
â”‚   â”‚   â”‚   â”œâ”€â”€ v1/                  # API version 1
â”‚   â”‚   â”‚   â”‚   â”œâ”€â”€ __init__.py
â”‚   â”‚   â”‚   â”‚   â”œâ”€â”€ auth.py          # OAuth flow & session management
â”‚   â”‚   â”‚   â”‚   â”œâ”€â”€ upload.py        # File upload & validation
â”‚   â”‚   â”‚   â”‚   â”œâ”€â”€ processing.py    # Ticket generation
â”‚   â”‚   â”‚   â”‚   â”œâ”€â”€ review.py        # Ticket editing & review
â”‚   â”‚   â”‚   â”‚   â”œâ”€â”€ export.py        # Jira integration
â”‚   â”‚   â”‚   â”‚   â””â”€â”€ health.py        # Health checks & diagnostics (includes worker health)
â”‚   â”‚   â”‚   â””â”€â”€ websockets/          # WebSocket handlers
â”‚   â”‚   â”‚       â”œâ”€â”€ __init__.py
â”‚   â”‚   â”‚       â”œâ”€â”€ processing.py    # Processing progress (Redis pub/sub subscriber)
â”‚   â”‚   â”‚       â””â”€â”€ export.py        # Export progress (Redis pub/sub subscriber)
â”‚   â”‚   â”‚
â”‚   â”‚   â”œâ”€â”€ integrations/            # External services
â”‚   â”‚   â”‚   â”œâ”€â”€ __init__.py
â”‚   â”‚   â”‚   â”œâ”€â”€ jira/                # Jira REST API integration
â”‚   â”‚   â”‚   â”‚   â”œâ”€â”€ __init__.py
â”‚   â”‚   â”‚   â”‚   â”œâ”€â”€ client.py        # Main Jira API client
â”‚   â”‚   â”‚   â”‚   â”œâ”€â”€ auth.py          # OAuth 2.0 handling
â”‚   â”‚   â”‚   â”‚   â”œâ”€â”€ adf_converter.py # HTML to ADF conversion
â”‚   â”‚   â”‚   â”‚   â”œâ”€â”€ exceptions.py    # Jira-specific exceptions
â”‚   â”‚   â”‚   â”‚   â””â”€â”€ models.py        # Jira API response models
â”‚   â”‚   â”‚   â””â”€â”€ llm/                 # LLM provider integration
â”‚   â”‚   â”‚       â”œâ”€â”€ __init__.py
â”‚   â”‚   â”‚       â”œâ”€â”€ interface.py     # LLM service interface
â”‚   â”‚   â”‚       â”œâ”€â”€ service.py       # LLM service implementation
â”‚   â”‚   â”‚       â”œâ”€â”€ openai_provider.py   # OpenAI implementation
â”‚   â”‚   â”‚       â”œâ”€â”€ anthropic_provider.py # Anthropic implementation
â”‚   â”‚   â”‚       â”œâ”€â”€ exceptions.py    # LLM-specific exceptions
â”‚   â”‚   â”‚       â””â”€â”€ prompts/         # Prompt templates
â”‚   â”‚   â”‚           â”œâ”€â”€ __init__.py
â”‚   â”‚   â”‚           â”œâ”€â”€ ticket_generation.py
â”‚   â”‚   â”‚           â””â”€â”€ error_explanation.py
â”‚   â”‚   â”‚
â”‚   â”‚   â”œâ”€â”€ utils/                   # Utility modules
â”‚   â”‚   â”‚   â”œâ”€â”€ __init__.py
â”‚   â”‚   â”‚   â”œâ”€â”€ csv/                 # CSV processing utilities
â”‚   â”‚   â”‚   â”‚   â”œâ”€â”€ __init__.py
â”‚   â”‚   â”‚   â”‚   â”œâ”€â”€ registry.py      # CSV type registry & detection
â”‚   â”‚   â”‚   â”‚   â”œâ”€â”€ parser.py        # CSV parsing utilities
â”‚   â”‚   â”‚   â”‚   â”œâ”€â”€ validator.py     # CSV validation engine
â”‚   â”‚   â”‚   â”‚   â””â”€â”€ relationships.py # Cross-file relationship mapping
â”‚   â”‚   â”‚   â”œâ”€â”€ logging.py           # Logging configuration
â”‚   â”‚   â”‚   â”œâ”€â”€ formatting.py        # Response formatting utilities
â”‚   â”‚   â”‚   â””â”€â”€ validators.py        # Custom validation functions
â”‚   â”‚   â”‚
â”‚   â”‚   â””â”€â”€ workers/                 # ARQ background task workers
â”‚   â”‚       â”œâ”€â”€ __init__.py
â”‚   â”‚       â”œâ”€â”€ settings.py          # ARQ WorkerSettings (functions, cron_jobs, startup/shutdown)
â”‚   â”‚       â”œâ”€â”€ utils.py             # Shared worker utilities (progress publishing)
â”‚   â”‚       â”œâ”€â”€ processing_worker.py # generate_tickets_job
â”‚   â”‚       â”œâ”€â”€ export_worker.py     # export_session_job
â”‚   â”‚       â”œâ”€â”€ validation_worker.py # validate_adf_job
â”‚   â”‚       â””â”€â”€ cleanup_worker.py    # Scheduled cleanup jobs (sessions, audit logs, tokens)
â”‚   â”‚
â”‚   â””â”€â”€ scripts/                     # Management scripts
â”‚       â”œâ”€â”€ create_test_data.py      # Generate test CSVs
â”‚       â”œâ”€â”€ reset_database.py        # Development utilities
â”‚       â””â”€â”€ migrate_data.py          # Data migration scripts
â”‚
â”œâ”€â”€ frontend/                        # Vue.js application
â”‚   â”œâ”€â”€ Dockerfile
â”‚   â”œâ”€â”€ package.json
â”‚   â”œâ”€â”€ vite.config.js
â”‚   â”œâ”€â”€ src/
â”‚   â”‚   â”œâ”€â”€ main.js
â”‚   â”‚   â”œâ”€â”€ App.vue
â”‚   â”‚   â”‚
â”‚   â”‚   â”œâ”€â”€ components/              # Vue components
â”‚   â”‚   â”‚   â”œâ”€â”€ common/              # Reusable UI components
â”‚   â”‚   â”‚   â”‚   â”œâ”€â”€ LoadingSpinner.vue
â”‚   â”‚   â”‚   â”‚   â”œâ”€â”€ ErrorDisplay.vue
â”‚   â”‚   â”‚   â”‚   â”œâ”€â”€ ProgressBar.vue
â”‚   â”‚   â”‚   â”‚   â””â”€â”€ FileUploader.vue
â”‚   â”‚   â”‚   â”œâ”€â”€ auth/                # Authentication components
â”‚   â”‚   â”‚   â”‚   â”œâ”€â”€ LoginCallback.vue
â”‚   â”‚   â”‚   â”‚   â””â”€â”€ SessionRecovery.vue
â”‚   â”‚   â”‚   â”œâ”€â”€ upload/              # Upload stage components
â”‚   â”‚   â”‚   â”‚   â”œâ”€â”€ FileUploadZone.vue
â”‚   â”‚   â”‚   â”‚   â”œâ”€â”€ ClassificationReview.vue
â”‚   â”‚   â”‚   â”‚   â””â”€â”€ ValidationResults.vue
â”‚   â”‚   â”‚   â”œâ”€â”€ processing/          # Processing stage components
â”‚   â”‚   â”‚   â”‚   â”œâ”€â”€ ProcessingProgress.vue
â”‚   â”‚   â”‚   â”‚   â””â”€â”€ ProcessingErrors.vue
â”‚   â”‚   â”‚   â”œâ”€â”€ review/              # Review stage components
â”‚   â”‚   â”‚   â”‚   â”œâ”€â”€ TicketList.vue
â”‚   â”‚   â”‚   â”‚   â”œâ”€â”€ TicketEditor.vue
â”‚   â”‚   â”‚   â”‚   â”œâ”€â”€ DependencyGraph.vue
â”‚   â”‚   â”‚   â”‚   â””â”€â”€ BulkActions.vue
â”‚   â”‚   â”‚   â””â”€â”€ export/              # Export stage components
â”‚   â”‚   â”‚       â”œâ”€â”€ ExportProgress.vue
â”‚   â”‚   â”‚       â”œâ”€â”€ ExportResults.vue
â”‚   â”‚   â”‚       â””â”€â”€ ManualFixGuidance.vue
â”‚   â”‚   â”‚
â”‚   â”‚   â”œâ”€â”€ views/                   # Page components
â”‚   â”‚   â”‚   â”œâ”€â”€ AuthCallback.vue     # OAuth callback handling
â”‚   â”‚   â”‚   â”œâ”€â”€ SessionSetup.vue     # Site info collection
â”‚   â”‚   â”‚   â”œâ”€â”€ Upload.vue           # File upload interface
â”‚   â”‚   â”‚   â”œâ”€â”€ Processing.vue       # Processing progress
â”‚   â”‚   â”‚   â”œâ”€â”€ Review.vue           # Ticket review interface
â”‚   â”‚   â”‚   â””â”€â”€ Export.vue           # Jira export interface
â”‚   â”‚   â”‚
â”‚   â”‚   â”œâ”€â”€ stores/                  # Pinia state management
â”‚   â”‚   â”‚   â”œâ”€â”€ auth.js              # Authentication state
â”‚   â”‚   â”‚   â”œâ”€â”€ session.js           # Current session state
â”‚   â”‚   â”‚   â”œâ”€â”€ upload.js            # Upload stage state
â”‚   â”‚   â”‚   â”œâ”€â”€ tickets.js           # Ticket data & editing
â”‚   â”‚   â”‚   â”œâ”€â”€ processing.js        # Processing progress state
â”‚   â”‚   â”‚   â”œâ”€â”€ export.js            # Export progress & results
â”‚   â”‚   â”‚   â””â”€â”€ notifications.js     # Toast notifications
â”‚   â”‚   â”‚
â”‚   â”‚   â”œâ”€â”€ services/                # API integration
â”‚   â”‚   â”‚   â”œâ”€â”€ api.js               # Base axios configuration
â”‚   â”‚   â”‚   â”œâ”€â”€ auth.service.js      # Authentication API calls
â”‚   â”‚   â”‚   â”œâ”€â”€ session.service.js   # Session management API calls
â”‚   â”‚   â”‚   â”œâ”€â”€ upload.service.js    # File upload API calls
â”‚   â”‚   â”‚   â”œâ”€â”€ processing.service.js # Processing API calls
â”‚   â”‚   â”‚   â”œâ”€â”€ review.service.js    # Review API calls
â”‚   â”‚   â”‚   â”œâ”€â”€ export.service.js    # Export API calls
â”‚   â”‚   â”‚   â””â”€â”€ websocket.service.js # WebSocket management
â”‚   â”‚   â”‚
â”‚   â”‚   â”œâ”€â”€ composables/             # Vue 3 composables
â”‚   â”‚   â”‚   â”œâ”€â”€ useAuth.js           # Authentication logic
â”‚   â”‚   â”‚   â”œâ”€â”€ useWebSocket.js      # WebSocket management
â”‚   â”‚   â”‚   â”œâ”€â”€ useFileUpload.js     # File upload logic
â”‚   â”‚   â”‚   â””â”€â”€ useErrorHandling.js  # Error handling patterns
â”‚   â”‚   â”‚
â”‚   â”‚   â”œâ”€â”€ utils/                   # Frontend utilities
â”‚   â”‚   â”‚   â”œâ”€â”€ constants.js         # Application constants
â”‚   â”‚   â”‚   â”œâ”€â”€ formatters.js        # Data formatting
â”‚   â”‚   â”‚   â”œâ”€â”€ validators.js        # Client-side validation
â”‚   â”‚   â”‚   â””â”€â”€ errorHandlers.js     # Error categorization
â”‚   â”‚   â”‚
â”‚   â”‚   â””â”€â”€ assets/                  # Static assets
â”‚   â”‚       â”œâ”€â”€ styles/              # CSS/SCSS files
â”‚   â”‚       â””â”€â”€ images/              # Image assets
â”‚
â””â”€â”€ tests/                           # Comprehensive test suites
    â”œâ”€â”€ backend/
    â”‚   â”œâ”€â”€ conftest.py              # Pytest configuration & async fixtures
    â”‚   â”œâ”€â”€ unit/                    # Fast tests with mocked dependencies
    â”‚   â”‚   â”œâ”€â”€ test_models/         # SQLAlchemy model tests
    â”‚   â”‚   â”‚   â”œâ”€â”€ test_session.py
    â”‚   â”‚   â”‚   â”œâ”€â”€ test_upload.py
    â”‚   â”‚   â”‚   â”œâ”€â”€ test_ticket.py
    â”‚   â”‚   â”‚   â”œâ”€â”€ test_auth.py
    â”‚   â”‚   â”‚   â””â”€â”€ test_error.py
    â”‚   â”‚   â”œâ”€â”€ test_repositories/   # Repository interface tests (AsyncMock)
    â”‚   â”‚   â”‚   â”œâ”€â”€ test_session_repository.py
    â”‚   â”‚   â”‚   â”œâ”€â”€ test_upload_repository.py
    â”‚   â”‚   â”‚   â”œâ”€â”€ test_ticket_repository.py
    â”‚   â”‚   â”‚   â”œâ”€â”€ test_auth_repository.py
    â”‚   â”‚   â”‚   â””â”€â”€ test_error_repository.py
    â”‚   â”‚   â”œâ”€â”€ test_services/       # Business logic tests (AsyncMock)
    â”‚   â”‚   â”‚   â”œâ”€â”€ test_session_service.py
    â”‚   â”‚   â”‚   â”œâ”€â”€ test_upload_service.py
    â”‚   â”‚   â”‚   â”œâ”€â”€ test_processing_service.py
    â”‚   â”‚   â”‚   â”œâ”€â”€ test_review_service.py
    â”‚   â”‚   â”‚   â””â”€â”€ test_export_service.py
    â”‚   â”‚   â”œâ”€â”€ test_workers/        # ARQ job function tests
    â”‚   â”‚   â”‚   â”œâ”€â”€ test_processing_worker.py
    â”‚   â”‚   â”‚   â”œâ”€â”€ test_export_worker.py
    â”‚   â”‚   â”‚   â””â”€â”€ test_cleanup_worker.py
    â”‚   â”‚   â”œâ”€â”€ test_utils/          # Utility function tests
    â”‚   â”‚   â”‚   â”œâ”€â”€ test_csv_registry.py
    â”‚   â”‚   â”‚   â”œâ”€â”€ test_csv_parser.py
    â”‚   â”‚   â”‚   â””â”€â”€ test_validators.py
    â”‚   â”‚   â””â”€â”€ test_integrations/   # External service tests (mocked)
    â”‚   â”‚       â”œâ”€â”€ test_jira_client.py
    â”‚   â”‚       â””â”€â”€ test_llm_clients.py
    â”‚   â”‚
    â”‚   â”œâ”€â”€ integration/             # Real database, mocked external APIs
    â”‚   â”‚   â”œâ”€â”€ test_api_endpoints/  # FastAPI endpoint tests
    â”‚   â”‚   â”‚   â”œâ”€â”€ test_auth_endpoints.py
    â”‚   â”‚   â”‚   â”œâ”€â”€ test_upload_endpoints.py
    â”‚   â”‚   â”‚   â”œâ”€â”€ test_processing_endpoints.py
    â”‚   â”‚   â”‚   â”œâ”€â”€ test_review_endpoints.py
    â”‚   â”‚   â”‚   â””â”€â”€ test_export_endpoints.py
    â”‚   â”‚   â”œâ”€â”€ test_workflows/      # End-to-end workflow tests
    â”‚   â”‚   â”‚   â”œâ”€â”€ test_complete_workflow.py
    â”‚   â”‚   â”‚   â”œâ”€â”€ test_error_recovery.py
    â”‚   â”‚   â”‚   â””â”€â”€ test_session_recovery.py
    â”‚   â”‚   â””â”€â”€ test_database/       # Database integration tests
    â”‚   â”‚       â”œâ”€â”€ test_migrations.py
    â”‚   â”‚       â”œâ”€â”€ test_relationships.py
    â”‚   â”‚       â””â”€â”€ test_constraints.py
    â”‚   â”‚
    â”‚   â””â”€â”€ fixtures/                # Test data and utilities
    â”‚       â”œâ”€â”€ sample_data/         # Test CSV files
    â”‚       â”‚   â”œâ”€â”€ valid/           # Valid CSV test cases
    â”‚       â”‚   â”œâ”€â”€ invalid/         # Invalid CSV test cases
    â”‚       â”‚   â””â”€â”€ edge_cases/      # Edge case CSV files
    â”‚       â”œâ”€â”€ api_responses/       # Mock API responses
    â”‚       â”‚   â”œâ”€â”€ jira_responses.json
    â”‚       â”‚   â””â”€â”€ llm_responses.json
    â”‚       â”œâ”€â”€ database_fixtures.py # Database test data factories
    â”‚       â””â”€â”€ test_builders.py     # Test data builders
    â”‚
    â”œâ”€â”€ frontend/
    â”‚   â”œâ”€â”€ unit/                    # Component unit tests
    â”‚   â”‚   â”œâ”€â”€ components/          # Component tests
    â”‚   â”‚   â”œâ”€â”€ services/            # Service tests
    â”‚   â”‚   â””â”€â”€ utils/               # Utility tests
    â”‚   â”œâ”€â”€ integration/             # Component integration tests
    â”‚   â”‚   â”œâ”€â”€ workflows/           # User workflow tests
    â”‚   â”‚   â””â”€â”€ api_integration/     # API integration tests
    â”‚   â””â”€â”€ e2e/                     # End-to-end tests
    â”‚       â”œâ”€â”€ auth_flow.spec.js    # Authentication flow
    â”‚       â”œâ”€â”€ upload_flow.spec.js  # File upload flow
    â”‚       â”œâ”€â”€ processing_flow.spec.js # Processing flow
    â”‚       â”œâ”€â”€ review_flow.spec.js  # Review flow
    â”‚       â””â”€â”€ export_flow.spec.js  # Export flow
    â”‚
    â””â”€â”€ shared/                      # Cross-stack test utilities
        â”œâ”€â”€ test_helpers.py          # Python test utilities
        â”œâ”€â”€ test_helpers.js          # JavaScript test utilities
        â””â”€â”€ mock_data/               # Shared mock data
            â”œâ”€â”€ csv_samples/         # Sample CSV files
            â”œâ”€â”€ api_responses/       # Mock API responses
            â””â”€â”€ database_seeds/      # Database seed data
```

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
- **Three-tier testing**: Unit â†’ Integration â†’ E2E
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
- âœ… **Consistent file locations**: All models in appropriate files
- âœ… **Unified enum definitions**: All enums in `schemas/base.py`
- âœ… **Clear repository interfaces**: Complete interface definitions
- âœ… **Comprehensive response models**: All missing models included
- âœ… **Consistent naming**: Repository and service naming aligned
- âœ… **Async throughout**: Full async support from database to endpoints

### **Development Efficiency**
- **Clear module boundaries**: Easy to understand and navigate
- **Dependency injection**: Testable and maintainable architecture
- **Separation of concerns**: Business logic separated from infrastructure
- **Comprehensive testing**: Multiple testing strategies for reliability

### **Operational Characteristics**
- **Standard patterns**: Familiar web application structure
- **Database migrations**: Proper schema evolution support
- **Background processing**: ARQ for scalable task processing
- **Real-time updates**: Redis pub/sub for WebSocket progress
- **External service integration**: Robust integration patterns

This structure resolves all identified discrepancies and provides a solid foundation for async-first implementation.
