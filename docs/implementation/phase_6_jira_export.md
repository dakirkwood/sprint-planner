# Phase 6: Jira Export

## Overview
Implement the final stage: exporting tickets to Jira with dependency linking, attachment uploads, manual fix tracking, and comprehensive error handling. This phase completes the workflow by creating real Jira tickets.

**Estimated Effort**: 3-4 days  
**Prerequisites**: Phases 1-5 complete (full review workflow functional)  
**Deliverables**: ExportService, Jira ticket creation, dependency linking, export worker

---

## Test-Driven Development Approach

### TDD Workflow for This Phase
1. Write unit tests for validation staleness check
2. Write unit tests for dependency ordering algorithm
3. Write unit tests for ExportService orchestration
4. Write integration tests for Jira API calls (mocked)
5. Write tests for manual fix tracking
6. Write API endpoint tests
7. Implement code to make tests pass
8. End-to-end test with Jira sandbox

---

## Part 1: Test Structure

### 1.1 Phase 6 Test Directory

```
tests/
â”œâ”€â”€ phase_6_export/
â”‚   â”œâ”€â”€ __init__.py
â”‚   â”œâ”€â”€ test_export_service.py
â”‚   â”œâ”€â”€ test_validation_staleness.py
â”‚   â”œâ”€â”€ test_dependency_ordering.py
â”‚   â”œâ”€â”€ test_jira_ticket_creation.py
â”‚   â”œâ”€â”€ test_attachment_upload.py
â”‚   â”œâ”€â”€ test_dependency_linking.py
â”‚   â”œâ”€â”€ test_manual_fix_tracking.py
â”‚   â”œâ”€â”€ test_export_resume.py
â”‚   â”œâ”€â”€ test_arq_jobs/
â”‚   â”‚   â”œâ”€â”€ __init__.py
â”‚   â”‚   â””â”€â”€ test_export_worker.py
â”‚   â””â”€â”€ test_api/
â”‚       â”œâ”€â”€ __init__.py
â”‚       â””â”€â”€ test_export_endpoints.py
```

### 1.2 Additional Fixtures (add to conftest.py)

```python
# tests/conftest.py - additions for Phase 6
import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta


@pytest.fixture
def mock_jira_service_for_export():
    """Mock JiraService configured for export operations."""
    service = AsyncMock()
    
    # Default successful ticket creation
    service.create_ticket.return_value = {
        'key': 'TEST-123',
        'id': '10001',
        'self': 'https://test.atlassian.net/rest/api/3/issue/10001'
    }
    
    # Default successful attachment upload
    service.upload_attachment.return_value = {
        'id': 'att-123',
        'filename': 'details.md',
        'self': 'https://test.atlassian.net/rest/api/3/attachment/att-123'
    }
    
    # Default successful link creation
    service.create_issue_link.return_value = {'id': 'link-123'}
    
    return service


@pytest.fixture
def session_with_validated_tickets(db_session, sample_session_data):
    """Create session with validated tickets ready for export."""
    async def _create(ticket_count=5):
        # Create session
        session = Session(**sample_session_data)
        db_session.add(session)
        await db_session.flush()
        
        # Create validation record (passed)
        validation = SessionValidation(
            session_id=session.id,
            validation_passed=True,
            last_validated_at=datetime.utcnow(),
            last_invalidated_at=None
        )
        db_session.add(validation)
        
        # Create tickets
        tickets = []
        for i in range(ticket_count):
            ticket = Ticket(
                session_id=session.id,
                title=f'Ticket {i+1}',
                description=f'Description for ticket {i+1}',
                entity_group='Content',
                user_order=i+1,
                ready_for_jira=True
            )
            db_session.add(ticket)
            tickets.append(ticket)
        
        await db_session.flush()
        return session, tickets
    
    return _create


@pytest.fixture
def tickets_with_dependencies(session_with_validated_tickets, db_session):
    """Create tickets with dependency chain: A -> B -> C."""
    async def _create():
        session, tickets = await session_with_validated_tickets(3)
        
        # tickets[0] depends on tickets[1]
        # tickets[1] depends on tickets[2]
        dep1 = TicketDependency(
            ticket_id=tickets[0].id,
            depends_on_ticket_id=tickets[1].id
        )
        dep2 = TicketDependency(
            ticket_id=tickets[1].id,
            depends_on_ticket_id=tickets[2].id
        )
        db_session.add(dep1)
        db_session.add(dep2)
        await db_session.flush()
        
        return session, tickets
    
    return _create


@pytest.fixture
def mock_export_repository():
    """Mock repository for export operations."""
    repo = AsyncMock()
    repo.get_export_progress.return_value = None
    repo.save_export_progress.return_value = None
    repo.record_manual_fix.return_value = None
    return repo
```

