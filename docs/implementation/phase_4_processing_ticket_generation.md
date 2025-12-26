# Phase 4: Processing (Ticket Generation)

## Overview
Implement LLM-powered ticket generation, background task processing with ARQ, and progress tracking via Redis pub/sub. This phase introduces the first background jobs and real-time progress communication.

**Estimated Effort**: 3-4 days  
**Prerequisites**: Phases 1-3 complete (models, auth, sessions, file upload)  
**Deliverables**: ProcessingService, LLMService, ARQ workers, progress WebSocket

---

## Test-Driven Development Approach

### TDD Workflow for This Phase
1. Write unit tests for LLMService interface and response validation
2. Write unit tests for ProcessingService orchestration
3. Write integration tests for ARQ job execution
4. Write tests for progress callback/pub-sub
5. Write API endpoint tests
6. Implement code to make tests pass
7. End-to-end test with mocked LLM

---

## Part 1: Test Structure

### 1.1 Phase 4 Test Directory

```
tests/
â”œâ”€â”€ conftest.py                    # Add processing-specific fixtures
â”œâ”€â”€ mocks/
â”‚   â”œâ”€â”€ __init__.py
â”‚   â”œâ”€â”€ jira_service.py
â”‚   â””â”€â”€ llm_service.py             # Mock LLM responses
â”œâ”€â”€ phase_4_processing/
â”‚   â”œâ”€â”€ __init__.py
â”‚   â”œâ”€â”€ test_llm_service.py
â”‚   â”œâ”€â”€ test_llm_response_validation.py
â”‚   â”œâ”€â”€ test_processing_service.py
â”‚   â”œâ”€â”€ test_entity_grouping.py
â”‚   â”œâ”€â”€ test_arq_jobs/
â”‚   â”‚   â”œâ”€â”€ __init__.py
â”‚   â”‚   â””â”€â”€ test_processing_worker.py
â”‚   â”œâ”€â”€ test_progress_tracking.py
â”‚   â””â”€â”€ test_api/
â”‚       â”œâ”€â”€ __init__.py
â”‚       â””â”€â”€ test_processing_endpoints.py
```

### 1.2 Additional Fixtures (add to conftest.py)

```python
# tests/conftest.py - additions for Phase 4
import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from app.schemas.base import TaskType, TaskStatus


@pytest.fixture
def mock_llm_service():
    """Mock LLMService with valid responses."""
    service = AsyncMock()
    
    # Default successful ticket generation response
    service.generate_ticket_content.return_value = {
        'title': 'Configure Content Type: Article',
        'user_story': 'As a content editor, I need to configure the Article content type...',
        'analysis': '## Technical Analysis\n\nThe Article content type requires...',
        'verification': '## Verification Steps\n\n1. Navigate to Structure > Content Types...'
    }
    
    service.validate_connectivity.return_value = {'status': 'healthy', 'provider': 'openai'}
    
    return service


@pytest.fixture
def mock_arq_pool():
    """Mock ARQ connection pool."""
    pool = AsyncMock()
    pool.enqueue_job.return_value = MagicMock(job_id='test-job-123')
    return pool


@pytest.fixture
def sample_entity_data():
    """Sample entity data for ticket generation."""
    return {
        'type': 'bundles',
        'entity_group': 'Content',
        'data': {
            'machine_name': 'article',
            'label': 'Article',
            'description': 'Use articles for time-sensitive content.'
        },
        'csv_source': {'filename': 'bundles.csv', 'rows': [1]}
    }


@pytest.fixture
def sample_session_with_files(db_session, sample_session_data):
    """Create session with uploaded files for processing."""
    async def _create():
        session = Session(**sample_session_data)
        db_session.add(session)
        await db_session.flush()
        
        # Add uploaded file
        file = UploadedFile(
            session_id=session.id,
            filename='UWEC_Bundles.csv',
            csv_type='bundles',
            parsed_content={
                'headers': ['machine_name', 'label', 'description'],
                'rows': [
                    {'machine_name': 'article', 'label': 'Article', 'description': 'News articles'},
                    {'machine_name': 'page', 'label': 'Page', 'description': 'Static pages'}
                ]
            },
            validation_status='valid',
            row_count=2
        )
        db_session.add(file)
        await db_session.flush()
        
        return session
    
    return _create


@pytest.fixture
def mock_progress_callback():
    """Mock progress callback for testing."""
    callback = AsyncMock()
    calls = []
    
    async def track_progress(percentage, stage, details):
        calls.append({'percentage': percentage, 'stage': stage, 'details': details})
        await callback(percentage, stage, details)
    
    track_progress.calls = calls
    return track_progress
```

