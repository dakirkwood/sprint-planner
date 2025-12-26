# Phase 2: Authentication & Session Management

## Overview
Implement OAuth authentication flow with Jira, session creation and management, and the foundational SessionService. This phase establishes user identity and project context that all subsequent operations depend on.

**Estimated Effort**: 2-3 days  
**Prerequisites**: Phase 1 complete (models, repositories, infrastructure)  
**Deliverables**: Working OAuth flow, session CRUD, JiraService (auth subset), SessionService

---

## Test-Driven Development Approach

### TDD Workflow for This Phase
1. Write unit tests for token encryption/decryption
2. Write unit tests for SessionService with mocked dependencies
3. Write integration tests for OAuth callback flow
4. Write API endpoint tests for auth routes
5. Implement code to make tests pass
6. Verify end-to-end OAuth flow manually

---

## Part 1: Test Structure

### 1.1 Phase 2 Test Directory

```
tests/
â”œâ”€â”€ conftest.py                    # Add auth-specific fixtures
â”œâ”€â”€ mocks/
â”‚   â”œâ”€â”€ __init__.py
â”‚   â””â”€â”€ jira_service.py            # Mock Jira API responses
â”œâ”€â”€ phase_2_auth/
â”‚   â”œâ”€â”€ __init__.py
â”‚   â”œâ”€â”€ test_token_encryption.py
â”‚   â”œâ”€â”€ test_session_service.py
â”‚   â”œâ”€â”€ test_jira_service.py
â”‚   â”œâ”€â”€ test_auth_repository.py
â”‚   â””â”€â”€ test_api/
â”‚       â”œâ”€â”€ __init__.py
â”‚       â”œâ”€â”€ test_auth_endpoints.py
â”‚       â””â”€â”€ test_session_endpoints.py
```

### 1.2 Additional Fixtures (add to conftest.py)

```python
# tests/conftest.py - additions for Phase 2
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta

from app.schemas.auth import UserInfo, ProjectContextData, ProjectPermissions


@pytest.fixture
def mock_jira_service():
    """Mock JiraService for unit tests."""
    service = AsyncMock()
    
    # Default successful responses
    service.exchange_code_for_tokens.return_value = {
        'access_token': 'test-access-token',
        'refresh_token': 'test-refresh-token',
        'expires_in': 3600
    }
    
    service.get_user_info.return_value = UserInfo(
        jira_user_id='user-123',
        display_name='Test User',
        email='test@example.com'
    )
    
    service.get_project_metadata.return_value = ProjectContextData(
        project_key='TEST',
        project_name='Test Project',
        permissions=ProjectPermissions(can_create_tickets=True, can_assign_tickets=True),
        available_sprints=[],
        team_members=[],
        cached_at=datetime.utcnow()
    )
    
    service.validate_project_access.return_value = True
    
    return service


@pytest.fixture
def mock_auth_repository():
    """Mock AuthRepository for unit tests."""
    repo = AsyncMock()
    repo.store_token.return_value = None
    repo.get_token.return_value = MagicMock(
        access_token='encrypted-token',
        refresh_token='encrypted-refresh',
        expires_at=datetime.utcnow() + timedelta(hours=1)
    )
    repo.cache_project_context.return_value = None
    repo.get_project_context.return_value = None
    return repo


@pytest.fixture
def mock_session_repository():
    """Mock SessionRepository for unit tests."""
    repo = AsyncMock()
    repo.create_session.return_value = MagicMock(
        id=uuid4(),
        site_name='Test Site',
        current_stage='upload'
    )
    repo.get_session_by_id.return_value = None
    repo.commit.return_value = None
    return repo


@pytest.fixture
def valid_oauth_callback_params():
    """Valid OAuth callback parameters."""
    return {
        'code': 'auth-code-from-jira',
        'state': 'csrf-state-token'
    }


@pytest.fixture
def sample_create_session_request():
    """Valid session creation request."""
    return {
        'site_name': 'University of Wisconsin',
        'site_description': 'Main campus Drupal site',
        'llm_provider_choice': 'openai',
        'jira_project_key': 'UWEC'
    }
```