---

## Part 2: Validation Staleness Tests

### 2.1 Validation Staleness Check Tests

```python
# tests/phase_6_export/test_validation_staleness.py
import pytest
from uuid import uuid4
from datetime import datetime, timedelta

from app.services.export_service import ExportService
from app.services.exceptions import ExportError


class TestValidationStalenessCheck:
    """Test validation staleness before export."""
    
    @pytest.fixture
    def service(self, mock_session_repository, mock_ticket_repository,
                mock_jira_service_for_export, mock_arq_pool):
        return ExportService(
            session_repo=mock_session_repository,
            ticket_repo=mock_ticket_repository,
            jira_service=mock_jira_service_for_export,
            arq_pool=mock_arq_pool
        )
    
    async def test_allows_export_when_validation_fresh(
        self, service, mock_session_repository
    ):
        """Should allow export when validation is current."""
        session_id = uuid4()
        
        mock_session_repository.get_session_validation.return_value = MagicMock(
            validation_passed=True,
            last_validated_at=datetime.utcnow(),
            last_invalidated_at=None
        )
        mock_session_repository.is_export_ready.return_value = True
        
        # Should not raise
        result = await service.export_session(session_id)
        assert result.task_id is not None
    
    async def test_blocks_export_when_never_validated(
        self, service, mock_session_repository
    ):
        """Should block export if validation never run."""
        session_id = uuid4()
        
        mock_session_repository.get_session_validation.return_value = None
        
        with pytest.raises(ExportError) as exc_info:
            await service.export_session(session_id)
        
        assert exc_info.value.category == 'user_fixable'
        assert 'validation' in exc_info.value.message.lower()
    
    async def test_blocks_export_when_validation_failed(
        self, service, mock_session_repository
    ):
        """Should block export if validation failed."""
        session_id = uuid4()
        
        mock_session_repository.get_session_validation.return_value = MagicMock(
            validation_passed=False,
            last_validated_at=datetime.utcnow()
        )
        
        with pytest.raises(ExportError) as exc_info:
            await service.export_session(session_id)
        
        assert exc_info.value.category == 'user_fixable'
    
    async def test_blocks_export_when_validation_stale(
        self, service, mock_session_repository
    ):
        """Should block when last_invalidated_at > last_validated_at."""
        session_id = uuid4()
        
        validated_time = datetime.utcnow() - timedelta(hours=2)
        invalidated_time = datetime.utcnow() - timedelta(hours=1)  # After validation
        
        mock_session_repository.get_session_validation.return_value = MagicMock(
            validation_passed=True,
            last_validated_at=validated_time,
            last_invalidated_at=invalidated_time
        )
        
        with pytest.raises(ExportError) as exc_info:
            await service.export_session(session_id)
        
        assert exc_info.value.category == 'user_fixable'
        assert 're-validation' in exc_info.value.message.lower() or 'stale' in exc_info.value.message.lower()
    
    async def test_allows_export_when_validated_after_invalidation(
        self, service, mock_session_repository
    ):
        """Should allow when validated after last invalidation."""
        session_id = uuid4()
        
        invalidated_time = datetime.utcnow() - timedelta(hours=2)
        validated_time = datetime.utcnow() - timedelta(hours=1)  # After invalidation
        
        mock_session_repository.get_session_validation.return_value = MagicMock(
            validation_passed=True,
            last_validated_at=validated_time,
            last_invalidated_at=invalidated_time
        )
        mock_session_repository.is_export_ready.return_value = True
        
        # Should not raise
        result = await service.export_session(session_id)
        assert result.task_id is not None
```