---

## Part 2: LLM Service Tests

### 2.1 LLMService Interface Tests

```python
# tests/phase_4_processing/test_llm_service.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.integrations.llm.service import LLMService
from app.integrations.llm.exceptions import LLMError, LLMRateLimitError, LLMTimeoutError


class TestLLMServiceConnectivity:
    """Test LLM service connectivity validation."""
    
    @pytest.fixture
    def service(self):
        return LLMService(
            openai_api_key='test-openai-key',
            anthropic_api_key='test-anthropic-key',
            default_provider='openai'
        )
    
    async def test_validate_connectivity_openai(self, service):
        """Should validate OpenAI connectivity."""
        with patch.object(service, '_openai_client') as mock_client:
            mock_client.models.list.return_value = MagicMock()
            
            result = await service.validate_connectivity(provider='openai')
            
            assert result['status'] == 'healthy'
            assert result['provider'] == 'openai'
    
    async def test_validate_connectivity_anthropic(self, service):
        """Should validate Anthropic connectivity."""
        with patch.object(service, '_anthropic_client') as mock_client:
            mock_client.messages.create.return_value = MagicMock()
            
            result = await service.validate_connectivity(provider='anthropic')
            
            assert result['status'] == 'healthy'
            assert result['provider'] == 'anthropic'
    
    async def test_validate_connectivity_failure(self, service):
        """Should report unhealthy on connection failure."""
        with patch.object(service, '_openai_client') as mock_client:
            mock_client.models.list.side_effect = Exception("Connection refused")
            
            result = await service.validate_connectivity(provider='openai')
            
            assert result['status'] == 'unhealthy'
            assert 'error' in result


class TestLLMServiceGeneration:
    """Test ticket content generation."""
    
    @pytest.fixture
    def service(self):
        return LLMService(
            openai_api_key='test-openai-key',
            anthropic_api_key='test-anthropic-key',
            default_provider='openai'
        )
    
    async def test_generate_ticket_content_success(self, service, sample_entity_data):
        """Should generate ticket content from entity data."""
        with patch.object(service, '_call_llm') as mock_call:
            mock_call.return_value = {
                'title': 'Configure Content Type: Article',
                'user_story': 'As a content editor...',
                'analysis': '## Analysis\n...',
                'verification': '## Verification\n...'
            }
            
            result = await service.generate_ticket_content(
                entity=sample_entity_data,
                site_context={'site_name': 'UWEC', 'description': 'University site'}
            )
            
            assert 'title' in result
            assert 'user_story' in result
            assert 'analysis' in result
            assert 'verification' in result
    
    async def test_generate_ticket_retries_on_rate_limit(self, service, sample_entity_data):
        """Should retry on rate limit errors."""
        call_count = 0
        
        async def mock_call(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise LLMRateLimitError("Rate limited")
            return {'title': 'Success', 'user_story': '...', 'analysis': '...', 'verification': '...'}
        
        with patch.object(service, '_call_llm', side_effect=mock_call):
            result = await service.generate_ticket_content(
                entity=sample_entity_data,
                site_context={}
            )
            
            assert call_count == 3
            assert result['title'] == 'Success'
    
    async def test_generate_ticket_timeout_raises_error(self, service, sample_entity_data):
        """Should raise timeout error after max retries."""
        with patch.object(service, '_call_llm') as mock_call:
            mock_call.side_effect = LLMTimeoutError("Timeout")
            
            with pytest.raises(LLMError) as exc_info:
                await service.generate_ticket_content(
                    entity=sample_entity_data,
                    site_context={}
                )
            
            assert 'timeout' in str(exc_info.value).lower()


class TestLLMResponseValidation:
    """Test LLM response validation."""
    
    def test_valid_response_passes(self):
        """Valid response should pass validation."""
        from app.services.processing_service import _validate_llm_response
        
        response = {
            'title': 'Configure Article',
            'user_story': 'As a user...',
            'analysis': 'Technical analysis...',
            'verification': 'Verification steps...'
        }
        
        # Should not raise
        _validate_llm_response(response)
    
    def test_missing_field_raises_error(self):
        """Missing required field should raise error."""
        from app.services.processing_service import _validate_llm_response
        from app.services.exceptions import ProcessingError
        
        response = {
            'title': 'Configure Article',
            'user_story': 'As a user...',
            # Missing 'analysis' and 'verification'
        }
        
        with pytest.raises(ProcessingError) as exc_info:
            _validate_llm_response(response)
        
        assert 'analysis' in str(exc_info.value).lower() or 'verification' in str(exc_info.value).lower()
    
    def test_empty_field_raises_error(self):
        """Empty required field should raise error."""
        from app.services.processing_service import _validate_llm_response
        from app.services.exceptions import ProcessingError
        
        response = {
            'title': '',  # Empty
            'user_story': 'As a user...',
            'analysis': 'Analysis...',
            'verification': 'Verification...'
        }
        
        with pytest.raises(ProcessingError):
            _validate_llm_response(response)
    
    def test_title_too_long_raises_error(self):
        """Title over 255 chars should raise error."""
        from app.services.processing_service import _validate_llm_response
        from app.services.exceptions import ProcessingError
        
        response = {
            'title': 'x' * 300,  # Too long
            'user_story': 'As a user...',
            'analysis': 'Analysis...',
            'verification': 'Verification...'
        }
        
        with pytest.raises(ProcessingError) as exc_info:
            _validate_llm_response(response)
        
        assert 'title' in str(exc_info.value).lower()
```

