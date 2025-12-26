# JiraAuthToken Model - SQLAlchemy Implementation Specification

## 1. Class Name
**JiraAuthToken** - OAuth token storage with encryption for Jira authentication

## 2. Directory Path
`/backend/app/models/auth.py` (new file for authentication-related models)

## 3. Purpose & Responsibilities
- Store encrypted OAuth access and refresh tokens
- Enable session recovery across authentication sessions
- Track token expiration for proactive refresh
- Validate granted scopes for permission checking
- Handle token lifecycle management

## 4. Methods and Properties

### Core Fields (7 total)
```python
jira_user_id: str (primary key)
encrypted_access_token: str  # Application-level encrypted
encrypted_refresh_token: str  # Application-level encrypted
token_expires_at: datetime
granted_scopes: dict  # JSON: Array of granted OAuth scopes
last_refresh_at: Optional[datetime]  # Last successful refresh timestamp
created_at: datetime
```

### Instance Methods
```python
def is_expired(self) -> bool:
    # True if token_expires_at is in the past

def needs_refresh(self, buffer_minutes: int = 5) -> bool:
    # True if token expires within buffer time

def decrypt_access_token(self) -> str:
    # Decrypt and return access token

def decrypt_refresh_token(self) -> str:
    # Decrypt and return refresh token

def update_tokens(self, access_token: str, refresh_token: str, expires_in: int) -> None:
    # Encrypt and store new token pair

@classmethod
def find_expiring_soon(cls, buffer_minutes: int = 60) -> List['JiraAuthToken']:
    # Find tokens that need refresh
```

### Properties
```python
@property
def expires_in_minutes(self) -> Optional[int]:
    # Minutes until token expiration, None if already expired

@property
def is_refresh_needed(self) -> bool:
    # True if token should be refreshed (within 5-minute buffer)

@property
def days_since_created(self) -> float:
    # How many days ago this token was created
```

## 5. Dependencies/Imports
```python
from sqlalchemy import Column, String, DateTime, Index
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime, timedelta
from typing import List, Optional
from app.core.security import encrypt_token, decrypt_token  # Our encryption utilities
```

## 6. Database Integration

### Table Definition
```python
__tablename__ = "jira_auth_tokens"
__table_args__ = (
    Index('idx_jira_auth_tokens_expires_at', 'token_expires_at'),
)
```

### Primary Key
```python
jira_user_id = Column(String(255), primary_key=True)
```

### Transaction Strategy
- Participates in repository-managed transactions
- Updated during token refresh operations
- Independent cleanup based on token expiration (not tied to session cleanup)
- No cascading relationships - tokens survive session deletions

### Token Cleanup Strategy
- Cleanup based on actual token expiration dates
- Independent of 7-day session cleanup policy
- Tokens may live for weeks/months to enable session recovery
- Cleanup job removes tokens expired beyond grace period

## 7. Logging Events

### Token Lifecycle
- **INFO**: Token creation, refresh, and expiration events with user context
- **DEBUG**: Token expiration timing and refresh scheduling
- **AUDIT**: Token refresh attempts, success/failure with full context

### Specific Logging
- **INFO**: `OAuth tokens stored for user {jira_user_id}, expires at {token_expires_at}`
- **INFO**: `OAuth tokens refreshed for user {jira_user_id}, new expiration: {token_expires_at}`
- **WARNING**: `OAuth token refresh failed for user {jira_user_id}: {error_message}`
- **AUDIT**: Full token refresh events with request correlation and error details

## 8. Error Handling

### Error Categories
- **user_fixable**: Token expiration requiring re-authentication
- **admin_required**: OAuth configuration issues, encryption key problems
- **temporary**: Network timeouts during refresh, Jira service unavailable

### Specific Error Patterns
```python
# Token expiration
if self.is_expired():
    raise TokenExpiredError(
        message="OAuth token has expired",
        category="user_fixable"  # User needs to re-authenticate
    )

# Encryption/decryption failures
try:
    access_token = decrypt_token(self.encrypted_access_token)
except DecryptionError as e:
    raise TokenValidationError(
        message="Unable to decrypt access token",
        category="admin_required"  # Likely encryption key issue
    )

# Refresh failures
if refresh_response.status_code == 400:
    raise TokenRefreshError(
        message="Invalid refresh token",
        category="user_fixable"  # Force re-authentication
    )
```

## Key Design Decisions

### User ID as Primary Key
- Uses jira_user_id as primary key for simple 1:1 relationship
- One token record per Jira user across all sessions
- Enables session recovery by linking sessions to user tokens

### Application-Level Encryption
- Tokens encrypted before database storage using Fernet encryption
- Encryption utilities handle key management and rotation capability
- Database never stores plaintext OAuth tokens

### Independent Token Lifecycle
- Token cleanup based on actual expiration dates, not session cleanup
- Tokens survive session deletion to enable recovery across multiple sessions
- Long-lived tokens (weeks/months) vs short-lived sessions (7 days)

### Audit Log Integration
- Token refresh events tracked in audit_log table with full context
- No duplicate refresh failure tracking in token model
- Relies on audit logging for refresh pattern analysis and debugging