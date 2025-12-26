# Complete Repository Interface Specifications - Drupal Ticket Generator

## Overview
Comprehensive definition of all repository interfaces with their responsibilities, method signatures, and service dependencies to eliminate naming ambiguity and ensure consistent implementation.

## Repository Interface List

### **1. SessionRepositoryInterface**
**File**: `/backend/app/repositories/interfaces/session_repository.py`  
**Models**: Session, SessionTask, SessionValidation (aggregate repository)

```python
from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from app.schemas.base import SessionStage, SessionStatus, TaskType, TaskStatus, ValidationStatus

class SessionRepositoryInterface(ABC):
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
    
    # Session Task Operations
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
    
    # Session Validation Operations
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
    def flush(self) -> None:
        pass
    
    @abstractmethod
    def commit(self) -> None:
        pass
    
    @abstractmethod
    def rollback(self) -> None:
        pass
```

### **2. UploadRepositoryInterface**
**File**: `/backend/app/repositories/interfaces/upload_repository.py`  
**Models**: UploadedFile

```python
from abc import ABC, abstractmethod
from typing import List, Optional, Dict
from uuid import UUID
from app.schemas.base import ValidationStatus

class UploadRepositoryInterface(ABC):
    # File CRUD
    @abstractmethod
    async def create_file(self, file_data: dict) -> UploadedFile:
        pass
    
    @abstractmethod
    async def get_file_by_id(self, file_id: UUID) -> Optional[UploadedFile]:
        pass
    
    @abstractmethod
    async def get_files_by_session(self, session_id: UUID) -> List[UploadedFile]:
        pass
    
    @abstractmethod
    async def update_file(self, file_id: UUID, updates: dict) -> UploadedFile:
        pass
    
    @abstractmethod
    async def delete_files_by_session(self, session_id: UUID) -> int:
        pass
    
    # Classification Operations
    @abstractmethod
    async def update_classifications(self, classifications: List[dict]) -> List[UploadedFile]:
        pass
    
    @abstractmethod
    async def get_files_by_csv_type(self, session_id: UUID, csv_type: str) -> List[UploadedFile]:
        pass
    
    @abstractmethod
    async def get_unclassified_files(self, session_id: UUID) -> List[UploadedFile]:
        pass
    
    # Validation Operations
    @abstractmethod
    async def mark_file_validated(self, file_id: UUID, is_valid: bool) -> None:
        pass
    
    @abstractmethod
    async def get_validation_summary(self, session_id: UUID) -> dict:
        pass
    
    @abstractmethod
    async def all_files_valid(self, session_id: UUID) -> bool:
        pass
    
    # Content Access
    @abstractmethod
    async def get_parsed_content(self, file_id: UUID) -> dict:
        pass
    
    @abstractmethod
    async def get_total_entity_count(self, session_id: UUID) -> int:
        pass
    
    # Transaction Control
    @abstractmethod
    def flush(self) -> None:
        pass
    
    @abstractmethod
    def commit(self) -> None:
        pass
    
    @abstractmethod
    def rollback(self) -> None:
        pass
```

### **3. TicketRepositoryInterface**
**File**: `/backend/app/repositories/interfaces/ticket_repository.py`  
**Models**: Ticket, TicketDependency, Attachment (aggregate repository)