---

## Part 3: Processing Service Tests

### 3.1 ProcessingService Unit Tests

```python
# tests/phase_4_processing/test_processing_service.py
import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

from app.services.processing_service import ProcessingService
from app.services.exceptions import ProcessingError
from app.schemas.base import SessionStage, TaskStatus


class TestProcessingServiceEnqueue:
    """Test job enqueueing (public method)."""
    
    @pytest.fixture
    def service(self, mock_session_repository, mock_ticket_repository, 
                mock_upload_repository, mock_error_repository, 
                mock_llm_service, mock_arq_pool):
        return ProcessingService(
            session_repo=mock_session_repository,
            ticket_repo=mock_ticket_repository,
            upload_repo=mock_upload_repository,
            error_repo=mock_error_repository,
            llm_service=mock_llm_service,
            arq_pool=mock_arq_pool
        )
    
    async def test_generate_tickets_validates_llm_first(
        self, service, mock_llm_service
    ):
        """Should validate LLM connectivity before enqueueing."""
        session_id = uuid4()
        
        await service.generate_tickets(session_id)
        
        mock_llm_service.validate_connectivity.assert_called_once()
    
    async def test_generate_tickets_fails_if_llm_unhealthy(
        self, service, mock_llm_service
    ):
        """Should fail if LLM is not available."""
        session_id = uuid4()
        mock_llm_service.validate_connectivity.return_value = {
            'status': 'unhealthy',
            'error': 'Connection refused'
        }
        
        with pytest.raises(ProcessingError) as exc_info:
            await service.generate_tickets(session_id)
        
        assert exc_info.value.category == 'temporary'
    
    async def test_generate_tickets_creates_task(
        self, service, mock_session_repository
    ):
        """Should create SessionTask for tracking."""
        session_id = uuid4()
        
        result = await service.generate_tickets(session_id)
        
        mock_session_repository.start_task.assert_called_once()
        assert result.task_id is not None
    
    async def test_generate_tickets_enqueues_job(
        self, service, mock_arq_pool
    ):
        """Should enqueue ARQ job."""
        session_id = uuid4()
        
        result = await service.generate_tickets(session_id)
        
        mock_arq_pool.enqueue_job.assert_called_once_with(
            'generate_tickets_job',
            session_id=session_id,
            task_id=result.task_id
        )
    
    async def test_generate_tickets_returns_idempotent_if_running(
        self, service, mock_session_repository
    ):
        """Should return existing task if already running."""
        session_id = uuid4()
        existing_task_id = uuid4()
        
        mock_session_repository.get_active_task.return_value = MagicMock(
            task_id=existing_task_id,
            status=TaskStatus.RUNNING
        )
        mock_session_repository.can_start_task.return_value = False
        
        result = await service.generate_tickets(session_id)
        
        assert result.task_id == existing_task_id
        assert result.status == 'processing'


class TestProcessingServiceExecution:
    """Test ticket generation execution (internal method)."""
    
    @pytest.fixture
    def service(self, mock_session_repository, mock_ticket_repository, 
                mock_upload_repository, mock_error_repository, mock_llm_service):
        # No arq_pool needed for internal execution
        return ProcessingService(
            session_repo=mock_session_repository,
            ticket_repo=mock_ticket_repository,
            upload_repo=mock_upload_repository,
            error_repo=mock_error_repository,
            llm_service=mock_llm_service
        )
    
    async def test_execute_generates_tickets_for_all_entities(
        self, service, mock_upload_repository, mock_ticket_repository, 
        mock_llm_service, mock_progress_callback
    ):
        """Should generate ticket for each entity."""
        session_id = uuid4()
        task_id = uuid4()
        
        # Setup: 2 entities in uploaded file
        mock_upload_repository.get_files_by_session.return_value = [
            MagicMock(
                csv_type='bundles',
                parsed_content={
                    'headers': ['machine_name', 'label'],
                    'rows': [
                        {'machine_name': 'article', 'label': 'Article'},
                        {'machine_name': 'page', 'label': 'Page'}
                    ]
                }
            )
        ]
        
        await service.execute_ticket_generation(
            session_id, task_id, mock_progress_callback
        )
        
        # Should call LLM twice
        assert mock_llm_service.generate_ticket_content.call_count == 2
        # Should create 2 tickets
        assert mock_ticket_repository.create.call_count == 2
    
    async def test_execute_publishes_progress(
        self, service, mock_upload_repository, mock_progress_callback
    ):
        """Should publish progress updates via callback."""
        session_id = uuid4()
        task_id = uuid4()
        
        mock_upload_repository.get_files_by_session.return_value = [
            MagicMock(
                csv_type='bundles',
                parsed_content={'headers': [], 'rows': [{'a': 'b'}]}
            )
        ]
        
        await service.execute_ticket_generation(
            session_id, task_id, mock_progress_callback
        )
        
        # Should have progress calls
        assert len(mock_progress_callback.calls) > 0
        # Final call should be 100%
        assert mock_progress_callback.calls[-1]['percentage'] == 100.0
    
    async def test_execute_handles_llm_error_gracefully(
        self, service, mock_upload_repository, mock_llm_service, 
        mock_error_repository, mock_progress_callback
    ):
        """Should record error and continue on LLM failure."""
        session_id = uuid4()
        task_id = uuid4()
        
        mock_upload_repository.get_files_by_session.return_value = [
            MagicMock(
                csv_type='bundles',
                parsed_content={
                    'headers': [],
                    'rows': [
                        {'machine_name': 'article'},
                        {'machine_name': 'page'}
                    ]
                }
            )
        ]
        
        # First call fails, second succeeds
        mock_llm_service.generate_ticket_content.side_effect = [
            Exception("LLM error"),
            {'title': 'Page', 'user_story': '...', 'analysis': '...', 'verification': '...'}
        ]
        
        await service.execute_ticket_generation(
            session_id, task_id, mock_progress_callback
        )
        
        # Error should be recorded
        mock_error_repository.create_error.assert_called()
    
    async def test_execute_checks_cancellation(
        self, service, mock_session_repository, mock_upload_repository, 
        mock_progress_callback
    ):
        """Should check for cancellation between entities."""
        session_id = uuid4()
        task_id = uuid4()
        
        mock_upload_repository.get_files_by_session.return_value = [
            MagicMock(
                csv_type='bundles',
                parsed_content={
                    'headers': [],
                    'rows': [{'a': 'b'}, {'c': 'd'}]
                }
            )
        ]
        
        # Task gets cancelled after first entity
        call_count = 0
        async def mock_get_task(sid):
            nonlocal call_count
            call_count += 1
            if call_count > 1:
                return MagicMock(task_id=uuid4(), status=TaskStatus.CANCELLED)
            return MagicMock(task_id=task_id, status=TaskStatus.RUNNING)
        
        mock_session_repository.get_active_task.side_effect = mock_get_task
        
        await service.execute_ticket_generation(
            session_id, task_id, mock_progress_callback
        )
        
        # Should have stopped early (check final progress)
        final_call = mock_progress_callback.calls[-1]
        assert 'cancelled' in final_call['stage'].lower() or final_call['percentage'] < 100


class TestProcessingServiceRetry:
    """Test retry functionality."""
    
    @pytest.fixture
    def service(self, mock_session_repository, mock_ticket_repository, 
                mock_upload_repository, mock_error_repository, 
                mock_llm_service, mock_arq_pool):
        return ProcessingService(
            session_repo=mock_session_repository,
            ticket_repo=mock_ticket_repository,
            upload_repo=mock_upload_repository,
            error_repo=mock_error_repository,
            llm_service=mock_llm_service,
            arq_pool=mock_arq_pool
        )
    
    async def test_retry_cleans_up_partial_tickets(
        self, service, mock_session_repository, mock_ticket_repository
    ):
        """Should delete partial tickets before retry."""
        session_id = uuid4()
        
        mock_session_repository.get_active_task.return_value = MagicMock(
            status=TaskStatus.FAILED,
            retry_count=0
        )
        
        await service.retry_processing(session_id)
        
        mock_ticket_repository.delete_session_tickets.assert_called_with(session_id)
    
    async def test_retry_fails_after_max_attempts(
        self, service, mock_session_repository
    ):
        """Should fail after 3 retry attempts."""
        session_id = uuid4()
        
        mock_session_repository.get_active_task.return_value = MagicMock(
            status=TaskStatus.FAILED,
            retry_count=3
        )
        
        with pytest.raises(ProcessingError) as exc_info:
            await service.retry_processing(session_id)
        
        assert exc_info.value.category == 'admin_required'
        assert '3' in exc_info.value.message
```