---

## Part 2: Token Encryption Tests

### 2.1 Token Encryption/Decryption Tests

```python
# tests/phase_2_auth/test_token_encryption.py
import pytest
from app.core.security import encrypt_token, decrypt_token, TokenEncryptionError


class TestTokenEncryption:
    """Test Fernet-based token encryption."""
    
    def test_encrypt_returns_different_value(self):
        """Encrypted value should differ from original."""
        original = "test-access-token"
        
        encrypted = encrypt_token(original)
        
        assert encrypted != original
        assert isinstance(encrypted, str)
    
    def test_decrypt_recovers_original(self):
        """Decryption should recover the original token."""
        original = "test-access-token-12345"
        
        encrypted = encrypt_token(original)
        decrypted = decrypt_token(encrypted)
        
        assert decrypted == original
    
    def test_encrypt_produces_different_ciphertext_each_time(self):
        """Same plaintext should produce different ciphertext (IV)."""
        original = "same-token"
        
        encrypted1 = encrypt_token(original)
        encrypted2 = encrypt_token(original)
        
        # Fernet includes timestamp and random IV, so ciphertexts differ
        assert encrypted1 != encrypted2
    
    def test_decrypt_invalid_token_raises_error(self):
        """Invalid ciphertext should raise TokenEncryptionError."""
        with pytest.raises(TokenEncryptionError):
            decrypt_token("not-a-valid-encrypted-token")
    
    def test_decrypt_tampered_token_raises_error(self):
        """Tampered ciphertext should raise TokenEncryptionError."""
        original = "test-token"
        encrypted = encrypt_token(original)
        
        # Tamper with the encrypted value
        tampered = encrypted[:-5] + "XXXXX"
        
        with pytest.raises(TokenEncryptionError):
            decrypt_token(tampered)
    
    def test_handles_unicode_tokens(self):
        """Should handle tokens with unicode characters."""
        original = "token-with-Ã©mojis-ðŸ”‘"
        
        encrypted = encrypt_token(original)
        decrypted = decrypt_token(encrypted)
        
        assert decrypted == original
```

---

## Part 3: Service Layer Tests

### 3.1 SessionService Tests

