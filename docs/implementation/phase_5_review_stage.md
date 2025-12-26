# Phase 5: Review Stage

## Overview
Implement ticket editing, dependency management, bulk operations, and ADF validation. This phase provides the user interface for reviewing and refining generated tickets before export.

**Estimated Effort**: 3-4 days  
**Prerequisites**: Phases 1-4 complete (models, auth, sessions, upload, processing)  
**Deliverables**: ReviewService, ticket CRUD endpoints, ADF validation worker, dependency graph

---

## Test-Driven Development Approach

### TDD Workflow for This Phase
1. Write unit tests for ticket update logic (including auto-attachment)
2. Write unit tests for dependency validation (circular detection)
3. Write unit tests for ADF validation triggering
4. Write tests for bulk operations
5. Write API endpoint tests
6. Implement code to make tests pass
7. Test full review workflow

---

## Part 1: Test Structure

### 1.1 Phase 5 Test Directory

```
tests/
â”œâ”€â”€ phase_5_review/
â”‚   â”œâ”€â”€ __init__.py
â”‚   â”œâ”€â”€ test_review_service.py
â”‚   â”œâ”€â”€ test_ticket_updates.py
â”‚   â”œâ”€â”€ test_auto_attachment.py
â”‚   â”œâ”€â”€ test_dependency_validation.py
â”‚   â”œâ”€â”€ test_adf_validation.py
â”‚   â”œâ”€â”€ test_bulk_operations.py
â”‚   â”œâ”€â”€ test_export_readiness.py
â”‚   â”œâ”€â”€ test_arq_jobs/
â”‚   â”‚   â”œâ”€â”€ __init__.py
â”‚   â”‚   â””â”€â”€ test_validation_worker.py
â”‚   â””â”€â”€ test_api/
â”‚       â”œâ”€â”€ __init__.py
â”‚       â”œâ”€â”€ test_ticket_endpoints.py
â”‚       â”œâ”€â”€ test_dependency_endpoints.py
â”‚       â””â”€â”€ test_validation_endpoints.py
```

### 1.2 Additional Fixtures (add to conftest.py)

```python
# tests/conftest.py - additions for Phase 5
import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def sample_ticket(db_session):
    """Create a sample ticket for testing."""
    async def _create(session_id, **overrides):
        ticket_data = {
            'session_id': session_id,
            'title': 'Configure Content Type: Article',
            'description': 'As a content editor...\n## Analysis\n...\n## Verification\n...',
            'entity_group': 'Content',
            'user_order': 1,
            'csv_source_files': [{'filename': 'bundles.csv', 'rows': [1]}],
            **overrides
        }
        ticket = Ticket(**ticket_data)
        db_session.add(ticket)
        await db_session.flush()
        return ticket
    return _create


@pytest.fixture
def sample_tickets(sample_ticket):
    """Create multiple tickets for testing."""
    async def _create(session_id, count=5):
        tickets = []
        for i in range(count):
            ticket = await sample_ticket(
                session_id,
                title=f'Ticket {i+1}',
                user_order=i+1
            )
            tickets.append(ticket)
        return tickets
    return _create


@pytest.fixture
def mock_review_service():
    """Mock ReviewService for API tests."""
    service = AsyncMock()
    service.get_tickets_summary.return_value = MagicMock(
        tickets=[],
        total=0,
        by_entity_group={}
    )
    service.update_ticket.return_value = MagicMock(
        ticket_id=uuid4(),
        updated_fields=['title']
    )
    return service


@pytest.fixture
def long_description():
    """Generate description over 30k characters."""
    return "x" * 35000


@pytest.fixture
def mock_jira_service_for_adf():
    """Mock JiraService for ADF validation."""
    service = AsyncMock()
    service.validate_adf_conversion.return_value = {
        'valid': True,
        'errors': []
    }
    return service
```

---

## Part 2: Ticket Update Tests

### 2.1 Ticket Update Tests

