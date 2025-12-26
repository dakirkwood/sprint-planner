# Drupal Ticket Generator

Web application that converts CSV files containing Drupal configuration data into structured Jira tickets using LLM integration. Serves a 9-person development team.

## Tech Stack

- **API**: FastAPI
- **Database**: PostgreSQL with SQLAlchemy 2.0 (async via asyncpg)
- **Task Queue**: ARQ with Redis
- **Real-time**: WebSocket for progress updates
- **Testing**: pytest (TDD approach)

## Key Conventions

- **Async-everywhere**: All database operations use async patterns with asyncpg driver
- **Layer separation**: Repository → Service → API (strict boundaries)
- **Dependency injection**: FastAPI's `Depends()` throughout
- **Error categorization**: "Who can fix it" system (user-fixable vs system errors)

## Documentation

All specs are in `docs/`:

| Path | Contents |
|------|----------|
| `docs/architecture/` | System patterns, DI lifecycle, task infrastructure |
| `docs/models/` | Database model specifications (11 models) |
| `docs/services/` | Service layer architecture |
| `docs/api/` | FastAPI endpoint specifications |
| `docs/schemas/` | Pydantic schema definitions (.py files) |
| `docs/implementation/` | Phase 1-6 implementation guides with test structures |
| `docs/decisions/` | Architectural decision records |

**Start here:**
- `docs/drupal_ticket_generator_prd.md` — Business context
- `docs/architecture/Comprehensive_Updated_Directory_Structure_updated.md` — Project layout
- `docs/implementation/phase_1_foundation_infrastructure.md` — First implementation phase

## Sample Data

Test and development data in `docs/sample_data/`:

```
sample_data/
├── test_cases/
│   ├── UWEC_CustomViewsDisplays_BROKEN.csv      # Intentionally malformed for validation testing
│   └── UWEC_ResponsiveImageStyles_BROKEN.csv   # Intentionally malformed for validation testing
└── uwec_complete/
    └── *.csv                                    # Real Drupal config data from previous project
```

- **test_cases/**: Broken CSVs for testing validation and error handling
- **uwec_complete/**: Valid production data for end-to-end testing

## Workflow Stages

1. **Upload** — CSV file upload and storage
2. **Validation** — Schema validation, error detection
3. **Processing** — LLM generates tickets from CSV data
4. **Review** — Human review/edit of generated tickets
5. **Export** — Push approved tickets to Jira via OAuth

## Commands

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=app --cov-report=term-missing

# Start dev server
uvicorn app.main:app --reload

# Start ARQ worker
arq app.workers.WorkerSettings
```

## Implementation Approach

- TDD: Write tests first, then implementation
- Follow phase documents in order (phase_1 → phase_6)
- Each phase has success criteria that must pass before moving on