```python
# tests/phase_2_auth/test_session_service.py
import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from app.services.session_service import SessionService
from app.services.exceptions import SessionError
from app.schemas.auth import SessionCreateRequest
from app.schemas.base import SessionStage


class TestSessionServiceCreation:
    """Test session creation flow."""
    
    @pytest.fixture
    def service(self, mock_session_repository, mock_auth_repository, mock_jira_service):
        return SessionService(
            session_repo=mock_session_repository,
            auth_repo=mock_auth_repository,
            jira_service=mock_jira_service
        )
    
    async def test_create_session_validates_project_access(
        self, service, mock_jira_service, sample_create_session_request
    ):
        """Should validate Jira project access before creating session."""
        request = SessionCreateRequest(**sample_create_session_request)
        
        await service.create_session(request, user_id='user-123')
        
        mock_jira_service.validate_project_access.assert_called_once_with('UWEC')
    
    async def test_create_session_caches_project_context(
        self, service, mock_auth_repository, mock_jira_service, sample_create_session_request
    ):
        """Should cache project metadata for dropdowns."""
        request = SessionCreateRequest(**sample_create_session_request)
        
        await service.create_session(request, user_id='user-123')
        
        mock_jira_service.get_project_metadata.assert_called_once()
        mock_auth_repository.cache_project_context.assert_called_once()
    
    async def test_create_session_returns_session_response(
        self, service, sample_create_session_request
    ):
        """Should return SessionResponse with all required fields."""
        request = SessionCreateRequest(**sample_create_session_request)
        
        response = await service.create_session(request, user_id='user-123')
        
        assert response.session_id is not None
        assert response.site_name == sample_create_session_request['site_name']
        assert response.current_stage == SessionStage.UPLOAD
        assert response.user_info is not None
        assert response.project_context is not None
    
    async def test_create_session_commits_transaction(
        self, service, mock_session_repository, sample_create_session_request
    ):
        """Should commit the transaction after successful creation."""
        request = SessionCreateRequest(**sample_create_session_request)
        
        await service.create_session(request, user_id='user-123')
        
        mock_session_repository.commit.assert_called_once()
    
    async def test_create_session_fails_without_project_access(
        self, service, mock_jira_service, sample_create_session_request
    ):
        """Should raise error if user lacks project access."""
        mock_jira_service.validate_project_access.return_value = False
        request = SessionCreateRequest(**sample_create_session_request)
        
        with pytest.raises(SessionError) as exc_info:
            await service.create_session(request, user_id='user-123')
        
        assert exc_info.value.category == 'user_fixable'
        assert 'access' in exc_info.value.message.lower()


class TestSessionServiceRecovery:
    """Test session recovery flow."""
    
    @pytest.fixture
    def service(self, mock_session_repository, mock_auth_repository, mock_jira_service):
        return SessionService(
            session_repo=mock_session_repository,
            auth_repo=mock_auth_repository,
            jira_service=mock_jira_service
        )
    
    async def test_recover_session_returns_session_state(
        self, service, mock_session_repository
    ):
        """Should return current session state for recovery."""
        session_id = uuid4()
        mock_session_repository.get_session_by_id.return_value = MagicMock(
            id=session_id,
            site_name='Recovered Site',
            current_stage=SessionStage.REVIEW,
            jira_user_id='user-123'
        )
        
        response = await service.recover_session(session_id, user_id='user-123')
        
        assert response.session_id == session_id
        assert response.ready_to_continue is True
    
    async def test_recover_session_validates_ownership(
        self, service, mock_session_repository
    ):
        """Should reject recovery if user doesn't own session."""
        session_id = uuid4()
        mock_session_repository.get_session_by_id.return_value = MagicMock(
            id=session_id,
            jira_user_id='different-user'
        )
        
        with pytest.raises(SessionError) as exc_info:
            await service.recover_session(session_id, user_id='user-123')
        
        assert exc_info.value.category == 'user_fixable'
    
    async def test_recover_session_not_found(self, service, mock_session_repository):
        """Should raise error for non-existent session."""
        mock_session_repository.get_session_by_id.return_value = None
        
        with pytest.raises(SessionError) as exc_info:
            await service.recover_session(uuid4(), user_id='user-123')
        
        assert 'not found' in exc_info.value.message.lower()


class TestSessionServiceIncompleteSessionQuery:
    """Test querying incomplete sessions for user."""
    
    @pytest.fixture
    def service(self, mock_session_repository, mock_auth_repository, mock_jira_service):
        return SessionService(
            session_repo=mock_session_repository,
            auth_repo=mock_auth_repository,
            jira_service=mock_jira_service
        )
    
    async def test_get_incomplete_sessions(self, service, mock_session_repository):
        """Should return list of user's incomplete sessions."""
        mock_session_repository.find_incomplete_sessions_by_user.return_value = [
            MagicMock(id=uuid4(), site_name='Site 1', current_stage=SessionStage.UPLOAD),
            MagicMock(id=uuid4(), site_name='Site 2', current_stage=SessionStage.REVIEW)
        ]
        
        sessions = await service.get_incomplete_sessions(user_id='user-123')
        
        assert len(sessions) == 2
        mock_session_repository.find_incomplete_sessions_by_user.assert_called_with('user-123')
```

### 3.2 JiraService Tests (Auth Subset)