```python
# tests/phase_5_review/test_ticket_updates.py
import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

from app.services.review_service import ReviewService
from app.services.exceptions import ReviewError
from app.schemas.review import TicketUpdateRequest


class TestTicketUpdate:
    """Test ticket update functionality."""
    
    @pytest.fixture
    def service(self, mock_ticket_repository, mock_session_repository, 
                mock_error_repository, mock_jira_service):
        return ReviewService(
            ticket_repo=mock_ticket_repository,
            session_repo=mock_session_repository,
            error_repo=mock_error_repository,
            jira_service=mock_jira_service
        )
    
    async def test_update_ticket_title(self, service, mock_ticket_repository):
        """Should update ticket title."""
        session_id = uuid4()
        ticket_id = uuid4()
        
        mock_ticket_repository.get_ticket_by_id.return_value = MagicMock(
            id=ticket_id,
            session_id=session_id,
            title='Old Title'
        )
        
        request = TicketUpdateRequest(title='New Title')
        result = await service.update_ticket(session_id, ticket_id, request)
        
        mock_ticket_repository.update_ticket.assert_called()
        assert 'title' in result.updated_fields
    
    async def test_update_ticket_description(self, service, mock_ticket_repository):
        """Should update ticket description."""
        session_id = uuid4()
        ticket_id = uuid4()
        
        mock_ticket_repository.get_ticket_by_id.return_value = MagicMock(
            id=ticket_id,
            session_id=session_id,
            description='Old content'
        )
        
        request = TicketUpdateRequest(description='New content with more details')
        result = await service.update_ticket(session_id, ticket_id, request)
        
        assert 'description' in result.updated_fields
    
    async def test_update_ticket_invalidates_validation(
        self, service, mock_session_repository
    ):
        """Any content update should invalidate ADF validation."""
        session_id = uuid4()
        ticket_id = uuid4()
        
        request = TicketUpdateRequest(title='Changed Title')
        await service.update_ticket(session_id, ticket_id, request)
        
        mock_session_repository.invalidate_validation.assert_called_with(session_id)
    
    async def test_update_ticket_sets_updated_at(self, service, mock_ticket_repository):
        """Should update the updated_at timestamp."""
        session_id = uuid4()
        ticket_id = uuid4()
        
        mock_ticket = MagicMock(id=ticket_id, session_id=session_id)
        mock_ticket_repository.get_ticket_by_id.return_value = mock_ticket
        
        request = TicketUpdateRequest(title='New Title')
        await service.update_ticket(session_id, ticket_id, request)
        
        # Verify updated_at was set
        update_call = mock_ticket_repository.update_ticket.call_args
        assert 'updated_at' in update_call[1] or hasattr(mock_ticket, 'updated_at')
    
    async def test_update_ticket_not_found(self, service, mock_ticket_repository):
        """Should raise error for non-existent ticket."""
        mock_ticket_repository.get_ticket_by_id.return_value = None
        
        request = TicketUpdateRequest(title='New Title')
        with pytest.raises(ReviewError) as exc_info:
            await service.update_ticket(uuid4(), uuid4(), request)
        
        assert exc_info.value.category == 'user_fixable'
    
    async def test_update_ticket_wrong_session(self, service, mock_ticket_repository):
        """Should reject update if ticket belongs to different session."""
        session_id = uuid4()
        other_session_id = uuid4()
        ticket_id = uuid4()
        
        mock_ticket_repository.get_ticket_by_id.return_value = MagicMock(
            id=ticket_id,
            session_id=other_session_id
        )
        
        request = TicketUpdateRequest(title='New Title')
        with pytest.raises(ReviewError):
            await service.update_ticket(session_id, ticket_id, request)
```

### 2.2 Auto-Attachment Tests

