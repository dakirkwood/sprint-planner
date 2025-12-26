# Updated Authentication Flow Specification - Drupal Ticket Generator

## Overview
This document defines the updated authentication flow specification for the simplified, database-driven Drupal Ticket Generator architecture, replacing the complex session file management with standard database patterns.

## Core Authentication Principles
- **Early Authentication**: Users must authenticate before accessing any functionality
- **Database-Driven Session Management**: Standard database session tracking with user linking
- **Single Jira Instance**: Hardcoded for `https://ecitizen.atlassian.net`
- **Fail-Fast Permission Validation**: Verify permissions immediately after OAuth success
- **Simple Session Recovery**: Database queries by jira_user_id for incomplete sessions

## 1. OAuth 2.0 Flow Design

### Flow Type and Configuration
- **Flow**: OAuth 2.0 Authorization Code Flow with PKCE
- **Target Instance**: `https://ecitizen.atlassian.net` (hardcoded)
- **Required Scopes**: 
  - `write:jira-work` - Create and modify issues
  - `read:jira-work` - Read project and issue data  
  - `read:jira-user` - Validate user permissions
- **PKCE Implementation**: Required for security best practices
- **State Parameter**: Simple random value for CSRF protection
- **Redirect Handling**: Full-page redirect (required - Jira blocks iframes)

### Authentication Timing and Session Creation
- **Early Authentication**: Immediate redirect on application start
- **Permission Validation**: Test specific permissions immediately after OAuth success
- **Session Creation**: Create database session record only after permission validation passes
- **Workflow Integration**: Auth → Permission Validation → Session Creation → App Access

## 2. Database-Driven Session Management

### Token Storage Structure
```sql
-- jira_auth_tokens table
CREATE TABLE jira_auth_tokens (
    jira_user_id VARCHAR(255) PRIMARY KEY,
    encrypted_access_token TEXT NOT NULL,
    encrypted_refresh_token TEXT NOT NULL,
    token_expires_at TIMESTAMP NOT NULL,
    granted_scopes JSONB,
    last_refresh_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

### Session Management Strategy
- **Database Sessions**: Records in `sessions` table linked by `jira_user_id`
- **Token Persistence**: Tokens survive across sessions for recovery in `jira_auth_tokens` table
- **Session Lifecycle**: 7-day cleanup for incomplete sessions (aligned with data retention)
- **Token Cleanup**: Separate cleanup based on token expiration + grace period

### Token Management
- **Refresh Strategy**: Proactive refresh (check expiry before each Jira API call)
- **Re-authentication**: Modal overlay that preserves page state for expired tokens
- **Token Classification**: Distinguish between "token expired" vs "network problems"
- **Storage Encryption**: Fernet symmetric encryption for all stored tokens

## 3. Authentication Error Handling

### Error Classification (Aligned with "Who Can Fix It" Strategy)
```python
AUTH_ERRORS = {
    'user_fixable': [
        'oauth_permissions_denied',      # User declined OAuth - redirect to retry
        'invalid_jira_project_key',      # User entered wrong project key
        'insufficient_permissions'       # User lacks create ticket permission
    ],
    'admin_required': [
        'oauth_client_misconfigured',    # Invalid client credentials  
        'jira_instance_unreachable',     # Network/infrastructure issues
        'scope_validation_failed'        # Required scopes not available
    ],
    'temporary': [
        'oauth_service_unavailable',     # Jira OAuth temporarily down
        'token_refresh_failed',          # Network timeout during refresh
        'rate_limit_exceeded'            # OAuth API rate limit
    ]
}
```

### Error Handling Strategy
- **Authentication First**: Authentication errors must be resolved before session recovery
- **OAuth Denial**: Simple redirect back to OAuth flow (no explanation page)
- **Token Refresh Failures**: Classify error type and only show re-auth overlay when needed
- **Permission Validation**: Validate immediately after OAuth success, before any user investment

### Token Refresh Error Classification
```python
async def refresh_token_with_error_classification(refresh_token):
    try:
        response = await oauth_client.refresh_token(refresh_token)
        return response
    except OAuthError as e:
        if e.error in ['invalid_grant', 'invalid_request']:
            # Show re-auth overlay immediately
            raise TokenExpiredError("Re-authentication required")
        else:
            # Retry 2-3 times, then show service error
            raise TemporaryAuthError("OAuth service unavailable")
    except (ConnectionError, TimeoutError, DNSError):
        # Retry 2-3 times, then show network error
        raise TemporaryAuthError("Network connectivity issue")