```python
# tests/phase_2_auth/test_jira_service.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from app.integrations.jira.client import JiraService
from app.integrations.jira.exceptions import JiraAuthError, JiraAPIError


class TestJiraServiceOAuth:
    """Test OAuth token exchange."""
    
    @pytest.fixture
    def service(self):
        return JiraService(
            base_url='https://api.atlassian.com',
            client_id='test-client-id',
            client_secret='test-client-secret'
        )
    
    async def test_exchange_code_for_tokens_success(self, service):
        """Should exchange auth code for access/refresh tokens."""
        with patch.object(service, '_http_client') as mock_client:
            mock_client.post.return_value = MagicMock(
                status_code=200,
                json=lambda: {
                    'access_token': 'new-access-token',
                    'refresh_token': 'new-refresh-token',
                    'expires_in': 3600
                }
            )
            
            result = await service.exchange_code_for_tokens(
                code='auth-code',
                redirect_uri='http://localhost/callback'
            )
            
            assert result['access_token'] == 'new-access-token'
            assert result['refresh_token'] == 'new-refresh-token'
    
    async def test_exchange_code_invalid_code_raises_error(self, service):
        """Should raise JiraAuthError for invalid auth code."""
        with patch.object(service, '_http_client') as mock_client:
            mock_client.post.return_value = MagicMock(
                status_code=400,
                json=lambda: {'error': 'invalid_grant'}
            )
            
            with pytest.raises(JiraAuthError):
                await service.exchange_code_for_tokens(
                    code='invalid-code',
                    redirect_uri='http://localhost/callback'
                )
    
    async def test_refresh_token_success(self, service):
        """Should refresh expired access token."""
        with patch.object(service, '_http_client') as mock_client:
            mock_client.post.return_value = MagicMock(
                status_code=200,
                json=lambda: {
                    'access_token': 'refreshed-access-token',
                    'refresh_token': 'new-refresh-token',
                    'expires_in': 3600
                }
            )
            
            result = await service.refresh_access_token(refresh_token='old-refresh-token')
            
            assert result['access_token'] == 'refreshed-access-token'


class TestJiraServiceUserInfo:
    """Test user info retrieval."""
    
    @pytest.fixture
    def service(self):
        return JiraService(
            base_url='https://api.atlassian.com',
            client_id='test-client-id',
            client_secret='test-client-secret'
        )
    
    async def test_get_user_info_success(self, service):
        """Should retrieve user info from Jira."""
        with patch.object(service, '_http_client') as mock_client:
            mock_client.get.return_value = MagicMock(
                status_code=200,
                json=lambda: {
                    'account_id': 'user-123',
                    'name': 'Test User',
                    'email': 'test@example.com'
                }
            )
            
            user_info = await service.get_user_info(access_token='valid-token')
            
            assert user_info.jira_user_id == 'user-123'
            assert user_info.display_name == 'Test User'
    
    async def test_get_user_info_expired_token(self, service):
        """Should raise JiraAuthError for expired token."""
        with patch.object(service, '_http_client') as mock_client:
            mock_client.get.return_value = MagicMock(status_code=401)
            
            with pytest.raises(JiraAuthError):
                await service.get_user_info(access_token='expired-token')


class TestJiraServiceProjectValidation:
    """Test project access validation."""
    
    @pytest.fixture
    def service(self):
        return JiraService(
            base_url='https://api.atlassian.com',
            client_id='test-client-id',
            client_secret='test-client-secret'
        )
    
    async def test_validate_project_access_success(self, service):
        """Should return True when user has project access."""
        with patch.object(service, '_http_client') as mock_client:
            mock_client.get.return_value = MagicMock(
                status_code=200,
                json=lambda: {
                    'key': 'TEST',
                    'name': 'Test Project',
                    'permissions': {'CREATE_ISSUES': True}
                }
            )
            
            result = await service.validate_project_access(
                project_key='TEST',
                access_token='valid-token'
            )
            
            assert result is True
    
    async def test_validate_project_access_no_permission(self, service):
        """Should return False when user lacks create permission."""
        with patch.object(service, '_http_client') as mock_client:
            mock_client.get.return_value = MagicMock(
                status_code=200,
                json=lambda: {
                    'key': 'TEST',
                    'name': 'Test Project',
                    'permissions': {'CREATE_ISSUES': False}
                }
            )
            
            result = await service.validate_project_access(
                project_key='TEST',
                access_token='valid-token'
            )
            
            assert result is False
    
    async def test_validate_project_not_found(self, service):
        """Should return False for non-existent project."""
        with patch.object(service, '_http_client') as mock_client:
            mock_client.get.return_value = MagicMock(status_code=404)
            
            result = await service.validate_project_access(
                project_key='NOTEXIST',
                access_token='valid-token'
            )
            
            assert result is False
```