### 3.2 Entity Grouping Tests

```python
# tests/phase_4_processing/test_entity_grouping.py
import pytest

from app.services.processing_service import _group_entities_by_type


class TestEntityGrouping:
    """Test entity grouping logic."""
    
    def test_groups_bundles_to_content(self):
        """Bundles should map to Content group."""
        files = [
            MagicMock(csv_type='bundles', parsed_content={'rows': [{'a': 'b'}]})
        ]
        
        groups = _group_entities_by_type(files)
        
        assert 'Content' in groups
        assert len(groups['Content']) == 1
    
    def test_groups_fields_to_content(self):
        """Fields should map to Content group."""
        files = [
            MagicMock(csv_type='fields', parsed_content={'rows': [{'a': 'b'}]})
        ]
        
        groups = _group_entities_by_type(files)
        
        assert 'Content' in groups
    
    def test_groups_views_to_views(self):
        """Views should map to Views group."""
        files = [
            MagicMock(csv_type='views', parsed_content={'rows': [{'a': 'b'}]})
        ]
        
        groups = _group_entities_by_type(files)
        
        assert 'Views' in groups
    
    def test_groups_image_styles_to_media(self):
        """Image styles should map to Media group."""
        files = [
            MagicMock(csv_type='image_styles', parsed_content={'rows': [{'a': 'b'}]})
        ]
        
        groups = _group_entities_by_type(files)
        
        assert 'Media' in groups
    
    def test_multiple_files_same_group(self):
        """Multiple files of same group should be combined."""
        files = [
            MagicMock(csv_type='bundles', parsed_content={'rows': [{'a': 'b'}]}),
            MagicMock(csv_type='fields', parsed_content={'rows': [{'c': 'd'}]})
        ]
        
        groups = _group_entities_by_type(files)
        
        assert len(groups['Content']) == 2
    
    def test_groups_in_correct_order(self):
        """Groups should be ordered correctly for processing."""
        files = [
            MagicMock(csv_type='workflows', parsed_content={'rows': [{}]}),
            MagicMock(csv_type='views', parsed_content={'rows': [{}]}),
            MagicMock(csv_type='bundles', parsed_content={'rows': [{}]})
        ]
        
        groups = _group_entities_by_type(files)
        group_order = list(groups.keys())
        
        # Content should come before Views, Views before Workflow
        assert group_order.index('Content') < group_order.index('Views')
        assert group_order.index('Views') < group_order.index('Workflow')
```

