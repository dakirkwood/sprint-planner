# Updated Error Response Standards - Drupal Ticket Generator

## Overview
Updated error response standards for the simplified, database-driven Drupal Ticket Generator architecture. Focus on "who can fix it" error categorization with streamlined handling patterns.

## Core Principles
- **User-focused error categorization** based on who can resolve the issue
- **Database-driven tracking** using session IDs instead of complex correlation
- **Fail-fast with complete feedback** - single-pass processing with comprehensive error reporting
- **Context-aware error handling** in business logic rather than automatic classification

## 1. Standardized Error Response Format

```python
class StandardErrorResponse(BaseModel):
    # Core Error Information
    error_id: str                    # Unique error instance ID
    session_id: str                  # Database session ID for tracking
    error_code: str                  # Application-specific error code
    error_category: str              # 'user_fixable', 'admin_required', 'temporary'
    severity: str                    # 'blocking', 'warning', 'info'
    
    # User-Facing Information
    user_message: str                # User-friendly error message
    recovery_actions: List[str]      # Specific steps user can take
    
    # Context & Technical Details
    operation_stage: str             # 'upload', 'processing', 'review', 'jira_export'
    component: str                   # 'CSVProcessor', 'TicketGenerator', 'JiraClient'
    technical_details: Optional[str] # Developer debugging information
    
    # Tracking
    timestamp: datetime              # When error occurred
    related_file_id: Optional[str]   # UUID of uploaded file if relevant
    related_ticket_id: Optional[str] # UUID of ticket if relevant
```

**Key Changes from Original:**
- Simplified error categories focusing on "who can fix it"
- Database session tracking instead of complex correlation IDs
- Removed agent-specific fields (circuit breakers, retry attempts)
- Streamlined context tracking

## 2. HTTP Status Code Mapping Strategy

```python
# Default category mapping
ERROR_CATEGORY_TO_STATUS = {
    'user_fixable': 422,        # User can fix the data/input
    'admin_required': 403,      # Admin intervention needed
    'temporary': 503            # Try again later
}

# Semantic overrides for standard HTTP behaviors
SEMANTIC_OVERRIDES = {
    'authentication_required': 401,  # Triggers auth flows
    'jira_project_not_found': 404,  # "Thing doesn't exist" vs "no permission"
    'llm_rate_limit_exceeded': 429  # Standard rate limit response
}
```

**Decision Rationale:**
- Category-based approach for consistent frontend handling
- Semantic overrides for standard HTTP client expectations
- CSV validation always uses 422 (FastAPI standard)

## 3. User-Friendly Error Messages and Guidance

```python
class ErrorMessageGenerator:
    CATEGORY_TEMPLATES = {
        'user_fixable': {
            'message_format': "There's an issue with {context} that you can fix.",
            'guidance_intro': "To resolve this:",
            'default_actions': ["Review the highlighted issue", "Make corrections", "Try again"]
        },
        'admin_required': {
            'message_format': "This requires administrator assistance: {context}",
            'guidance_intro': "Please contact your administrator to:",
            'default_actions': ["Contact system administrator", "Reference error ID: {error_id}"]
        },
        'temporary': {
            'message_format': "A temporary service issue occurred: {context}",
            'guidance_intro': "This usually resolves automatically:",
            'default_actions': ["Wait a few minutes and try again", "Check service status if issue persists"]
        }
    }
```

**Design Decisions:**
- Category-driven messaging for consistent user experience
- Self-contained error messages without external documentation links
- Actionable guidance focused on what users can actually do

## 4. Error Context and Correlation Tracking

```python
class ErrorContext(BaseModel):
    # Core tracking
    session_id: str                     # Database session ID
    operation_stage: str                # 'upload', 'processing', 'review', 'jira_export'
    
    # Request context
    endpoint: str                       # Which API endpoint failed
    user_id: str                        # Jira user ID
    
    # Related entities (for debugging)
    affected_file_id: Optional[str]     # UUID from uploaded_files table
    affected_ticket_id: Optional[str]   # UUID from tickets table
    
    # Simple operation context
    entity_group: Optional[str]         # 'Content', 'Media', 'Views', etc.
    csv_source_info: Optional[str]      # "bundles.csv rows 3-5" for debugging
```

**CSV Source Info Examples:**
- `"bundles.csv row 3"` - specific row issue
- `"fields.csv rows 12-15"` - multiple related rows
- `"bundles.csv + fields.csv"` - relationship issues between files

## 5. Error Response Consistency Across Endpoints