```python
from abc import ABC, abstractmethod
from typing import List, Optional, Dict
from uuid import UUID

class TicketRepositoryInterface(ABC):
    # Ticket CRUD
    @abstractmethod
    async def create_ticket(self, ticket_data: dict) -> Ticket:
        pass
    
    @abstractmethod
    async def get_ticket_by_id(self, ticket_id: UUID) -> Optional[Ticket]:
        pass
    
    @abstractmethod
    async def get_tickets_by_session(self, session_id: UUID) -> List[Ticket]:
        pass
    
    @abstractmethod
    async def update_ticket(self, ticket_id: UUID, updates: dict) -> Ticket:
        pass
    
    @abstractmethod
    async def delete_tickets_by_session(self, session_id: UUID) -> int:
        pass
    
    # Review Interface Support
    @abstractmethod
    async def get_tickets_by_entity_group(self, session_id: UUID, entity_group: str) -> List[Ticket]:
        pass
    
    @abstractmethod
    async def get_tickets_summary(self, session_id: UUID) -> dict:
        pass
    
    @abstractmethod
    async def update_ticket_order(self, session_id: UUID, order_updates: List[dict]) -> None:
        pass
    
    # Bulk Operations
    @abstractmethod
    async def bulk_assign_tickets(self, ticket_ids: List[UUID], assignments: dict) -> int:
        pass
    
    @abstractmethod
    async def bulk_update_tickets(self, ticket_ids: List[UUID], updates: dict) -> int:
        pass
    
    # Export Support
    @abstractmethod
    async def get_export_ready_tickets(self, session_id: UUID) -> List[Ticket]:
        pass
    
    @abstractmethod
    async def get_tickets_in_dependency_order(self, session_id: UUID) -> List[Ticket]:
        pass
    
    @abstractmethod
    async def mark_ticket_exported(self, ticket_id: UUID, jira_key: str, jira_url: str) -> None:
        pass
    
    # Dependency Operations
    @abstractmethod
    async def create_dependency(self, ticket_id: UUID, depends_on_ticket_id: UUID) -> TicketDependency:
        pass
    
    @abstractmethod
    async def remove_dependency(self, ticket_id: UUID, depends_on_ticket_id: UUID) -> None:
        pass
    
    @abstractmethod
    async def get_dependencies_for_ticket(self, ticket_id: UUID) -> List[UUID]:
        pass
    
    @abstractmethod
    async def get_dependents_for_ticket(self, ticket_id: UUID) -> List[UUID]:
        pass
    
    @abstractmethod
    async def has_circular_dependency(self, ticket_id: UUID, depends_on_id: UUID) -> bool:
        pass
    
    @abstractmethod
    async def get_dependency_graph(self, session_id: UUID) -> dict:
        pass
    
    # Attachment Operations
    @abstractmethod
    async def create_attachment(self, attachment_data: dict) -> Attachment:
        pass
    
    @abstractmethod
    async def get_attachment_by_ticket(self, ticket_id: UUID) -> Optional[Attachment]:
        pass
    
    @abstractmethod
    async def mark_attachment_uploaded(self, attachment_id: UUID, jira_attachment_id: str) -> None:
        pass
    
    @abstractmethod
    async def get_pending_attachments(self, session_id: UUID) -> List[Attachment]:
        pass
    
    # Transaction Control
    @abstractmethod
    def flush(self) -> None:
        pass
    
    @abstractmethod
    def commit(self) -> None:
        pass
    
    @abstractmethod
    def rollback(self) -> None:
        pass
```

### **4. AuthRepositoryInterface**
**File**: `/backend/app/repositories/interfaces/auth_repository.py`  
**Models**: JiraAuthToken, JiraProjectContext (aggregate repository)

```python
from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID
from datetime import datetime

class AuthRepositoryInterface(ABC):
    # Token Management
    @abstractmethod
    async def store_tokens(self, jira_user_id: str, access_token: str, 
                          refresh_token: str, expires_in: int, granted_scopes: List[str]) -> None:
        pass
    
    @abstractmethod
    async def get_tokens(self, jira_user_id: str) -> Optional[JiraAuthToken]:
        pass
    
    @abstractmethod
    async def refresh_tokens(self, jira_user_id: str, new_access_token: str, 
                            new_refresh_token: str, expires_in: int) -> None:
        pass
    
    @abstractmethod
    async def delete_tokens(self, jira_user_id: str) -> None:
        pass
    
    @abstractmethod
    async def find_expiring_tokens(self, buffer_minutes: int = 60) -> List[JiraAuthToken]:
        pass
    
    @abstractmethod
    async def token_needs_refresh(self, jira_user_id: str, buffer_minutes: int = 5) -> bool:
        pass
    
    # Project Context Management
    @abstractmethod
    async def cache_project_context(self, session_id: UUID, project_data: dict) -> JiraProjectContext:
        pass
    
    @abstractmethod
    async def get_project_context(self, session_id: UUID) -> Optional[JiraProjectContext]:
        pass
    
    @abstractmethod
    async def is_project_context_stale(self, session_id: UUID, max_age_hours: int = 24) -> bool:
        pass
    
    @abstractmethod
    async def refresh_project_context(self, session_id: UUID, fresh_data: dict) -> JiraProjectContext:
        pass
    
    # Validation Support
    @abstractmethod
    async def validate_sprint_name(self, session_id: UUID, sprint_name: str) -> bool:
        pass
    
    @abstractmethod
    async def validate_assignee_id(self, session_id: UUID, account_id: str) -> bool:
        pass
    
    @abstractmethod
    async def get_active_sprints(self, session_id: UUID) -> List[dict]:
        pass
    
    @abstractmethod
    async def get_team_members(self, session_id: UUID) -> List[dict]:
        pass
    
    # Cleanup
    @abstractmethod
    async def cleanup_expired_tokens(self, grace_period_days: int = 30) -> int:
        pass
    
    # Transaction Control
    @abstractmethod
    def flush(self) -> None:
        pass
    
    @abstractmethod
    def commit(self) -> None:
        pass
    
    @abstractmethod
    def rollback(self) -> None:
        pass
```