---

## Part 4: ARQ Worker Tests

### 4.1 Processing Worker Tests

```python
# tests/phase_4_processing/test_arq_jobs/test_processing_worker.py
import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from app.workers.processing_worker import generate_tickets_job
from app.services.exceptions import ProcessingError


class TestProcessingWorkerJob:
    """Test ARQ job function."""
    
    @pytest.fixture
    def arq_context(self, db_session):
        """Simulated ARQ worker context."""
        return {
            'async_session': lambda: db_session,
            'redis': AsyncMock(),
            'job_try': 1
        }
    
    async def test_job_creates_service_and_executes(self, arq_context):
        """Job should create service and call execute method."""
        session_id = uuid4()
        task_id = uuid4()
        
        with patch('app.workers.processing_worker.ProcessingService') as MockService:
            mock_service = AsyncMock()
            MockService.return_value = mock_service
            
            await generate_tickets_job(arq_context, session_id, task_id)
            
            mock_service.execute_ticket_generation.assert_called_once()
    
    async def test_job_publishes_progress(self, arq_context):
        """Job should publish progress to Redis."""
        session_id = uuid4()
        task_id = uuid4()
        
        with patch('app.workers.processing_worker.ProcessingService') as MockService:
            with patch('app.workers.processing_worker.publish_progress') as mock_publish:
                mock_service = AsyncMock()
                MockService.return_value = mock_service
                
                await generate_tickets_job(arq_context, session_id, task_id)
                
                # Verify progress callback was passed
                call_args = mock_service.execute_ticket_generation.call_args
                progress_callback = call_args[0][2]  # Third positional arg
                
                # Call the callback
                await progress_callback(50.0, 'Processing', {})
                
                mock_publish.assert_called()
    
    async def test_job_publishes_completion(self, arq_context):
        """Job should publish completion message."""
        session_id = uuid4()
        task_id = uuid4()
        
        with patch('app.workers.processing_worker.ProcessingService') as MockService:
            with patch('app.workers.processing_worker.publish_completion') as mock_complete:
                mock_service = AsyncMock()
                MockService.return_value = mock_service
                
                await generate_tickets_job(arq_context, session_id, task_id)
                
                mock_complete.assert_called_once()
    
    async def test_job_retries_on_temporary_error(self, arq_context):
        """Should retry for temporary errors."""
        session_id = uuid4()
        task_id = uuid4()
        
        with patch('app.workers.processing_worker.ProcessingService') as MockService:
            mock_service = AsyncMock()
            mock_service.execute_ticket_generation.side_effect = ProcessingError(
                message="LLM timeout",
                category="temporary"
            )
            MockService.return_value = mock_service
            
            from arq import Retry
            with pytest.raises(Retry):
                await generate_tickets_job(arq_context, session_id, task_id)
    
    async def test_job_records_failure_on_permanent_error(self, arq_context):
        """Should record failure for permanent errors."""
        session_id = uuid4()
        task_id = uuid4()
        
        with patch('app.workers.processing_worker.ProcessingService') as MockService:
            with patch('app.workers.processing_worker.record_job_failure') as mock_record:
                mock_service = AsyncMock()
                mock_service.execute_ticket_generation.side_effect = ProcessingError(
                    message="Invalid configuration",
                    category="admin_required"
                )
                MockService.return_value = mock_service
                
                await generate_tickets_job(arq_context, session_id, task_id)
                
                mock_record.assert_called_once()
```