```python
# tests/phase_5_review/test_auto_attachment.py
import pytest
from uuid import uuid4

from app.services.review_service import ReviewService
from app.schemas.review import TicketUpdateRequest


class TestAutoAttachment:
    """Test automatic attachment generation for oversized content."""
    
    @pytest.fixture
    def service(self, mock_ticket_repository, mock_session_repository, 
                mock_error_repository, mock_jira_service):
        return ReviewService(
            ticket_repo=mock_ticket_repository,
            session_repo=mock_session_repository,
            error_repo=mock_error_repository,
            jira_service=mock_jira_service
        )
    
    async def test_creates_attachment_when_over_30k(
        self, service, mock_ticket_repository, long_description
    ):
        """Should create attachment when description exceeds 30,000 chars."""
        session_id = uuid4()
        ticket_id = uuid4()
        
        mock_ticket_repository.get_ticket_by_id.return_value = MagicMock(
            id=ticket_id,
            session_id=session_id,
            description='short',
            attachment=None
        )
        
        request = TicketUpdateRequest(description=long_description)
        result = await service.update_ticket(session_id, ticket_id, request)
        
        assert result.attachment_created is True
        mock_ticket_repository.create_attachment.assert_called()
    
    async def test_attachment_contains_full_content(
        self, service, mock_ticket_repository, long_description
    ):
        """Attachment should contain the full original content."""
        session_id = uuid4()
        ticket_id = uuid4()
        
        mock_ticket_repository.get_ticket_by_id.return_value = MagicMock(
            id=ticket_id,
            session_id=session_id,
            description='short',
            attachment=None
        )
        
        request = TicketUpdateRequest(description=long_description)
        await service.update_ticket(session_id, ticket_id, request)
        
        # Check attachment content
        create_call = mock_ticket_repository.create_attachment.call_args
        attachment_content = create_call[1]['content']
        assert attachment_content == long_description
    
    async def test_description_replaced_with_reference(
        self, service, mock_ticket_repository, long_description
    ):
        """Description should be replaced with attachment reference."""
        session_id = uuid4()
        ticket_id = uuid4()
        
        mock_ticket_repository.get_ticket_by_id.return_value = MagicMock(
            id=ticket_id,
            session_id=session_id,
            description='short',
            attachment=None
        )
        
        request = TicketUpdateRequest(description=long_description)
        await service.update_ticket(session_id, ticket_id, request)
        
        # Check that description was truncated
        update_call = mock_ticket_repository.update_ticket.call_args
        new_description = update_call[1].get('description', '')
        
        assert len(new_description) < 30000
        assert 'attachment' in new_description.lower() or 'see attached' in new_description.lower()
    
    async def test_updates_existing_attachment(
        self, service, mock_ticket_repository, long_description
    ):
        """Should update existing attachment if one exists."""
        session_id = uuid4()
        ticket_id = uuid4()
        attachment_id = uuid4()
        
        mock_ticket_repository.get_ticket_by_id.return_value = MagicMock(
            id=ticket_id,
            session_id=session_id,
            attachment=MagicMock(id=attachment_id)
        )
        
        request = TicketUpdateRequest(description=long_description)
        await service.update_ticket(session_id, ticket_id, request)
        
        mock_ticket_repository.update_attachment.assert_called()
    
    async def test_no_attachment_under_30k(self, service, mock_ticket_repository):
        """Should not create attachment for content under 30k."""
        session_id = uuid4()
        ticket_id = uuid4()
        short_description = "x" * 1000
        
        mock_ticket_repository.get_ticket_by_id.return_value = MagicMock(
            id=ticket_id,
            session_id=session_id,
            description='old',
            attachment=None
        )
        
        request = TicketUpdateRequest(description=short_description)
        result = await service.update_ticket(session_id, ticket_id, request)
        
        assert result.attachment_created is False
        mock_ticket_repository.create_attachment.assert_not_called()
```

---

## Part 3: Dependency Validation Tests

### 3.1 Dependency Validation Tests