---

## Part 3: Dependency Ordering Tests

### 3.1 Topological Sort Tests

```python
# tests/phase_6_export/test_dependency_ordering.py
import pytest
from uuid import uuid4
from unittest.mock import MagicMock

from app.services.export_service import _order_tickets_for_export


class TestDependencyOrdering:
    """Test topological sort for export ordering."""
    
    def test_orders_independent_tickets_by_user_order(self):
        """Tickets without dependencies should be ordered by user_order."""
        tickets = [
            MagicMock(id=uuid4(), user_order=3, dependencies=[]),
            MagicMock(id=uuid4(), user_order=1, dependencies=[]),
            MagicMock(id=uuid4(), user_order=2, dependencies=[])
        ]
        
        ordered = _order_tickets_for_export(tickets)
        
        orders = [t.user_order for t in ordered]
        assert orders == [1, 2, 3]
    
    def test_dependency_comes_before_dependent(self):
        """Dependency must be exported before dependent ticket."""
        ticket_a = MagicMock(id=uuid4(), user_order=1)
        ticket_b = MagicMock(id=uuid4(), user_order=2)
        
        # A depends on B
        ticket_a.dependencies = [MagicMock(depends_on_ticket_id=ticket_b.id)]
        ticket_b.dependencies = []
        
        ordered = _order_tickets_for_export([ticket_a, ticket_b])
        
        ordered_ids = [t.id for t in ordered]
        assert ordered_ids.index(ticket_b.id) < ordered_ids.index(ticket_a.id)
    
    def test_chain_ordering(self):
        """Chain A->B->C should export as C, B, A."""
        ticket_a = MagicMock(id=uuid4(), user_order=1)
        ticket_b = MagicMock(id=uuid4(), user_order=2)
        ticket_c = MagicMock(id=uuid4(), user_order=3)
        
        # A depends on B, B depends on C
        ticket_a.dependencies = [MagicMock(depends_on_ticket_id=ticket_b.id)]
        ticket_b.dependencies = [MagicMock(depends_on_ticket_id=ticket_c.id)]
        ticket_c.dependencies = []
        
        ordered = _order_tickets_for_export([ticket_a, ticket_b, ticket_c])
        
        ordered_ids = [t.id for t in ordered]
        assert ordered_ids.index(ticket_c.id) < ordered_ids.index(ticket_b.id)
        assert ordered_ids.index(ticket_b.id) < ordered_ids.index(ticket_a.id)
    
    def test_multiple_dependencies(self):
        """Ticket with multiple dependencies waits for all."""
        ticket_a = MagicMock(id=uuid4(), user_order=1)
        ticket_b = MagicMock(id=uuid4(), user_order=2)
        ticket_c = MagicMock(id=uuid4(), user_order=3)
        
        # A depends on both B and C
        ticket_a.dependencies = [
            MagicMock(depends_on_ticket_id=ticket_b.id),
            MagicMock(depends_on_ticket_id=ticket_c.id)
        ]
        ticket_b.dependencies = []
        ticket_c.dependencies = []
        
        ordered = _order_tickets_for_export([ticket_a, ticket_b, ticket_c])
        
        ordered_ids = [t.id for t in ordered]
        # A should be last
        assert ordered_ids[-1] == ticket_a.id
    
    def test_preserves_user_order_within_same_level(self):
        """Same-level tickets should maintain user_order."""
        ticket_parent = MagicMock(id=uuid4(), user_order=3)
        ticket_child_1 = MagicMock(id=uuid4(), user_order=1)
        ticket_child_2 = MagicMock(id=uuid4(), user_order=2)
        
        # Both children depend on parent
        ticket_child_1.dependencies = [MagicMock(depends_on_ticket_id=ticket_parent.id)]
        ticket_child_2.dependencies = [MagicMock(depends_on_ticket_id=ticket_parent.id)]
        ticket_parent.dependencies = []
        
        ordered = _order_tickets_for_export([ticket_child_2, ticket_child_1, ticket_parent])
        
        # Parent first, then children by user_order
        ordered_ids = [t.id for t in ordered]
        assert ordered_ids[0] == ticket_parent.id
        child_indices = [ordered_ids.index(ticket_child_1.id), ordered_ids.index(ticket_child_2.id)]
        assert child_indices[0] < child_indices[1]  # child_1 before child_2
```

