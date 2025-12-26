# JiraProjectContext Model - SQLAlchemy Implementation Specification

## 1. Class Name
**JiraProjectContext** - Cached Jira project metadata for session optimization

## 2. Directory Path
`/backend/app/models/auth.py` (same file as JiraAuthToken for related Jira integration)

## 3. Purpose & Responsibilities
- Cache Jira project metadata (sprints, team members, permissions)
- Optimize review stage dropdowns and validation
- Enable offline validation of user selections
- Track cache freshness for refresh decisions
- Store project-specific permission context

## 4. Methods and Properties

### Core Fields (8 total)
```python
session_id: UUID (primary key, foreign key to sessions)
project_key: str
project_name: str
can_create_tickets: bool = False
can_assign_tickets: bool = False
available_sprints: dict  # JSON: [{"name": "Sprint 1", "state": "active"}, ...]
team_members: dict  # JSON: [{"account_id": "123", "display_name": "John Doe", "email": "...", "active": true}, ...]
cached_at: datetime
```

### Instance Methods
```python
def is_stale(self, max_age_hours: int = 24) -> bool:
    # True if cache is older than specified hours

def get_active_sprints(self) -> List[dict]:
    # Filter sprints by "active" state

def get_team_member_by_id(self, account_id: str) -> Optional[dict]:
    # Find team member by Jira account ID

def validate_sprint_name(self, sprint_name: str) -> bool:
    # True if sprint name exists in cached data

def validate_assignee_id(self, account_id: str) -> bool:
    # True if account_id is valid team member

@classmethod 
def refresh_for_session(cls, session_id: UUID, project_data: dict) -> 'JiraProjectContext':
    # Replace entire cache with fresh project data
```

### Properties
```python
@property
def cache_age_hours(self) -> float:
    # How many hours old the cache is

@property
def has_active_sprints(self) -> bool:
    # True if any sprints are in "active" state

@property
def active_team_member_count(self) -> int:
    # Count of team members with active=true
```

## 5. Dependencies/Imports
```python
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime, timedelta
from typing import List, Dict, Optional
```

## 6. Database Integration

### Table Definition
```python
__tablename__ = "jira_project_context"
# No additional indexes needed - primary key covers session lookups
```

### Primary Key / Foreign Key
```python
session_id = Column(UUID(as_uuid=True), ForeignKey('sessions.id', ondelete='CASCADE'), primary_key=True)
```

### Transaction Strategy
- Participates in repository-managed transactions
- Created/updated when session transitions to review stage
- Cascading delete with parent session (no independent value)

## 7. Logging Events

### Cache Lifecycle
- **INFO**: Project context caching and refresh events
- **DEBUG**: Cache hit/miss patterns, data freshness checks
- **AUDIT**: Permission validation results

### Specific Logging
- **INFO**: `Project context cached for session {session_id}: {project_key} ({team_member_count} members, {sprint_count} sprints)`
- **DEBUG**: `Cache age: {cache_age_hours}h, active sprints: {active_sprint_count}`
- **WARNING**: `Stale project context detected for session {session_id}, age: {cache_age_hours}h`

## 8. Error Handling

### Error Categories
- **user_fixable**: Invalid project selections, assignment validation failures
- **admin_required**: Jira API issues, project access problems
- **temporary**: Network timeouts during project metadata fetch

### Specific Error Patterns
```python
# Stale cache detection
if self.is_stale(max_age_hours=24):
    raise CacheStaleError(
        message="Project context cache is stale",
        category="temporary"  # Refresh will resolve
    )

# Assignment validation
if not self.validate_assignee_id(account_id):
    raise AssignmentValidationError(
        message=f"Assignee '{account_id}' not found in project team",
        category="user_fixable"
    )
```

## Key Design Decisions

### Session ID as Primary Key
- Uses session_id as primary key for true 1:1 relationship with sessions
- Each session works with exactly one Jira project
- Simplifies queries and ensures exactly one project context per session
- Cascading delete maintains data integrity

### Complete Record Replacement
- Refresh strategy replaces entire record rather than partial updates
- Simpler than tracking individual field changes
- Ensures cache consistency and reduces complexity
- Adequate refresh frequency for project metadata

### JSON Storage for Lists
- Sprint and team member data stored as JSON arrays
- Flexible structure accommodates varying Jira project configurations
- Sufficient for validation and dropdown population
- Avoids complexity of normalized sprint/member tables

### Simple Permission Model
- Boolean flags for essential permissions only
- Covers core use cases without overcomplicating model
- `can_create_tickets` - Essential for export functionality
- `can_assign_tickets` - Determines assignee dropdown availability