```python
# tests/phase_5_review/test_dependency_validation.py
import pytest
from uuid import uuid4

from app.services.review_service import ReviewService
from app.services.exceptions import ReviewError


class TestCircularDependencyDetection:
    """Test circular dependency detection."""
    
    @pytest.fixture
    def service(self, mock_ticket_repository, mock_session_repository, 
                mock_error_repository, mock_jira_service):
        return ReviewService(
            ticket_repo=mock_ticket_repository,
            session_repo=mock_session_repository,
            error_repo=mock_error_repository,
            jira_service=mock_jira_service
        )
    
    async def test_allows_valid_dependency(self, service, mock_ticket_repository):
        """Should allow valid non-circular dependency."""
        session_id = uuid4()
        ticket_a = uuid4()
        ticket_b = uuid4()
        
        # A depends on B (valid - B has no dependencies)
        mock_ticket_repository.get_ticket_dependencies.return_value = []
        
        result = await service.add_dependency(session_id, ticket_a, ticket_b)
        
        assert result.valid is True
        mock_ticket_repository.create_dependency.assert_called()
    
    async def test_detects_direct_circular(self, service, mock_ticket_repository):
        """Should detect A->B->A circular dependency."""
        session_id = uuid4()
        ticket_a = uuid4()
        ticket_b = uuid4()
        
        # B already depends on A
        mock_ticket_repository.get_ticket_dependencies.return_value = [
            MagicMock(ticket_id=ticket_b, depends_on_ticket_id=ticket_a)
        ]
        
        result = await service.add_dependency(session_id, ticket_a, ticket_b)
        
        assert result.valid is False
        assert 'circular' in result.error.lower()
    
    async def test_detects_indirect_circular(self, service, mock_ticket_repository):
        """Should detect A->B->C->A circular dependency."""
        session_id = uuid4()
        ticket_a = uuid4()
        ticket_b = uuid4()
        ticket_c = uuid4()
        
        # Current state: B->C, C->A
        # Attempting to add A->B would create circle
        def get_deps(tid):
            if tid == ticket_b:
                return [MagicMock(depends_on_ticket_id=ticket_c)]
            elif tid == ticket_c:
                return [MagicMock(depends_on_ticket_id=ticket_a)]
            return []
        
        mock_ticket_repository.get_ticket_dependencies.side_effect = get_deps
        
        result = await service.add_dependency(session_id, ticket_a, ticket_b)
        
        assert result.valid is False
    
    async def test_self_reference_rejected(self, service):
        """Should reject ticket depending on itself."""
        session_id = uuid4()
        ticket_a = uuid4()
        
        result = await service.add_dependency(session_id, ticket_a, ticket_a)
        
        assert result.valid is False
        assert 'self' in result.error.lower() or 'itself' in result.error.lower()


class TestDependencyGraph:
    """Test dependency graph generation."""
    
    @pytest.fixture
    def service(self, mock_ticket_repository, mock_session_repository, 
                mock_error_repository, mock_jira_service):
        return ReviewService(
            ticket_repo=mock_ticket_repository,
            session_repo=mock_session_repository,
            error_repo=mock_error_repository,
            jira_service=mock_jira_service
        )
    
    async def test_get_dependency_graph(self, service, mock_ticket_repository):
        """Should return dependency graph structure."""
        session_id = uuid4()
        
        mock_ticket_repository.get_tickets_with_dependencies.return_value = [
            MagicMock(id=uuid4(), title='Ticket A', dependencies=[]),
            MagicMock(id=uuid4(), title='Ticket B', dependencies=[])
        ]
        
        result = await service.get_dependency_graph(session_id)
        
        assert 'nodes' in result
        assert 'edges' in result
    
    async def test_graph_includes_entity_groups(self, service, mock_ticket_repository):
        """Graph nodes should include entity group info."""
        session_id = uuid4()
        
        mock_ticket_repository.get_tickets_with_dependencies.return_value = [
            MagicMock(id=uuid4(), title='Ticket A', entity_group='Content', dependencies=[])
        ]
        
        result = await service.get_dependency_graph(session_id)
        
        assert result['nodes'][0]['entity_group'] == 'Content'
```

---