---

## Part 4: Export Service Tests

### 4.1 ExportService Unit Tests

```python
# tests/phase_6_export/test_export_service.py
import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

from app.services.export_service import ExportService
from app.services.exceptions import ExportError


class TestExportServiceEnqueue:
    """Test export job enqueueing."""
    
    @pytest.fixture
    def service(self, mock_session_repository, mock_ticket_repository,
                mock_jira_service_for_export, mock_arq_pool):
        return ExportService(
            session_repo=mock_session_repository,
            ticket_repo=mock_ticket_repository,
            jira_service=mock_jira_service_for_export,
            arq_pool=mock_arq_pool
        )
    
    async def test_export_session_validates_first(
        self, service, mock_session_repository
    ):
        """Should validate export readiness before enqueueing."""
        session_id = uuid4()
        mock_session_repository.is_export_ready.return_value = True
        
        await service.export_session(session_id)
        
        mock_session_repository.is_export_ready.assert_called_with(session_id)
    
    async def test_export_session_creates_task(
        self, service, mock_session_repository
    ):
        """Should create SessionTask for tracking."""
        session_id = uuid4()
        mock_session_repository.is_export_ready.return_value = True
        
        result = await service.export_session(session_id)
        
        mock_session_repository.start_task.assert_called()
        assert result.task_id is not None
    
    async def test_export_session_enqueues_job(
        self, service, mock_session_repository, mock_arq_pool
    ):
        """Should enqueue ARQ export job."""
        session_id = uuid4()
        mock_session_repository.is_export_ready.return_value = True
        
        result = await service.export_session(session_id)
        
        mock_arq_pool.enqueue_job.assert_called_with(
            'export_session_job',
            session_id=session_id,
            task_id=result.task_id
        )
    
    async def test_export_idempotent_if_running(
        self, service, mock_session_repository
    ):
        """Should return existing task if export already running."""
        session_id = uuid4()
        existing_task_id = uuid4()
        
        mock_session_repository.get_active_task.return_value = MagicMock(
            task_id=existing_task_id,
            task_type='export',
            status='running'
        )
        
        result = await service.export_session(session_id)
        
        assert result.task_id == existing_task_id


class TestExportServiceExecution:
    """Test export execution logic."""
    
    @pytest.fixture
    def service(self, mock_session_repository, mock_ticket_repository,
                mock_jira_service_for_export):
        return ExportService(
            session_repo=mock_session_repository,
            ticket_repo=mock_ticket_repository,
            jira_service=mock_jira_service_for_export
        )
    
    async def test_execute_creates_tickets_in_order(
        self, service, mock_ticket_repository, mock_jira_service_for_export,
        mock_progress_callback
    ):
        """Should create Jira tickets in dependency order."""
        session_id = uuid4()
        task_id = uuid4()
        
        tickets = [
            MagicMock(id=uuid4(), title='Ticket 1', dependencies=[], attachment=None),
            MagicMock(id=uuid4(), title='Ticket 2', dependencies=[], attachment=None)
        ]
        mock_ticket_repository.get_tickets_for_export.return_value = tickets
        
        await service.execute_session_export(session_id, task_id, mock_progress_callback)
        
        assert mock_jira_service_for_export.create_ticket.call_count == 2
    
    async def test_execute_stores_jira_keys(
        self, service, mock_ticket_repository, mock_jira_service_for_export,
        mock_progress_callback
    ):
        """Should store Jira key/URL on each ticket."""
        session_id = uuid4()
        task_id = uuid4()
        
        ticket = MagicMock(id=uuid4(), title='Test', dependencies=[], attachment=None)
        mock_ticket_repository.get_tickets_for_export.return_value = [ticket]
        
        mock_jira_service_for_export.create_ticket.return_value = {
            'key': 'TEST-456',
            'self': 'https://test.atlassian.net/browse/TEST-456'
        }
        
        await service.execute_session_export(session_id, task_id, mock_progress_callback)
        
        mock_ticket_repository.update_ticket.assert_called()
        update_call = mock_ticket_repository.update_ticket.call_args
        assert update_call[1]['jira_ticket_key'] == 'TEST-456'
    
    async def test_execute_uploads_attachments(
        self, service, mock_ticket_repository, mock_jira_service_for_export,
        mock_progress_callback
    ):
        """Should upload attachments for tickets that have them."""
        session_id = uuid4()
        task_id = uuid4()
        
        attachment = MagicMock(content='Long content...', filename='details.md')
        ticket = MagicMock(
            id=uuid4(),
            title='Test',
            dependencies=[],
            attachment=attachment
        )
        mock_ticket_repository.get_tickets_for_export.return_value = [ticket]
        
        await service.execute_session_export(session_id, task_id, mock_progress_callback)
        
        mock_jira_service_for_export.upload_attachment.assert_called()
    
    async def test_execute_creates_dependency_links(
        self, service, mock_ticket_repository, mock_jira_service_for_export,
        mock_progress_callback
    ):
        """Should create Jira links for dependencies."""
        session_id = uuid4()
        task_id = uuid4()
        
        ticket_a_id = uuid4()
        ticket_b_id = uuid4()
        
        ticket_a = MagicMock(
            id=ticket_a_id,
            title='A',
            dependencies=[MagicMock(depends_on_ticket_id=ticket_b_id)],
            attachment=None,
            jira_ticket_key=None
        )
        ticket_b = MagicMock(
            id=ticket_b_id,
            title='B',
            dependencies=[],
            attachment=None,
            jira_ticket_key=None
        )
        
        mock_ticket_repository.get_tickets_for_export.return_value = [ticket_b, ticket_a]
        
        # Track created keys
        created_keys = {}
        async def mock_create(title, description, **kwargs):
            key = f'TEST-{len(created_keys) + 1}'
            created_keys[title] = key
            return {'key': key, 'self': f'https://.../{key}'}
        
        mock_jira_service_for_export.create_ticket.side_effect = mock_create
        
        await service.execute_session_export(session_id, task_id, mock_progress_callback)
        
        mock_jira_service_for_export.create_issue_link.assert_called()
    
    async def test_execute_publishes_progress(
        self, service, mock_ticket_repository, mock_progress_callback
    ):
        """Should publish progress for each ticket."""
        session_id = uuid4()
        task_id = uuid4()
        
        tickets = [
            MagicMock(id=uuid4(), title=f'Ticket {i}', dependencies=[], attachment=None)
            for i in range(5)
        ]
        mock_ticket_repository.get_tickets_for_export.return_value = tickets
        
        await service.execute_session_export(session_id, task_id, mock_progress_callback)
        
        # Should have progress updates for each ticket plus start/end
        assert len(mock_progress_callback.calls) >= 5
```