### **5. ErrorRepositoryInterface**
**File**: `/backend/app/repositories/interfaces/error_repository.py`  
**Models**: SessionError, AuditLog (aggregate repository)

```python
from abc import ABC, abstractmethod
from typing import List, Optional, Dict
from uuid import UUID
from datetime import datetime
from app.schemas.base import ErrorCategory, ErrorSeverity, EventCategory, AuditLevel

class ErrorRepositoryInterface(ABC):
    # Session Error Operations
    @abstractmethod
    async def create_error(self, error_data: dict) -> SessionError:
        pass
    
    @abstractmethod
    async def get_errors_by_session(self, session_id: UUID, 
                                   category: Optional[ErrorCategory] = None) -> List[SessionError]:
        pass
    
    @abstractmethod
    async def get_error_by_id(self, error_id: UUID) -> Optional[SessionError]:
        pass
    
    @abstractmethod
    async def has_blocking_errors(self, session_id: UUID) -> bool:
        pass
    
    @abstractmethod
    async def get_errors_by_category(self, session_id: UUID, category: ErrorCategory) -> List[SessionError]:
        pass
    
    @abstractmethod
    async def store_errors_with_pattern_detection(self, session_id: UUID, 
                                                  errors: List[dict]) -> List[SessionError]:
        pass
    
    # Audit Log Operations
    @abstractmethod
    async def log_event(self, event_type: str, category: EventCategory, description: str,
                       session_id: Optional[UUID] = None, jira_user_id: Optional[str] = None,
                       entity_type: Optional[str] = None, entity_id: Optional[str] = None,
                       event_data: Optional[dict] = None, request_id: Optional[str] = None,
                       execution_time_ms: Optional[int] = None) -> AuditLog:
        pass
    
    @abstractmethod
    async def get_session_timeline(self, session_id: UUID) -> List[AuditLog]:
        pass
    
    @abstractmethod
    async def get_user_activity(self, jira_user_id: str, days: int = 30) -> List[AuditLog]:
        pass
    
    @abstractmethod
    async def get_audit_events(self, session_id: Optional[UUID] = None,
                              category: Optional[EventCategory] = None,
                              audit_level: Optional[AuditLevel] = None,
                              start_date: Optional[datetime] = None,
                              end_date: Optional[datetime] = None) -> List[AuditLog]:
        pass
    
    # Cleanup Operations
    @abstractmethod
    async def cleanup_session_errors(self, session_id: UUID) -> int:
        pass
    
    @abstractmethod
    async def cleanup_audit_logs(self, retention_days: int = 90) -> int:
        pass
    
    # Transaction Control
    @abstractmethod
    def flush(self) -> None:
        pass
    
    @abstractmethod
    def commit(self) -> None:
        pass
    
    @abstractmethod
    def rollback(self) -> None:
        pass
```

## Service Dependencies Resolved

### **SessionService Dependencies**
```python
def __init__(self, 
             session_repo: SessionRepositoryInterface, 
             auth_repo: AuthRepositoryInterface,
             jira_service: JiraService):
```

### **UploadService Dependencies**
```python
def __init__(self, 
             upload_repo: UploadRepositoryInterface,
             session_repo: SessionRepositoryInterface, 
             error_repo: ErrorRepositoryInterface,
             csv_registry: CSVTypeRegistry,
             llm_service: LLMService):
```

