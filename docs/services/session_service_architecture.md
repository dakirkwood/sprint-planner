# SessionService Architecture Decisions

## Method Signatures

```python
class SessionService:
    def __init__(self, 
                 session_repo: SessionRepositoryInterface, 
                 auth_repo: AuthRepositoryInterface,
                 jira_service: JiraService):

    # Session Creation & Setup (Stage: site_info_collection → upload)
    async def create_session(self, request: SessionCreateRequest, jira_user_id: str) -> SessionResponse
    
    # Session Recovery 
    async def find_recoverable_sessions(self, jira_user_id: str) -> List[IncompleteSessionInfo]
    async def recover_session(self, session_id: UUID, jira_user_id: str) -> SessionResponse
    
    # Session Status & Retrieval
    async def get_session(self, session_id: UUID) -> SessionResponse
    async def get_session_status(self, session_id: UUID) -> SessionStatus  # Just the enum
    
    # Stage Transitions (enforces sequential progression)
    async def transition_to_upload(self, session_id: UUID) -> None
    async def transition_to_processing(self, session_id: UUID) -> None  
    async def transition_to_review(self, session_id: UUID) -> None
    async def transition_to_export(self, session_id: UUID) -> None
    async def mark_completed(self, session_id: UUID) -> None
    
    # Administrative
    async def cleanup_expired_sessions(self) -> int  # Background job, returns count deleted
```

## Key Decisions Made

### 1. Explicit Stage Transition Methods
- **Decision**: Use explicit methods (`transition_to_upload()`, etc.) rather than generic `transition_to_stage(session_id, new_stage)`
- **Rationale**: Enables business rule enforcement per transition, clearer API contracts

### 2. Direct JiraService Dependency
- **Decision**: SessionService directly depends on JiraService for project validation during session creation
- **Rationale**: Session creation requires immediate Jira project validation and context caching

### 3. No Additional Error Handling Methods
- **Decision**: Rely on try/catch and existing error categorization system, no special error handling methods
- **Rationale**: Clean slate recovery approach eliminates need for partial state management, stage-specific failures handled by appropriate services

## Dependencies
- **SessionRepositoryInterface**: Core session data operations
- **AuthRepositoryInterface**: OAuth token and project context operations  
- **JiraService**: Project validation and context caching during session creation