---

## Part 5: Manual Fix Tracking Tests

```python
# tests/phase_6_export/test_manual_fix_tracking.py
import pytest
from uuid import uuid4
from unittest.mock import MagicMock

from app.services.export_service import ExportService
from app.schemas.export import ManualFixType


class TestManualFixTracking:
    """Test tracking of manual fixes required."""
    
    @pytest.fixture
    def service(self, mock_session_repository, mock_ticket_repository,
                mock_jira_service_for_export, mock_export_repository):
        return ExportService(
            session_repo=mock_session_repository,
            ticket_repo=mock_ticket_repository,
            jira_service=mock_jira_service_for_export,
            export_repo=mock_export_repository
        )
    
    async def test_records_failed_attachment_upload(
        self, service, mock_ticket_repository, mock_jira_service_for_export,
        mock_export_repository, mock_progress_callback
    ):
        """Should record when attachment upload fails."""
        session_id = uuid4()
        task_id = uuid4()
        
        ticket = MagicMock(
            id=uuid4(),
            title='Test',
            dependencies=[],
            attachment=MagicMock(content='content', filename='file.md')
        )
        mock_ticket_repository.get_tickets_for_export.return_value = [ticket]
        
        # Ticket creates OK, but attachment fails
        mock_jira_service_for_export.create_ticket.return_value = {'key': 'TEST-1'}
        mock_jira_service_for_export.upload_attachment.side_effect = Exception("Upload failed")
        
        await service.execute_session_export(session_id, task_id, mock_progress_callback)
        
        mock_export_repository.record_manual_fix.assert_called()
        call_args = mock_export_repository.record_manual_fix.call_args
        assert call_args[1]['fix_type'] == ManualFixType.ATTACHMENT_UPLOAD
    
    async def test_records_failed_dependency_link(
        self, service, mock_ticket_repository, mock_jira_service_for_export,
        mock_export_repository, mock_progress_callback
    ):
        """Should record when dependency link fails."""
        session_id = uuid4()
        task_id = uuid4()
        
        ticket_a_id = uuid4()
        ticket_b_id = uuid4()
        
        ticket_a = MagicMock(
            id=ticket_a_id,
            title='A',
            dependencies=[MagicMock(depends_on_ticket_id=ticket_b_id)],
            attachment=None
        )
        ticket_b = MagicMock(
            id=ticket_b_id,
            title='B',
            dependencies=[],
            attachment=None
        )
        mock_ticket_repository.get_tickets_for_export.return_value = [ticket_b, ticket_a]
        
        # Tickets create OK, but link fails
        mock_jira_service_for_export.create_ticket.return_value = {'key': 'TEST-1'}
        mock_jira_service_for_export.create_issue_link.side_effect = Exception("Link failed")
        
        await service.execute_session_export(session_id, task_id, mock_progress_callback)
        
        mock_export_repository.record_manual_fix.assert_called()
        call_args = mock_export_repository.record_manual_fix.call_args
        assert call_args[1]['fix_type'] == ManualFixType.DEPENDENCY_LINK
    
    async def test_get_manual_fixes_returns_list(
        self, service, mock_export_repository
    ):
        """Should return list of required manual fixes."""
        session_id = uuid4()
        
        mock_export_repository.get_manual_fixes.return_value = [
            MagicMock(
                fix_type=ManualFixType.ATTACHMENT_UPLOAD,
                ticket_id=uuid4(),
                jira_key='TEST-123',
                description='Upload file.md to TEST-123'
            )
        ]
        
        fixes = await service.get_manual_fixes(session_id)
        
        assert len(fixes) == 1
        assert fixes[0].fix_type == ManualFixType.ATTACHMENT_UPLOAD
```