## Part 4: ADF Validation Tests

### 4.1 ADF Validation Tests

```python
# tests/phase_5_review/test_adf_validation.py
import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

from app.services.review_service import ReviewService
from app.services.exceptions import ReviewError


class TestAdfValidationEnqueue:
    """Test ADF validation job enqueueing."""
    
    @pytest.fixture
    def service(self, mock_ticket_repository, mock_session_repository, 
                mock_error_repository, mock_jira_service, mock_arq_pool):
        return ReviewService(
            ticket_repo=mock_ticket_repository,
            session_repo=mock_session_repository,
            error_repo=mock_error_repository,
            jira_service=mock_jira_service,
            arq_pool=mock_arq_pool
        )
    
    async def test_validate_adf_enqueues_job(self, service, mock_arq_pool):
        """Should enqueue ADF validation job."""
        session_id = uuid4()
        
        result = await service.validate_adf(session_id)
        
        mock_arq_pool.enqueue_job.assert_called_with(
            'validate_adf_job',
            session_id=session_id,
            task_id=result.task_id
        )
    
    async def test_validate_adf_returns_ticket_count(
        self, service, mock_ticket_repository
    ):
        """Should return total ticket count for progress estimation."""
        session_id = uuid4()
        mock_ticket_repository.count_session_tickets.return_value = 25
        
        result = await service.validate_adf(session_id)
        
        assert result.total_tickets == 25


class TestAdfValidationExecution:
    """Test ADF validation execution."""
    
    @pytest.fixture
    def service(self, mock_ticket_repository, mock_session_repository, 
                mock_error_repository, mock_jira_service_for_adf):
        return ReviewService(
            ticket_repo=mock_ticket_repository,
            session_repo=mock_session_repository,
            error_repo=mock_error_repository,
            jira_service=mock_jira_service_for_adf
        )
    
    async def test_execute_validates_all_tickets(
        self, service, mock_ticket_repository, mock_jira_service_for_adf, 
        mock_progress_callback
    ):
        """Should validate ADF for all tickets."""
        session_id = uuid4()
        task_id = uuid4()
        
        mock_ticket_repository.get_session_tickets.return_value = [
            MagicMock(id=uuid4(), description='Ticket 1 content'),
            MagicMock(id=uuid4(), description='Ticket 2 content')
        ]
        
        await service.execute_adf_validation(session_id, task_id, mock_progress_callback)
        
        assert mock_jira_service_for_adf.validate_adf_conversion.call_count == 2
    
    async def test_execute_records_failures(
        self, service, mock_ticket_repository, mock_jira_service_for_adf,
        mock_session_repository, mock_progress_callback
    ):
        """Should record validation failures."""
        session_id = uuid4()
        task_id = uuid4()
        
        mock_ticket_repository.get_session_tickets.return_value = [
            MagicMock(id=uuid4(), description='Valid content'),
            MagicMock(id=uuid4(), description='Invalid <content>')
        ]
        
        mock_jira_service_for_adf.validate_adf_conversion.side_effect = [
            {'valid': True, 'errors': []},
            {'valid': False, 'errors': ['Invalid markup']}
        ]
        
        await service.execute_adf_validation(session_id, task_id, mock_progress_callback)
        
        # Validation should complete with failure recorded
        complete_call = mock_session_repository.complete_validation.call_args
        assert complete_call[1]['passed'] is False
    
    async def test_execute_publishes_progress(
        self, service, mock_ticket_repository, mock_progress_callback
    ):
        """Should publish progress for each ticket."""
        session_id = uuid4()
        task_id = uuid4()
        
        mock_ticket_repository.get_session_tickets.return_value = [
            MagicMock(id=uuid4(), description='Content 1'),
            MagicMock(id=uuid4(), description='Content 2')
        ]
        
        await service.execute_adf_validation(session_id, task_id, mock_progress_callback)
        
        assert len(mock_progress_callback.calls) >= 2


class TestValidationInvalidation:
    """Test validation invalidation on ticket edit."""
    
    @pytest.fixture
    def service(self, mock_ticket_repository, mock_session_repository, 
                mock_error_repository, mock_jira_service):
        return ReviewService(
            ticket_repo=mock_ticket_repository,
            session_repo=mock_session_repository,
            error_repo=mock_error_repository,
            jira_service=mock_jira_service
        )
    
    async def test_ticket_edit_invalidates_validation(
        self, service, mock_session_repository
    ):
        """Editing ticket should invalidate existing validation."""
        session_id = uuid4()
        ticket_id = uuid4()
        
        request = TicketUpdateRequest(description='Changed content')
        await service.update_ticket(session_id, ticket_id, request)
        
        mock_session_repository.invalidate_validation.assert_called_with(session_id)
    
    async def test_invalidation_sets_timestamp(self, service, mock_session_repository):
        """Invalidation should set last_invalidated_at."""
        session_id = uuid4()
        
        await service.update_ticket(session_id, uuid4(), TicketUpdateRequest(title='New'))
        
        # Verify invalidation was called
        mock_session_repository.invalidate_validation.assert_called()
```