---

## Part 5: Progress Tracking Tests

### 5.1 Progress Pub/Sub Tests

```python
# tests/phase_4_processing/test_progress_tracking.py
import pytest
from uuid import uuid4

from app.workers.utils import publish_progress, publish_completion, publish_error


class TestProgressPublishing:
    """Test progress publishing utilities."""
    
    async def test_publish_progress_sends_to_redis(self, mock_redis):
        """Should publish progress to Redis channel."""
        session_id = uuid4()
        task_id = uuid4()
        
        await publish_progress(
            ctx={'redis': mock_redis},
            session_id=session_id,
            task_id=task_id,
            operation='processing',
            percentage=50.0,
            stage='Generating tickets',
            details={'current': 5, 'total': 10}
        )
        
        mock_redis.publish.assert_called_once()
        call_args = mock_redis.publish.call_args
        channel = call_args[0][0]
        
        assert str(session_id) in channel
    
    async def test_publish_completion_sends_final_message(self, mock_redis):
        """Should publish completion message."""
        session_id = uuid4()
        task_id = uuid4()
        
        await publish_completion(
            ctx={'redis': mock_redis},
            session_id=session_id,
            task_id=task_id,
            operation='processing',
            results={'tickets_created': 10}
        )
        
        mock_redis.publish.assert_called_once()
        call_args = mock_redis.publish.call_args
        message = call_args[0][1]
        
        assert 'completed' in message.lower() or '"status"' in message
    
    async def test_publish_error_includes_category(self, mock_redis):
        """Should include error category in message."""
        session_id = uuid4()
        task_id = uuid4()
        
        from app.services.exceptions import ProcessingError
        error = ProcessingError(message="LLM failed", category="temporary")
        
        await publish_error(
            ctx={'redis': mock_redis},
            session_id=session_id,
            task_id=task_id,
            operation='processing',
            error=error
        )
        
        call_args = mock_redis.publish.call_args
        message = call_args[0][1]
        
        assert 'temporary' in message or 'category' in message
```