---

## Part 4: API Endpoint Tests

### 4.1 Auth Endpoint Tests

```python
# tests/phase_2_auth/test_api/test_auth_endpoints.py
import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock
from fastapi import FastAPI

from app.main import app
from app.api.dependencies.services import get_jira_service
from app.api.dependencies.auth import get_current_user


class TestLoginEndpoint:
    """Test GET /api/auth/login."""
    
    async def test_login_returns_redirect_url(self):
        """Should return OAuth authorization URL."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/auth/login")
        
        assert response.status_code == 200
        data = response.json()
        assert 'redirect_url' in data
        assert 'state' in data
        assert 'atlassian.com' in data['redirect_url']
    
    async def test_login_includes_pkce_challenge(self):
        """Should include PKCE code_challenge in redirect URL."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/auth/login")
        
        data = response.json()
        assert 'code_challenge' in data['redirect_url']


class TestCallbackEndpoint:
    """Test GET /api/auth/callback."""
    
    async def test_callback_exchanges_code_for_tokens(self, mock_jira_service):
        """Should exchange auth code for tokens."""
        app.dependency_overrides[get_jira_service] = lambda: mock_jira_service
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                "/api/auth/callback",
                params={'code': 'auth-code', 'state': 'valid-state'}
            )
        
        assert response.status_code == 200
        mock_jira_service.exchange_code_for_tokens.assert_called_once()
        
        app.dependency_overrides.clear()
    
    async def test_callback_stores_encrypted_tokens(self, mock_jira_service, mock_auth_repository):
        """Should store encrypted tokens in database."""
        app.dependency_overrides[get_jira_service] = lambda: mock_jira_service
        # Also need to override auth repo dependency
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                "/api/auth/callback",
                params={'code': 'auth-code', 'state': 'valid-state'}
            )
        
        assert response.status_code == 200
        # Verify token storage was called
        
        app.dependency_overrides.clear()
    
    async def test_callback_missing_code_returns_error(self):
        """Should return error when code is missing."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                "/api/auth/callback",
                params={'state': 'valid-state'}  # Missing 'code'
            )
        
        assert response.status_code == 422  # Validation error
    
    async def test_callback_invalid_state_returns_error(self):
        """Should reject invalid CSRF state."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                "/api/auth/callback",
                params={'code': 'auth-code', 'state': 'invalid-csrf-state'}
            )
        
        assert response.status_code == 400


class TestAuthStatusEndpoint:
    """Test GET /api/auth/status."""
    
    async def test_status_unauthenticated(self):
        """Should return unauthenticated status when no token."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/auth/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data['authenticated'] is False
    
    async def test_status_authenticated_with_user_info(self, mock_user):
        """Should return user info when authenticated."""
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                "/api/auth/status",
                headers={'Authorization': 'Bearer valid-token'}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data['authenticated'] is True
        assert data['user_info']['display_name'] == mock_user.display_name
        
        app.dependency_overrides.clear()


class TestLogoutEndpoint:
    """Test POST /api/auth/logout."""
    
    async def test_logout_clears_tokens(self, mock_user, mock_auth_repository):
        """Should clear stored tokens on logout."""
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/auth/logout",
                headers={'Authorization': 'Bearer valid-token'}
            )
        
        assert response.status_code == 200
        
        app.dependency_overrides.clear()
```