---

## Part 5: Bulk Operations Tests

### 5.1 Bulk Operations Tests

```python
# tests/phase_5_review/test_bulk_operations.py
import pytest
from uuid import uuid4

from app.services.review_service import ReviewService
from app.schemas.review import BulkAssignRequest


class TestBulkAssignment:
    """Test bulk ticket assignment."""
    
    @pytest.fixture
    def service(self, mock_ticket_repository, mock_session_repository, 
                mock_error_repository, mock_jira_service):
        return ReviewService(
            ticket_repo=mock_ticket_repository,
            session_repo=mock_session_repository,
            error_repo=mock_error_repository,
            jira_service=mock_jira_service
        )
    
    async def test_bulk_assign_sprint(self, service, mock_ticket_repository):
        """Should assign sprint to multiple tickets."""
        session_id = uuid4()
        ticket_ids = [uuid4(), uuid4(), uuid4()]
        
        request = BulkAssignRequest(
            ticket_ids=ticket_ids,
            sprint='Sprint 5'
        )
        
        result = await service.bulk_assign_tickets(session_id, request)
        
        assert result.updated_count == 3
        mock_ticket_repository.bulk_update.assert_called()
    
    async def test_bulk_assign_assignee(self, service, mock_ticket_repository):
        """Should assign assignee to multiple tickets."""
        session_id = uuid4()
        ticket_ids = [uuid4(), uuid4()]
        
        request = BulkAssignRequest(
            ticket_ids=ticket_ids,
            assignee='user-123'
        )
        
        result = await service.bulk_assign_tickets(session_id, request)
        
        assert result.updated_count == 2
    
    async def test_bulk_assign_validates_ticket_ownership(
        self, service, mock_ticket_repository
    ):
        """Should only update tickets belonging to session."""
        session_id = uuid4()
        valid_ticket = uuid4()
        other_session_ticket = uuid4()
        
        mock_ticket_repository.get_tickets_by_ids.return_value = [
            MagicMock(id=valid_ticket, session_id=session_id),
            MagicMock(id=other_session_ticket, session_id=uuid4())  # Different session
        ]
        
        request = BulkAssignRequest(
            ticket_ids=[valid_ticket, other_session_ticket],
            sprint='Sprint 5'
        )
        
        result = await service.bulk_assign_tickets(session_id, request)
        
        assert result.updated_count == 1
        assert len(result.skipped) == 1


class TestTicketOrdering:
    """Test ticket ordering within entity groups."""
    
    @pytest.fixture
    def service(self, mock_ticket_repository, mock_session_repository, 
                mock_error_repository, mock_jira_service):
        return ReviewService(
            ticket_repo=mock_ticket_repository,
            session_repo=mock_session_repository,
            error_repo=mock_error_repository,
            jira_service=mock_jira_service
        )
    
    async def test_update_ordering(self, service, mock_ticket_repository):
        """Should update user_order for reordered tickets."""
        session_id = uuid4()
        ticket_ids = [uuid4(), uuid4(), uuid4()]
        
        request = TicketOrderingRequest(
            entity_group='Content',
            ticket_order=ticket_ids  # New order
        )
        
        await service.update_ticket_ordering(session_id, request)
        
        mock_ticket_repository.update_ordering.assert_called()
    
    async def test_ordering_validates_entity_group(
        self, service, mock_ticket_repository
    ):
        """Should validate all tickets belong to specified entity group."""
        session_id = uuid4()
        
        # One ticket is in wrong group
        mock_ticket_repository.get_tickets_by_ids.return_value = [
            MagicMock(entity_group='Content'),
            MagicMock(entity_group='Views')  # Wrong group
        ]
        
        request = TicketOrderingRequest(
            entity_group='Content',
            ticket_order=[uuid4(), uuid4()]
        )
        
        with pytest.raises(ReviewError):
            await service.update_ticket_ordering(session_id, request)
```