---

## Part 6: Export Resume Tests

```python
# tests/phase_6_export/test_export_resume.py
import pytest
from uuid import uuid4
from unittest.mock import MagicMock

from app.services.export_service import ExportService


class TestExportResume:
    """Test resuming export from failure point."""
    
    @pytest.fixture
    def service(self, mock_session_repository, mock_ticket_repository,
                mock_jira_service_for_export, mock_export_repository, mock_arq_pool):
        return ExportService(
            session_repo=mock_session_repository,
            ticket_repo=mock_ticket_repository,
            jira_service=mock_jira_service_for_export,
            export_repo=mock_export_repository,
            arq_pool=mock_arq_pool
        )
    
    async def test_resume_skips_completed_tickets(
        self, service, mock_ticket_repository, mock_jira_service_for_export,
        mock_progress_callback
    ):
        """Should skip tickets that already have Jira keys."""
        session_id = uuid4()
        task_id = uuid4()
        
        tickets = [
            MagicMock(id=uuid4(), title='Done', jira_ticket_key='TEST-1', dependencies=[], attachment=None),
            MagicMock(id=uuid4(), title='Pending', jira_ticket_key=None, dependencies=[], attachment=None)
        ]
        mock_ticket_repository.get_tickets_for_export.return_value = tickets
        
        await service.execute_session_export(session_id, task_id, mock_progress_callback)
        
        # Should only create 1 ticket
        assert mock_jira_service_for_export.create_ticket.call_count == 1
    
    async def test_resume_recalculates_progress(
        self, service, mock_ticket_repository, mock_progress_callback
    ):
        """Should calculate progress based on remaining tickets."""
        session_id = uuid4()
        task_id = uuid4()
        
        # 3 of 5 already done
        tickets = [
            MagicMock(id=uuid4(), jira_ticket_key='TEST-1', dependencies=[], attachment=None),
            MagicMock(id=uuid4(), jira_ticket_key='TEST-2', dependencies=[], attachment=None),
            MagicMock(id=uuid4(), jira_ticket_key='TEST-3', dependencies=[], attachment=None),
            MagicMock(id=uuid4(), jira_ticket_key=None, dependencies=[], attachment=None),
            MagicMock(id=uuid4(), jira_ticket_key=None, dependencies=[], attachment=None)
        ]
        mock_ticket_repository.get_tickets_for_export.return_value = tickets
        
        await service.execute_session_export(session_id, task_id, mock_progress_callback)
        
        # First progress should reflect 3/5 complete
        first_call = mock_progress_callback.calls[0]
        assert first_call['percentage'] >= 60.0  # At least 60% (3/5)
```