### **ProcessingService Dependencies**
```python
def __init__(self, 
             session_repo: SessionRepositoryInterface,
             ticket_repo: TicketRepositoryInterface,
             upload_repo: UploadRepositoryInterface,
             error_repo: ErrorRepositoryInterface,
             llm_service: LLMService):
```

### **ReviewService Dependencies**
```python
def __init__(self, 
             ticket_repo: TicketRepositoryInterface,
             session_repo: SessionRepositoryInterface,
             error_repo: ErrorRepositoryInterface,
             jira_service: JiraService):
```

### **ExportService Dependencies**
```python
def __init__(self, 
             session_repo: SessionRepositoryInterface,
             ticket_repo: TicketRepositoryInterface,
             error_repo: ErrorRepositoryInterface,
             jira_service: JiraService):
```

## Repository Implementation Structure

### **SQLAlchemy Implementations**
- `/backend/app/repositories/sqlalchemy/session_repository.py` → `SQLAlchemySessionRepository(SessionRepositoryInterface)`
- `/backend/app/repositories/sqlalchemy/upload_repository.py` → `SQLAlchemyUploadRepository(UploadRepositoryInterface)`
- `/backend/app/repositories/sqlalchemy/ticket_repository.py` → `SQLAlchemyTicketRepository(TicketRepositoryInterface)`
- `/backend/app/repositories/sqlalchemy/auth_repository.py` → `SQLAlchemyAuthRepository(AuthRepositoryInterface)`
- `/backend/app/repositories/sqlalchemy/error_repository.py` → `SQLAlchemyErrorRepository(ErrorRepositoryInterface)`

### **Dependency Injection Configuration**
```python
# /backend/app/api/dependencies/repositories.py
from fastapi import Depends
from sqlalchemy.orm import Session
from app.core.database import get_db_session

def get_session_repository(db: Session = Depends(get_db_session)) -> SessionRepositoryInterface:
    return SQLAlchemySessionRepository(db)

def get_upload_repository(db: Session = Depends(get_db_session)) -> UploadRepositoryInterface:
    return SQLAlchemyUploadRepository(db)

def get_ticket_repository(db: Session = Depends(get_db_session)) -> TicketRepositoryInterface:
    return SQLAlchemyTicketRepository(db)

def get_auth_repository(db: Session = Depends(get_db_session)) -> AuthRepositoryInterface:
    return SQLAlchemyAuthRepository(db)

def get_error_repository(db: Session = Depends(get_db_session)) -> ErrorRepositoryInterface:
    return SQLAlchemyErrorRepository(db)
```

## Key Design Decisions

### **1. Aggregate Repository Pattern**
- **SessionRepository**: Handles Session + SessionTask + SessionValidation together
- **TicketRepository**: Handles Ticket + TicketDependency + Attachment together  
- **AuthRepository**: Handles JiraAuthToken + JiraProjectContext together
- **ErrorRepository**: Handles SessionError + AuditLog together
- **UploadRepository**: Handles UploadedFile (single model)

### **2. Transaction Control Methods**
All repositories include `flush()`, `commit()`, and `rollback()` methods:
- **flush()**: Used by repository methods for immediate database sync
- **commit()**: Used by service methods when business transaction completes
- **rollback()**: Used automatically when exceptions occur

### **3. Async Method Signatures**
All repository methods are async to support:
- Future async database operations
- Consistent patterns across service layer
- Better performance for I/O-bound operations

### **4. Type Hints and Optional Returns**
- Clear return types for better IDE support
- Optional returns for get operations that might not find records
- List returns for query operations

## Naming Consistency Resolution

### **Previous Ambiguities Resolved:**
- ❌ `UploadRepositoryInterface` vs `UploadedFileRepository` → ✅ `UploadRepositoryInterface`
- ❌ `ErrorRepositoryInterface` vs `SessionErrorRepository` → ✅ `ErrorRepositoryInterface`
- ❌ `AuthRepositoryInterface` vs `JiraAuthTokenRepository` → ✅ `AuthRepositoryInterface`

### **Consistent Naming Pattern:**
- Interface names: `{Domain}RepositoryInterface`
- Implementation names: `SQLAlchemy{Domain}Repository`
- Dependency functions: `get_{domain}_repository`

This comprehensive specification eliminates all ambiguity about repository interfaces and provides clear contracts for implementation.