```python
class ProcessingError(Exception):
    """Base exception for all application errors"""
    def __init__(self, message: str, category: str, 
                 recovery_actions: List[str] = None,
                 file_id: str = None, ticket_id: str = None):
        self.message = message
        self.category = category  # 'user_fixable', 'admin_required', 'temporary'
        self.recovery_actions = recovery_actions or []
        self.file_id = file_id
        self.ticket_id = ticket_id
        super().__init__(message)

def handle_processing_errors(operation_stage: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except ProcessingError:
                raise  # Re-raise with context
            except Exception as e:
                raise ProcessingError(
                    message=f"Unexpected error during {operation_stage}",
                    category="admin_required",
                    recovery_actions=["Contact system administrator", f"Reference error in {operation_stage}"]
                ) from e
        return wrapper
    return decorator
```

**Error Classification Strategy:**
- **Case-by-case in business logic** rather than automatic classification
- More contextual messages and recovery actions
- Better user experience through specific, actionable guidance

**Example Business Logic Implementation:**
```python
try:
    self.save_bundle_to_database(bundle_data)
except IntegrityError as e:
    if "unique_constraint" in str(e):
        raise ProcessingError(
            message=f"Bundle name '{bundle_data.name}' already exists in row {row_num}",
            category="user_fixable",
            recovery_actions=["Choose a different bundle name", "Check for duplicates in your CSV"],
            file_id=csv_file_id
        )
    else:
        raise ProcessingError(
            message="Database configuration issue",
            category="admin_required",
            recovery_actions=["Contact system administrator"]
        )
```

## Database Integration

### Error Storage
All errors are stored in the `session_errors` table with the following structure:

```sql
CREATE TABLE session_errors (
    id UUID PRIMARY KEY,
    session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
    
    -- Error classification  
    error_category VARCHAR(50) NOT NULL,    -- 'user_fixable', 'admin_required', 'temporary'
    severity VARCHAR(20) NOT NULL,          -- 'blocking', 'warning', 'info'
    
    -- Context
    operation_stage VARCHAR(50),            -- 'upload', 'processing', 'review', 'jira_export'
    related_file_id UUID REFERENCES uploaded_files(id),
    related_ticket_id UUID REFERENCES tickets(id),
    
    -- User-facing information
    user_message TEXT NOT NULL,
    recovery_actions JSONB,                 -- Array of action steps
    
    -- Technical details  
    technical_details JSONB,               -- Stack traces, API responses, etc.
    error_code VARCHAR(100),               -- Application-specific error codes
    
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

### Error Retrieval
Frontend can query errors by session and category to provide appropriate UI treatment:

```python
# Get all user-fixable errors for display
user_errors = session.query(SessionError).filter(
    SessionError.session_id == session_id,
    SessionError.error_category == 'user_fixable'
).all()

# Get blocking errors that prevent progression
blocking_errors = session.query(SessionError).filter(
    SessionError.session_id == session_id,
    SessionError.severity == 'blocking'
).all()
```

## Implementation Benefits
- **Simplified codebase** - ~70% reduction in error handling complexity
- **Better user experience** - Context-aware messages with actionable guidance
- **Consistent frontend handling** - Category-based error treatment
- **Effective debugging** - Precise error location with CSV source tracking
- **Database integration** - Standard web app error tracking patterns

## Success Criteria
✅ All errors categorized by "who can fix them" for appropriate user treatment  
✅ Database session tracking enables robust error attribution and debugging  
✅ Business logic provides context-aware error messages and recovery actions  
✅ Frontend can handle errors consistently based on category classification  
✅ Unexpected errors gracefully convert to user-friendly admin-required messages  
✅ CSV source tracking provides precise guidance for data correction issues

## Usage Examples

### CSV Validation Error
```python
# User uploads invalid CSV
raise ProcessingError(
    message="Bundle machine name 'invalid name' contains spaces in row 5",
    category="user_fixable", 
    recovery_actions=[
        "Change machine name to use underscores instead of spaces",
        "Machine names must contain only letters, numbers, and underscores"
    ],
    file_id=uploaded_file.id
)
```

### LLM Service Error
```python
# LLM API quota exceeded
raise ProcessingError(
    message="AI service quota exceeded", 
    category="temporary",
    recovery_actions=[
        "Wait 15 minutes for quota reset",
        "Contact administrator if issue persists"
    ]
)
```

### Jira Integration Error
```python
# Project doesn't exist
raise ProcessingError(
    message="Jira project 'INVALID' not found",
    category="user_fixable",
    recovery_actions=[
        "Check the project key spelling",
        "Verify the project exists in Jira", 
        "Ensure you have access to the project"
    ]
)
```

### Database Error
```python
# Connection failure
raise ProcessingError(
    message="Unable to save session data",
    category="admin_required", 
    recovery_actions=[
        "Contact system administrator",
        "Database connection issue detected"
    ]
)
```