---

## Part 7: API Endpoint Tests

```python
# tests/phase_6_export/test_api/test_export_endpoints.py
import pytest
from httpx import AsyncClient
from uuid import uuid4
from unittest.mock import MagicMock

from app.main import app
from app.api.dependencies.auth import get_current_user
from app.api.dependencies.services import get_export_service
from app.services.exceptions import ExportError


class TestStartExportEndpoint:
    """Test POST /api/sessions/{session_id}/export."""
    
    async def test_start_export_requires_auth(self):
        """Should require authentication."""
        session_id = uuid4()
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(f"/api/sessions/{session_id}/export")
        
        assert response.status_code == 401
    
    async def test_start_export_success(self, mock_user, mock_export_service):
        """Should start export and return task ID."""
        session_id = uuid4()
        task_id = uuid4()
        
        mock_export_service.export_session.return_value = MagicMock(
            task_id=task_id,
            session_id=session_id,
            status='exporting',
            total_tickets=10
        )
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_export_service] = lambda: mock_export_service
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                f"/api/sessions/{session_id}/export",
                headers={'Authorization': 'Bearer valid-token'}
            )
        
        assert response.status_code == 202
        data = response.json()
        assert data['task_id'] == str(task_id)
        
        app.dependency_overrides.clear()
    
    async def test_start_export_validation_stale(self, mock_user, mock_export_service):
        """Should return 409 when validation is stale."""
        session_id = uuid4()
        
        mock_export_service.export_session.side_effect = ExportError(
            message='Re-validation required',
            category='user_fixable'
        )
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_export_service] = lambda: mock_export_service
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                f"/api/sessions/{session_id}/export",
                headers={'Authorization': 'Bearer valid-token'}
            )
        
        assert response.status_code == 409
        data = response.json()
        assert 'validation' in data['detail'].lower()
        
        app.dependency_overrides.clear()


class TestExportStatusEndpoint:
    """Test GET /api/sessions/{session_id}/export/status."""
    
    async def test_get_export_status(self, mock_user, mock_export_service):
        """Should return export progress."""
        session_id = uuid4()
        
        mock_export_service.get_export_status.return_value = MagicMock(
            status='exporting',
            progress_percentage=50.0,
            tickets_exported=5,
            total_tickets=10,
            current_ticket='Configure Article'
        )
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_export_service] = lambda: mock_export_service
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                f"/api/sessions/{session_id}/export/status",
                headers={'Authorization': 'Bearer valid-token'}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data['progress_percentage'] == 50.0
        
        app.dependency_overrides.clear()


class TestManualFixesEndpoint:
    """Test GET /api/sessions/{session_id}/export/manual-fixes."""
    
    async def test_get_manual_fixes(self, mock_user, mock_export_service):
        """Should return list of manual fixes needed."""
        session_id = uuid4()
        
        mock_export_service.get_manual_fixes.return_value = [
            MagicMock(
                fix_type='attachment_upload',
                jira_key='TEST-123',
                description='Upload file.md to TEST-123'
            )
        ]
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_export_service] = lambda: mock_export_service
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                f"/api/sessions/{session_id}/export/manual-fixes",
                headers={'Authorization': 'Bearer valid-token'}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data['fixes']) == 1
        
        app.dependency_overrides.clear()


class TestExportSummaryEndpoint:
    """Test GET /api/sessions/{session_id}/export/summary."""
    
    async def test_get_export_summary(self, mock_user, mock_export_service):
        """Should return export summary with all Jira links."""
        session_id = uuid4()
        
        mock_export_service.get_export_summary.return_value = MagicMock(
            session_id=session_id,
            status='completed',
            tickets_exported=10,
            tickets_with_errors=0,
            manual_fixes_needed=1,
            jira_tickets=[
                {'key': 'TEST-1', 'title': 'Ticket 1', 'url': 'https://...'},
                {'key': 'TEST-2', 'title': 'Ticket 2', 'url': 'https://...'}
            ]
        )
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_export_service] = lambda: mock_export_service
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                f"/api/sessions/{session_id}/export/summary",
                headers={'Authorization': 'Bearer valid-token'}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data['tickets_exported'] == 10
        assert len(data['jira_tickets']) == 2
        
        app.dependency_overrides.clear()
```