```

## 4. Authentication API Endpoints

### Core OAuth Flow Endpoints
```python
GET  /api/auth/login                    # Initiate OAuth flow (returns redirect URL)
GET  /api/auth/callback                 # Handle OAuth callback from Jira
POST /api/auth/logout                   # Clear tokens and session with active revocation
GET  /api/auth/status                   # Current auth status + session info

# Session Recovery
GET  /api/auth/check-recovery          # Check for incomplete sessions by jira_user_id
POST /api/auth/restore-session/{session_id}  # Apply current tokens to existing session
```

### Auth Status Endpoint Response
```json
{
    "authenticated": true,
    "user_info": {
        "jira_user_id": "user123",
        "display_name": "John Doe", 
        "email": "john@company.com"
    },
    "current_session": {
        "session_id": "uuid",
        "stage": "review",
        "site_name": "My Project"
    },
    "recovery_available": true,
    "incomplete_sessions": [
        {
            "session_id": "uuid", 
            "site_name": "Previous Project",
            "stage": "processing",
            "created_at": "2024-01-15T10:30:00Z"
        }
    ],
    "permissions": {
        "can_create_tickets": true,
        "validated_at": "2024-01-15T10:30:00Z"
    }
}
```

### Frontend Integration Strategy
- **Full-Page Redirects**: Required due to Jira iframe blocking
- **Routing Logic**: Frontend routes based on `current_session.stage`
- **Recovery UX**: Simple "Continue previous session?" prompt
- **State Preservation**: Re-auth modal preserves current page state during token refresh

## 5. Session Recovery Mechanism

### Recovery Process
```python
# Simplified database-driven recovery
1. User re-authenticates → new tokens generated
2. Query sessions table for incomplete sessions by jira_user_id
3. Present "Continue previous session?" prompt if incomplete sessions found
4. Apply new tokens to selected existing session
5. Resume workflow from current stage
```

### Recovery Integration
- **Recovery Linking**: Simple database query by jira_user_id
- **Token Application**: Update jira_auth_tokens table with new tokens
- **Session Continuation**: Resume from stored session.current_stage
- **No Complex Coordination**: Standard database operations only

## 6. Security Implementation

### PKCE Implementation
```python
# Standard PKCE flow
1. Generate code_verifier (random string)
2. Create code_challenge = base64url(sha256(code_verifier))
3. Store code_verifier in encrypted cookie (10-minute expiration)
4. Include code_challenge in OAuth authorization URL
5. Include code_verifier in token exchange request
```

### Security Measures
- **PKCE Storage**: Encrypted cookie with 10-minute expiration
- **State Parameter**: Simple random value (32 bytes) for CSRF protection
- **Token Encryption**: Fernet symmetric encryption for database storage
- **Database Security**: TLS connections + audit logging for token table access
- **Active Token Revocation**: Revoke tokens with Jira + database cleanup on logout

### Cookie Security Configuration
```python
# PKCE verifier storage
response.set_cookie(
    "oauth_verifier", 
    encrypted_data, 
    max_age=600,        # 10 minutes
    secure=True,        # HTTPS only
    httponly=True,      # No JavaScript access
    samesite="Lax"      # CSRF protection
)
```

## Implementation Benefits

### Simplified Architecture
- **Standard Database Patterns**: Familiar web application session management
- **~80% Less Custom Code**: Database operations vs complex session file coordination
- **ACID Compliance**: Consistent authentication state across workflow stages
- **Standard Backup/Recovery**: Database backup includes all authentication state

### Enhanced Security
- **Production-Grade Encryption**: Fernet encryption for sensitive token storage
- **Proper OAuth Implementation**: PKCE + state parameter for comprehensive security
- **Database-Level Security**: TLS connections + audit logging
- **Active Token Management**: Proper token revocation on logout

### Improved User Experience
- **Seamless Recovery**: Simple database queries enable robust session recovery
- **Proactive Token Management**: Users never see authentication failures
- **Preserved State**: Re-authentication preserves current page state
- **Early Validation**: Permission checking prevents wasted user effort

## Success Criteria
- ✅ Users authenticate seamlessly with Jira before starting workflow
- ✅ Token refresh happens transparently without user interruption
- ✅ Session recovery works reliably across browser sessions and server restarts
- ✅ Authentication errors provide clear guidance and appropriate recovery paths
- ✅ Permission validation prevents workflow progression with insufficient access
- ✅ Full-page redirect flow works reliably across all browsers and devices
- ✅ Early authentication prevents wasted user effort on upload/validation
- ✅ Database-driven approach provides standard operational characteristics