---

## Part 6: API Endpoint Tests

### 6.1 Processing Endpoint Tests

```python
# tests/phase_4_processing/test_api/test_processing_endpoints.py
import pytest
from httpx import AsyncClient
from uuid import uuid4

from app.main import app
from app.api.dependencies.auth import get_current_user
from app.api.dependencies.services import get_processing_service


class TestStartProcessingEndpoint:
    """Test POST /api/sessions/{session_id}/process."""
    
    async def test_start_processing_requires_auth(self):
        """Should require authentication."""
        session_id = uuid4()
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(f"/api/sessions/{session_id}/process")
        
        assert response.status_code == 401
    
    async def test_start_processing_success(self, mock_user, mock_processing_service):
        """Should start processing and return task ID."""
        session_id = uuid4()
        task_id = uuid4()
        
        mock_processing_service.generate_tickets.return_value = MagicMock(
            task_id=task_id,
            session_id=session_id,
            status='processing',
            estimated_tickets=10
        )
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_processing_service] = lambda: mock_processing_service
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                f"/api/sessions/{session_id}/process",
                headers={'Authorization': 'Bearer valid-token'}
            )
        
        assert response.status_code == 202  # Accepted
        data = response.json()
        assert data['task_id'] == str(task_id)
        assert data['status'] == 'processing'
        
        app.dependency_overrides.clear()


class TestProcessingStatusEndpoint:
    """Test GET /api/sessions/{session_id}/process/status."""
    
    async def test_get_status_returns_progress(self, mock_user, mock_processing_service):
        """Should return current processing status."""
        session_id = uuid4()
        
        mock_processing_service.get_processing_status.return_value = MagicMock(
            session_id=session_id,
            status='processing',
            progress_percentage=50.0,
            tickets_generated=5,
            estimated_total=10
        )
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_processing_service] = lambda: mock_processing_service
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                f"/api/sessions/{session_id}/process/status",
                headers={'Authorization': 'Bearer valid-token'}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data['progress_percentage'] == 50.0
        
        app.dependency_overrides.clear()


class TestCancelProcessingEndpoint:
    """Test POST /api/sessions/{session_id}/process/cancel."""
    
    async def test_cancel_processing(self, mock_user, mock_processing_service):
        """Should cancel running processing."""
        session_id = uuid4()
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_processing_service] = lambda: mock_processing_service
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                f"/api/sessions/{session_id}/process/cancel",
                headers={'Authorization': 'Bearer valid-token'}
            )
        
        assert response.status_code == 200
        mock_processing_service.cancel_processing.assert_called_with(session_id)
        
        app.dependency_overrides.clear()


class TestRetryProcessingEndpoint:
    """Test POST /api/sessions/{session_id}/process/retry."""
    
    async def test_retry_processing(self, mock_user, mock_processing_service):
        """Should retry failed processing."""
        session_id = uuid4()
        
        mock_processing_service.retry_processing.return_value = MagicMock(
            task_id=uuid4(),
            retry_attempt=2
        )
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_processing_service] = lambda: mock_processing_service
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                f"/api/sessions/{session_id}/process/retry",
                headers={'Authorization': 'Bearer valid-token'}
            )
        
        assert response.status_code == 202
        
        app.dependency_overrides.clear()
```