---

## Part 8: Implementation Specifications

### 8.1 ExportService

**File**: `/backend/app/services/export_service.py`
- `export_session()` - Public method: validate and enqueue job
- `execute_session_export()` - Internal: actual export execution
- `get_export_status()` - Get current progress
- `get_manual_fixes()` - List required manual fixes
- `get_export_summary()` - Final summary with all Jira links
- `_order_tickets_for_export()` - Topological sort helper
- `_is_validation_stale()` - Staleness check helper

### 8.2 JiraService Export Methods

**File**: `/backend/app/integrations/jira/client.py` (additions)
- `create_ticket()` - Create Jira issue
- `upload_attachment()` - Upload file attachment
- `create_issue_link()` - Create dependency link

### 8.3 ARQ Worker

**File**: `/backend/app/workers/export_worker.py`
- `export_session_job()` - ARQ job function

### 8.4 API Endpoints

**File**: `/backend/app/api/routes/export.py`
- `POST /api/sessions/{id}/export` - Start export
- `GET /api/sessions/{id}/export/status` - Get progress
- `GET /api/sessions/{id}/export/manual-fixes` - Get fixes needed
- `GET /api/sessions/{id}/export/summary` - Get final summary

---

## Document References

### Primary References (in project knowledge)
- `export_service_architecture_updated.md` - Service design with ARQ
- `background_task_infrastructure.md` - Worker patterns
- `Missing_Response_Models_-_Complete_Specifications.md` - Response models
- `fastapi_jira_integration_endpoints.md` - Jira API patterns

---

## Success Criteria

### All Tests Pass
```bash
pytest tests/phase_6_export/ -v --cov=app/services/export_service --cov=app/integrations/jira --cov-report=term-missing
```

### Coverage Requirements
- ExportService: >85% coverage
- Jira integration: >80% coverage
- API endpoints: >80% coverage

### Verification Checklist
- [ ] Validation staleness check blocks stale exports
- [ ] Dependency ordering creates tickets in correct sequence
- [ ] Jira tickets are created with correct fields
- [ ] Attachments upload to Jira successfully
- [ ] Dependency links are created in Jira
- [ ] Manual fixes are tracked for failures
- [ ] Export can resume from failure point
- [ ] Export summary shows all created tickets
- [ ] All Phase 6 tests pass

### Integration Testing
After unit tests pass:
1. Set up Jira sandbox/test project
2. Create session with validated tickets
3. Run export â†’ Verify tickets appear in Jira
4. Verify dependency links work
5. Test attachment upload
6. Simulate failures â†’ Verify manual fix tracking

---

## Commands to Run

```bash
# Run Phase 6 tests only
pytest tests/phase_6_export/ -v

# Run with coverage
pytest tests/phase_6_export/ -v --cov=app --cov-report=html

# Integration test with real Jira (requires credentials)
pytest tests/phase_6_export/ -v -m integration --jira-project=TEST
```