---

## Part 6: Export Readiness Tests

### 6.1 Export Readiness Tests

```python
# tests/phase_5_review/test_export_readiness.py
import pytest
from uuid import uuid4
from datetime import datetime, timedelta

from app.services.review_service import ReviewService


class TestExportReadiness:
    """Test export readiness checks."""
    
    @pytest.fixture
    def service(self, mock_ticket_repository, mock_session_repository, 
                mock_error_repository, mock_jira_service):
        return ReviewService(
            ticket_repo=mock_ticket_repository,
            session_repo=mock_session_repository,
            error_repo=mock_error_repository,
            jira_service=mock_jira_service
        )
    
    async def test_ready_when_all_conditions_met(
        self, service, mock_session_repository, mock_ticket_repository
    ):
        """Should be ready when validation passed and no blockers."""
        session_id = uuid4()
        
        mock_session_repository.get_session_validation.return_value = MagicMock(
            validation_passed=True,
            last_validated_at=datetime.utcnow(),
            last_invalidated_at=None
        )
        mock_ticket_repository.count_ready_tickets.return_value = 10
        mock_ticket_repository.count_session_tickets.return_value = 10
        
        result = await service.check_export_readiness(session_id)
        
        assert result.ready is True
    
    async def test_not_ready_without_validation(
        self, service, mock_session_repository
    ):
        """Should not be ready if validation not run."""
        session_id = uuid4()
        
        mock_session_repository.get_session_validation.return_value = None
        
        result = await service.check_export_readiness(session_id)
        
        assert result.ready is False
        assert 'validation' in result.blockers[0].lower()
    
    async def test_not_ready_when_validation_failed(
        self, service, mock_session_repository
    ):
        """Should not be ready if validation failed."""
        session_id = uuid4()
        
        mock_session_repository.get_session_validation.return_value = MagicMock(
            validation_passed=False
        )
        
        result = await service.check_export_readiness(session_id)
        
        assert result.ready is False
    
    async def test_not_ready_when_validation_stale(
        self, service, mock_session_repository
    ):
        """Should not be ready if tickets edited after validation."""
        session_id = uuid4()
        
        validated_time = datetime.utcnow() - timedelta(hours=1)
        invalidated_time = datetime.utcnow()  # After validation
        
        mock_session_repository.get_session_validation.return_value = MagicMock(
            validation_passed=True,
            last_validated_at=validated_time,
            last_invalidated_at=invalidated_time
        )
        
        result = await service.check_export_readiness(session_id)
        
        assert result.ready is False
        assert 'stale' in result.blockers[0].lower() or 'modified' in result.blockers[0].lower()
    
    async def test_reports_unready_tickets(
        self, service, mock_session_repository, mock_ticket_repository
    ):
        """Should report tickets not marked ready."""
        session_id = uuid4()
        
        mock_session_repository.get_session_validation.return_value = MagicMock(
            validation_passed=True,
            last_validated_at=datetime.utcnow(),
            last_invalidated_at=None
        )
        mock_ticket_repository.count_ready_tickets.return_value = 8
        mock_ticket_repository.count_session_tickets.return_value = 10
        
        result = await service.check_export_readiness(session_id)
        
        assert result.ready is False
        assert '2' in result.blockers[0] or 'not ready' in result.blockers[0].lower()
```