---

## Part 7: Implementation Specifications

### 7.1 LLMService

**File**: `/backend/app/integrations/llm/service.py`
- `validate_connectivity()` - Test provider connection
- `generate_ticket_content()` - Generate ticket from entity
- `_call_llm()` - Internal LLM API call with retry

### 7.2 ProcessingService

**File**: `/backend/app/services/processing_service.py`
- `generate_tickets()` - Public method: enqueue job
- `execute_ticket_generation()` - Internal: actual processing
- `get_processing_status()` - Get current status
- `retry_processing()` - Retry failed processing
- `cancel_processing()` - Set cancellation flag
- `_group_entities_by_type()` - Helper for grouping
- `_validate_llm_response()` - Helper for validation

### 7.3 ARQ Worker

**File**: `/backend/app/workers/processing_worker.py`
- `generate_tickets_job()` - ARQ job function

### 7.4 Worker Utilities

**File**: `/backend/app/workers/utils.py`
- `publish_progress()` - Redis progress publishing
- `publish_completion()` - Completion message
- `publish_error()` - Error notification
- `record_job_failure()` - Database failure recording

### 7.5 API Endpoints

**File**: `/backend/app/api/routes/processing.py`
- `POST /api/sessions/{id}/process` - Start processing
- `GET /api/sessions/{id}/process/status` - Get status
- `POST /api/sessions/{id}/process/cancel` - Cancel
- `POST /api/sessions/{id}/process/retry` - Retry

---

## Document References

### Primary References (in project knowledge)
- `processing_service_architecture_updated.md` - Service design
- `LLM_Service_Scope_and_Interface_Specification.md` - LLM interface
- `background_task_infrastructure.md` - ARQ patterns
- `fastapi_processing_endpoints.md` - API specifications
- `Task_Management_Architecture_Standardization.md` - Task patterns

---

## Success Criteria

### All Tests Pass
```bash
pytest tests/phase_4_processing/ -v --cov=app/services/processing_service --cov=app/integrations/llm --cov=app/workers --cov-report=term-missing
```

### Coverage Requirements
- LLMService: >80% coverage
- ProcessingService: >85% coverage
- ARQ workers: >80% coverage
- API endpoints: >80% coverage

### Verification Checklist
- [ ] LLM connectivity validation works
- [ ] LLM response validation catches invalid responses
- [ ] Job enqueue creates task and returns immediately
- [ ] Job execution generates tickets for all entities
- [ ] Progress callbacks are published to Redis
- [ ] Cancellation stops processing between entities
- [ ] Retry cleans up partial data before restarting
- [ ] Max retry limit (3) is enforced
- [ ] All API endpoints return correct schemas
- [ ] All Phase 4 tests pass

### Integration Testing
After unit tests pass:
1. Start Redis and ARQ worker
2. Upload UWEC CSV files to a session
3. Start processing â†’ Observe progress
4. Verify tickets created in database
5. Test cancellation mid-processing
6. Test retry after simulated failure

---

## Commands to Run

```bash
# Start Redis (Docker)
docker run -d -p 6379:6379 redis:alpine

# Run Phase 4 tests only
pytest tests/phase_4_processing/ -v

# Run with coverage
pytest tests/phase_4_processing/ -v --cov=app --cov-report=html

# Start ARQ worker (for integration tests)
arq app.workers.settings.WorkerSettings

# Test LLM connectivity (requires API keys)
pytest tests/phase_4_processing/test_llm_service.py -v -m integration
```