### 4.2 Session Endpoint Tests

```python
# tests/phase_2_auth/test_api/test_session_endpoints.py
import pytest
from httpx import AsyncClient
from uuid import uuid4

from app.main import app
from app.api.dependencies.auth import get_current_user
from app.api.dependencies.services import get_session_service


class TestCreateSessionEndpoint:
    """Test POST /api/sessions."""
    
    async def test_create_session_requires_auth(self):
        """Should require authentication."""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/sessions",
                json={
                    'site_name': 'Test',
                    'jira_project_key': 'TEST'
                }
            )
        
        assert response.status_code == 401
    
    async def test_create_session_success(self, mock_user, mock_session_service):
        """Should create session and return response."""
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session_service] = lambda: mock_session_service
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/sessions",
                json={
                    'site_name': 'University Site',
                    'site_description': 'Main campus',
                    'llm_provider_choice': 'openai',
                    'jira_project_key': 'UWEC'
                },
                headers={'Authorization': 'Bearer valid-token'}
            )
        
        assert response.status_code == 201
        data = response.json()
        assert 'session_id' in data
        assert data['site_name'] == 'University Site'
        
        app.dependency_overrides.clear()
    
    async def test_create_session_validates_request(self, mock_user):
        """Should validate request body."""
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/sessions",
                json={
                    'site_name': '',  # Empty - should fail
                    'jira_project_key': 'TEST'
                },
                headers={'Authorization': 'Bearer valid-token'}
            )
        
        assert response.status_code == 422
        
        app.dependency_overrides.clear()


class TestRecoverSessionEndpoint:
    """Test POST /api/sessions/{session_id}/recover."""
    
    async def test_recover_session_success(self, mock_user, mock_session_service):
        """Should recover existing session."""
        session_id = uuid4()
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session_service] = lambda: mock_session_service
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                f"/api/sessions/{session_id}/recover",
                headers={'Authorization': 'Bearer valid-token'}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data['ready_to_continue'] is True
        
        app.dependency_overrides.clear()
    
    async def test_recover_session_not_found(self, mock_user, mock_session_service):
        """Should return 404 for non-existent session."""
        mock_session_service.recover_session.side_effect = SessionError(
            message='Session not found',
            category='user_fixable'
        )
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session_service] = lambda: mock_session_service
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                f"/api/sessions/{uuid4()}/recover",
                headers={'Authorization': 'Bearer valid-token'}
            )
        
        assert response.status_code == 404
        
        app.dependency_overrides.clear()


class TestGetIncompleteSessionsEndpoint:
    """Test GET /api/sessions/incomplete."""
    
    async def test_get_incomplete_sessions(self, mock_user, mock_session_service):
        """Should return list of incomplete sessions."""
        mock_session_service.get_incomplete_sessions.return_value = [
            {'session_id': str(uuid4()), 'site_name': 'Site 1', 'stage': 'upload'},
            {'session_id': str(uuid4()), 'site_name': 'Site 2', 'stage': 'review'}
        ]
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_session_service] = lambda: mock_session_service
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                "/api/sessions/incomplete",
                headers={'Authorization': 'Bearer valid-token'}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data['incomplete_sessions']) == 2
        
        app.dependency_overrides.clear()
```

---

## Part 5: Implementation Specifications

After tests are written, implement the following components:

### 5.1 Core Security

**File**: `/backend/app/core/security.py`
- `encrypt_token(plaintext: str) -> str` - Fernet encryption
- `decrypt_token(ciphertext: str) -> str` - Fernet decryption
- `generate_pkce_pair() -> tuple[str, str]` - Code verifier and challenge
- `generate_csrf_state() -> str` - Random state token

### 5.2 JiraService (Auth Methods Only)