---

## Part 7: API Endpoint Tests

```python
# tests/phase_5_review/test_api/test_ticket_endpoints.py
import pytest
from httpx import AsyncClient
from uuid import uuid4

from app.main import app
from app.api.dependencies.auth import get_current_user
from app.api.dependencies.services import get_review_service


class TestGetTicketsEndpoint:
    """Test GET /api/sessions/{session_id}/tickets."""
    
    async def test_get_tickets_list(self, mock_user, mock_review_service):
        """Should return paginated ticket list."""
        session_id = uuid4()
        
        mock_review_service.get_tickets_summary.return_value = MagicMock(
            tickets=[
                {'ticket_id': str(uuid4()), 'title': 'Ticket 1'},
                {'ticket_id': str(uuid4()), 'title': 'Ticket 2'}
            ],
            total=2,
            by_entity_group={'Content': 2}
        )
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_review_service] = lambda: mock_review_service
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                f"/api/sessions/{session_id}/tickets",
                headers={'Authorization': 'Bearer valid-token'}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data['tickets']) == 2
        
        app.dependency_overrides.clear()


class TestUpdateTicketEndpoint:
    """Test PUT /api/sessions/{session_id}/tickets/{ticket_id}."""
    
    async def test_update_ticket(self, mock_user, mock_review_service):
        """Should update ticket and return result."""
        session_id = uuid4()
        ticket_id = uuid4()
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_review_service] = lambda: mock_review_service
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.put(
                f"/api/sessions/{session_id}/tickets/{ticket_id}",
                json={'title': 'Updated Title'},
                headers={'Authorization': 'Bearer valid-token'}
            )
        
        assert response.status_code == 200
        mock_review_service.update_ticket.assert_called()
        
        app.dependency_overrides.clear()


class TestAdfValidationEndpoint:
    """Test POST /api/sessions/{session_id}/validate."""
    
    async def test_start_validation(self, mock_user, mock_review_service):
        """Should start ADF validation."""
        session_id = uuid4()
        
        mock_review_service.validate_adf.return_value = MagicMock(
            task_id=uuid4(),
            total_tickets=10
        )
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_review_service] = lambda: mock_review_service
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                f"/api/sessions/{session_id}/validate",
                headers={'Authorization': 'Bearer valid-token'}
            )
        
        assert response.status_code == 202
        
        app.dependency_overrides.clear()
```

---

## Document References

### Primary References (in project knowledge)
- `review_service_architecture_updated.md` - Service design with ARQ
- `Missing_Response_Models_-_Complete_Specifications.md` - Response models
- `fastapi_processing_endpoints.md` - API patterns (similar structure)

---

## Success Criteria

### All Tests Pass
```bash
pytest tests/phase_5_review/ -v --cov=app/services/review_service --cov-report=term-missing
```

### Coverage Requirements
- ReviewService: >85% coverage
- Dependency validation: >90% coverage
- API endpoints: >80% coverage

### Verification Checklist
- [ ] Ticket updates work correctly
- [ ] Auto-attachment triggers at 30k characters
- [ ] Circular dependency detection works
- [ ] ADF validation enqueues job
- [ ] ADF validation execution tests all tickets
- [ ] Validation invalidation works on ticket edit
- [ ] Bulk operations update correct tickets
- [ ] Export readiness checks all conditions
- [ ] All Phase 5 tests pass

---

## Commands to Run

```bash
# Run Phase 5 tests only
pytest tests/phase_5_review/ -v

# Run with coverage
pytest tests/phase_5_review/ -v --cov=app --cov-report=html
```
