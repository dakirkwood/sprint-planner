# Drupal Ticket Generator - Documentation

A web application that converts CSV files containing Drupal configuration data into structured Jira tickets using LLM integration.

## Documentation Structure

```
docs/
├── drupal_ticket_generator_prd.md    # Product Requirements Document
├── architecture/                      # System architecture & patterns
├── models/                           # Database model specifications
├── services/                         # Service layer architecture
├── api/                              # API endpoint specifications
├── schemas/                          # Pydantic schema definitions (Python)
├── implementation/                   # Phase-by-phase implementation guides
└── decisions/                        # Architectural decision records
```

## Quick Navigation

### Product Requirements
- [PRD](drupal_ticket_generator_prd.md) - Business context, user personas, success metrics

### Architecture
| Document | Description |
|----------|-------------|
| [Directory Structure](architecture/Comprehensive_Updated_Directory_Structure_updated.md) | Project folder organization |
| [Background Tasks](architecture/background_task_infrastructure.md) | ARQ + Redis task processing |
| [Repository Patterns](architecture/repository_patterns_decisions_updated.md) | Data access layer patterns |
| [DI Lifecycle](architecture/fastapi_di_lifecycle_decisions_updated.md) | Dependency injection design |
| [SQLAlchemy Relationships](architecture/SQLAlchemy_Relationship_Bidirectional_Consistency_Audit_updated.md) | ORM relationship audit |
| [Task Management](architecture/Task_Management_Architecture_Standardization.md) | Task state management |
| [Repository Interfaces](architecture/Complete_Repository_Interface_Specifications.md) | Repository method signatures |
| [CSV Type Registry](architecture/CSV_Type_Registry_Structure_Specification.md) | CSV type handling |
| [Response Models](architecture/Missing_Response_Models_-_Complete_Specifications.md) | API response schemas |
| [Auth Flow](architecture/updated_auth_flow_spec.md) | Authentication workflow |
| [Error Standards](architecture/updated_error_response_standards.md) | Error response patterns |

### Database Models
| Model | Description |
|-------|-------------|
| [Session](models/session_model_spec.md) | User session management |
| [Session Task](models/session_task_model_spec.md) | Background task tracking |
| [Session Error](models/session_error_model_spec.md) | Error logging |
| [Session Validation](models/session_validation_model_spec_updated.md) | Validation results |
| [Uploaded File](models/uploaded_file_model_spec_updated.md) | File upload tracking |
| [Attachment](models/attachment_model_spec.md) | File attachments |
| [Ticket](models/ticket_model_spec_updated.md) | Generated tickets |
| [Ticket Dependency](models/ticket_dependency_model_spec.md) | Ticket relationships |
| [Jira Auth Token](models/jira_auth_token_model_spec.md) | OAuth token storage |
| [Jira Project Context](models/jira_project_context_model_spec.md) | Jira project mapping |
| [Audit Log](models/audit_log_model_spec.md) | Activity logging |

### Services
| Service | Description |
|---------|-------------|
| [Session Service](services/session_service_architecture.md) | Session lifecycle |
| [Upload Service](services/upload_service_architecture.md) | File upload handling |
| [Processing Service](services/processing_service_architecture_updated.md) | LLM ticket generation |
| [Review Service](services/review_service_architecture_updated.md) | Human review workflow |
| [Export Service](services/export_service_architecture_updated.md) | Jira export |
| [LLM Service](services/LLM_Service_Scope_and_Interface_Specification.md) | LLM integration |

### API Endpoints
| Specification | Description |
|---------------|-------------|
| [Upload Endpoints](api/fastapi_upload_endpoints.md) | File upload API |
| [Processing Endpoints](api/fastapi_processing_endpoints.md) | Processing API |
| [Jira Integration](api/fastapi_jira_integration_endpoints.md) | Jira OAuth & export |

### Pydantic Schemas
| File | Description |
|------|-------------|
| [Base Schemas](schemas/base_schemas_models_updated.py) | Common base models |
| [Auth Schemas](schemas/auth_schemas_models_updated.py) | Authentication models |
| [Upload Schemas](schemas/upload_schemas_models.py) | Upload request/response |

### Implementation Phases
| Phase | Description |
|-------|-------------|
| [Phase 1](implementation/phase_1_foundation_infrastructure.md) | Foundation & Infrastructure |
| [Phase 2](implementation/phase_2_authentication_session.md) | Authentication & Session |
| [Phase 3](implementation/phase_3_file_upload_validation.md) | File Upload & Validation |
| [Phase 4](implementation/phase_4_processing_ticket_generation.md) | Processing & Ticket Generation |
| [Phase 5](implementation/phase_5_review_stage.md) | Review Stage |
| [Phase 6](implementation/phase_6_jira_export.md) | Jira Export |

### Decision Records
| Document | Description |
|----------|-------------|
| [Discrepancy Resolutions](decisions/discrepancy_resolution_decisions.md) | Cross-document conflict resolutions |
| [Documentation Review](decisions/documentation_review_decisions.md) | Review session outcomes |
| [Review Session](decisions/documentation_review_session_decisions.md) | Additional review decisions |
| [Missing Implementations](decisions/missing_implementation_decisions.md) | Gap analysis |

## Technology Stack

- **API Framework**: FastAPI
- **Database**: PostgreSQL with SQLAlchemy 2.0 (async)
- **Task Queue**: ARQ with Redis
- **Real-time**: WebSocket for progress updates
- **Testing**: pytest with TDD approach

## Getting Started

1. Start with the [PRD](drupal_ticket_generator_prd.md) for business context
2. Review [Directory Structure](architecture/Comprehensive_Updated_Directory_Structure_updated.md) for project layout
3. Follow implementation phases in order, starting with [Phase 1](implementation/phase_1_foundation_infrastructure.md)