**File**: `/backend/app/integrations/jira/client.py`
- `exchange_code_for_tokens()` - OAuth code exchange
- `refresh_access_token()` - Token refresh
- `get_user_info()` - Current user details
- `validate_project_access()` - Check CREATE_ISSUES permission
- `get_project_metadata()` - Sprints, team members for caching

### 5.3 AuthRepository

**File**: `/backend/app/repositories/sqlalchemy/auth_repository.py`
- `store_token()` - Store encrypted tokens
- `get_token()` - Retrieve and decrypt tokens
- `delete_token()` - Remove on logout
- `cache_project_context()` - Store project metadata
- `get_project_context()` - Retrieve cached metadata

### 5.4 SessionService

**File**: `/backend/app/services/session_service.py`
- `create_session()` - Full session creation flow
- `recover_session()` - Session recovery with validation
- `get_incomplete_sessions()` - Query user's sessions
- `get_session_status()` - Current session state

### 5.5 API Endpoints

**File**: `/backend/app/api/routes/auth.py`
- `GET /api/auth/login` - Initiate OAuth
- `GET /api/auth/callback` - Handle OAuth callback
- `GET /api/auth/status` - Check auth status
- `POST /api/auth/logout` - Clear session

**File**: `/backend/app/api/routes/sessions.py`
- `POST /api/sessions` - Create new session
- `POST /api/sessions/{id}/recover` - Recover session
- `GET /api/sessions/incomplete` - List incomplete

### 5.6 Dependencies

**File**: `/backend/app/api/dependencies/auth.py`
- `get_current_user()` - Extract and validate user from token
- `get_optional_user()` - User if authenticated, None otherwise

**File**: `/backend/app/api/dependencies/services.py`
- `get_session_service()` - Inject SessionService
- `get_jira_service()` - Inject JiraService (singleton)

---

## Document References

### Primary References (in project knowledge)
- `updated_auth_flow_spec.md` - Complete OAuth flow specification
- `auth_schemas_models_updated.py` - Pydantic models for auth
- `session_model_spec.md` - Session model details
- `jira_auth_token_model_spec.md` - Token storage model
- `jira_project_context_model_spec.md` - Cached project data
- `session_service_architecture.md` - SessionService methods
- `fastapi_di_lifecycle_decisions_updated.md` - DI patterns

### API Specifications
- `fastapi_jira_integration_endpoints.md` - Jira endpoint specs

---

## Success Criteria

### All Tests Pass
```bash
pytest tests/phase_2_auth/ -v --cov=app/services --cov=app/api/routes --cov-report=term-missing
```

### Coverage Requirements
- Security utilities: >95% coverage
- SessionService: >85% coverage
- JiraService (auth methods): >80% coverage
- API endpoints: >80% coverage

### Verification Checklist
- [ ] Token encryption/decryption works correctly
- [ ] OAuth login flow redirects to Jira
- [ ] OAuth callback exchanges code for tokens
- [ ] Tokens are stored encrypted in database
- [ ] Token refresh works before expiry
- [ ] Session creation validates project access
- [ ] Project context is cached on session creation
- [ ] Session recovery validates ownership
- [ ] All API endpoints return correct response schemas
- [ ] All Phase 2 tests pass

### Manual Verification
After tests pass, manually verify:
1. Navigate to `/api/auth/login` â†’ Redirects to Atlassian
2. Complete Jira OAuth â†’ Callback stores tokens
3. Create session â†’ Project validation occurs
4. Check `/api/auth/status` â†’ Shows authenticated user

---

## Commands to Run

```bash
# Run Phase 2 tests only
pytest tests/phase_2_auth/ -v

# Run with coverage
pytest tests/phase_2_auth/ -v --cov=app --cov-report=html

# Run specific test class
pytest tests/phase_2_auth/test_session_service.py::TestSessionServiceCreation -v

# Integration test with real Jira (requires .env)
pytest tests/phase_2_auth/ -v -m integration
```
