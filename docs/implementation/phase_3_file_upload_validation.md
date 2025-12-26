# Phase 3: File Upload & Validation

## Overview
Implement CSV file upload, parsing, automatic type classification, and two-phase validation. This phase handles all file-related operations before ticket generation.

**Estimated Effort**: 2-3 days  
**Prerequisites**: Phases 1-2 complete (models, repositories, auth, sessions)  
**Deliverables**: File upload endpoints, CSV type registry, UploadService, validation logic

---

## Test-Driven Development Approach

### TDD Workflow for This Phase
1. Write unit tests for CSV parsing utilities
2. Write unit tests for CSV type detection/registry
3. Write unit tests for validation rules
4. Write integration tests for file upload flow
5. Write API endpoint tests
6. Implement code to make tests pass
7. Test with real UWEC CSV files

---

## Part 1: Test Structure

### 1.1 Phase 3 Test Directory

```
tests/
â”œâ”€â”€ conftest.py                    # Add upload-specific fixtures
â”œâ”€â”€ sample_data/                   # Copy of /docs/sample_data for tests
â”‚   â”œâ”€â”€ uwec_complete/
â”‚   â”‚   â”œâ”€â”€ UWEC_Bundles.csv
â”‚   â”‚   â”œâ”€â”€ UWEC_Fields.csv
â”‚   â”‚   â””â”€â”€ ...
â”‚   â””â”€â”€ test_cases/
â”‚       â””â”€â”€ UWEC_Fields_BROKEN.csv
â”œâ”€â”€ phase_3_upload/
â”‚   â”œâ”€â”€ __init__.py
â”‚   â”œâ”€â”€ test_csv_parsing.py
â”‚   â”œâ”€â”€ test_csv_type_registry.py
â”‚   â”œâ”€â”€ test_csv_validation.py
â”‚   â”œâ”€â”€ test_upload_service.py
â”‚   â”œâ”€â”€ test_upload_repository.py
â”‚   â””â”€â”€ test_api/
â”‚       â”œâ”€â”€ __init__.py
â”‚       â””â”€â”€ test_upload_endpoints.py
```

### 1.2 Additional Fixtures (add to conftest.py)

```python
# tests/conftest.py - additions for Phase 3
import pytest
from pathlib import Path
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock

from app.schemas.base import FileValidationStatus


@pytest.fixture
def sample_data_path():
    """Path to sample CSV files."""
    return Path(__file__).parent / 'sample_data' / 'uwec_complete'


@pytest.fixture
def broken_csv_path():
    """Path to broken CSV for error testing."""
    return Path(__file__).parent / 'sample_data' / 'test_cases' / 'UWEC_Fields_BROKEN.csv'


@pytest.fixture
def valid_bundles_csv(sample_data_path):
    """Load valid bundles CSV content."""
    return (sample_data_path / 'UWEC_Bundles.csv').read_text()


@pytest.fixture
def valid_fields_csv(sample_data_path):
    """Load valid fields CSV content."""
    return (sample_data_path / 'UWEC_Fields.csv').read_text()


@pytest.fixture
def mock_upload_repository():
    """Mock UploadRepository for unit tests."""
    repo = AsyncMock()
    repo.create_file.return_value = MagicMock(
        id=uuid4(),
        filename='test.csv',
        csv_type=None,
        validation_status=FileValidationStatus.PENDING
    )
    repo.get_files_by_session.return_value = []
    repo.commit.return_value = None
    return repo


@pytest.fixture
def mock_llm_service():
    """Mock LLMService for classification (fallback)."""
    service = AsyncMock()
    service.classify_csv_type.return_value = 'custom'
    return service


@pytest.fixture
def csv_upload_file(valid_bundles_csv):
    """Create uploadable file object."""
    return {
        'file': BytesIO(valid_bundles_csv.encode()),
        'filename': 'UWEC_Bundles.csv',
        'content_type': 'text/csv'
    }


@pytest.fixture
def multiple_csv_files(sample_data_path):
    """Multiple CSV files for batch upload testing."""
    files = []
    for csv_file in sample_data_path.glob('*.csv'):
        content = csv_file.read_bytes()
        files.append({
            'file': BytesIO(content),
            'filename': csv_file.name,
            'content_type': 'text/csv'
        })
    return files
```

---

## Part 2: CSV Parsing Tests

### 2.1 CSV Parsing Utility Tests

```python
# tests/phase_3_upload/test_csv_parsing.py
import pytest
from io import StringIO

from app.services.csv.parser import (
    parse_csv_content,
    extract_headers,
    validate_csv_structure,
    CsvParseError
)


class TestCsvParsing:
    """Test CSV parsing utilities."""
    
    def test_parse_csv_returns_headers_and_rows(self):
        """Should return dict with headers and rows."""
        content = "name,type,required\nfield1,string,true\nfield2,integer,false"
        
        result = parse_csv_content(content)
        
        assert 'headers' in result
        assert 'rows' in result
        assert result['headers'] == ['name', 'type', 'required']
        assert len(result['rows']) == 2
    
    def test_parse_csv_handles_quoted_fields(self):
        """Should handle CSV with quoted fields containing commas."""
        content = 'name,description\nfield1,"Description, with comma"'
        
        result = parse_csv_content(content)
        
        assert result['rows'][0]['description'] == 'Description, with comma'
    
    def test_parse_csv_trims_whitespace(self):
        """Should trim whitespace from headers and values."""
        content = "  name  ,  type  \n  field1  ,  string  "
        
        result = parse_csv_content(content)
        
        assert result['headers'] == ['name', 'type']
        assert result['rows'][0]['name'] == 'field1'
    
    def test_parse_csv_empty_file_raises_error(self):
        """Should raise error for empty file."""
        with pytest.raises(CsvParseError) as exc_info:
            parse_csv_content("")
        
        assert 'empty' in str(exc_info.value).lower()
    
    def test_parse_csv_headers_only_raises_error(self):
        """Should raise error for file with only headers."""
        with pytest.raises(CsvParseError) as exc_info:
            parse_csv_content("name,type,required")
        
        assert 'no data rows' in str(exc_info.value).lower()
    
    def test_parse_csv_inconsistent_columns_raises_error(self):
        """Should raise error when rows have different column counts."""
        content = "name,type\nfield1,string,extra_value"
        
        with pytest.raises(CsvParseError) as exc_info:
            parse_csv_content(content)
        
        assert 'column' in str(exc_info.value).lower()
    
    def test_extract_headers_normalizes_names(self):
        """Should normalize header names (lowercase, underscores)."""
        content = "Field Name,Field Type,Is Required"
        
        headers = extract_headers(content)
        
        assert headers == ['field_name', 'field_type', 'is_required']


class TestCsvStructureValidation:
    """Test CSV structure validation."""
    
    def test_validate_structure_valid_csv(self, valid_bundles_csv):
        """Should pass for valid CSV structure."""
        errors = validate_csv_structure(valid_bundles_csv)
        
        assert len(errors) == 0
    
    def test_validate_structure_detects_encoding_issues(self):
        """Should detect non-UTF8 encoding issues."""
        # Create content with invalid UTF-8 byte
        content = b"name,type\nfield1,\x80invalid"
        
        errors = validate_csv_structure(content.decode('latin-1'))
        
        assert any('encoding' in e.lower() for e in errors)
    
    def test_validate_structure_max_file_size(self):
        """Should reject files over 2MB."""
        large_content = "a" * (2 * 1024 * 1024 + 1)  # Just over 2MB
        
        errors = validate_csv_structure(large_content)
        
        assert any('size' in e.lower() for e in errors)
```

---

## Part 3: CSV Type Registry Tests

### 3.1 Type Registry Tests

```python
# tests/phase_3_upload/test_csv_type_registry.py
import pytest

from app.services.csv.type_registry import (
    CsvTypeRegistry,
    detect_csv_type,
    get_required_columns,
    get_type_metadata,
    SUPPORTED_CSV_TYPES
)


class TestCsvTypeRegistry:
    """Test CSV type registry configuration."""
    
    def test_registry_has_all_expected_types(self):
        """Registry should include all standard Drupal export types."""
        expected_types = {
            'bundles', 'fields', 'views', 'view_displays',
            'image_styles', 'user_roles', 'workflows',
            'workflow_states', 'migrations'
        }
        
        assert expected_types.issubset(set(SUPPORTED_CSV_TYPES))
    
    def test_each_type_has_required_columns(self):
        """Each type should define required columns."""
        for csv_type in SUPPORTED_CSV_TYPES:
            columns = get_required_columns(csv_type)
            
            assert isinstance(columns, list)
            assert len(columns) > 0, f"{csv_type} has no required columns"
    
    def test_each_type_has_entity_group_mapping(self):
        """Each type should map to an entity group."""
        for csv_type in SUPPORTED_CSV_TYPES:
            metadata = get_type_metadata(csv_type)
            
            assert 'entity_group' in metadata
            assert metadata['entity_group'] in [
                'Content', 'Media', 'Views', 'Migration',
                'Workflow', 'User Roles', 'Custom'
            ]


class TestCsvTypeDetection:
    """Test automatic CSV type detection."""
    
    def test_detect_bundles_by_filename(self):
        """Should detect bundles from filename pattern."""
        detected = detect_csv_type(
            filename='UWEC_Bundles.csv',
            headers=['machine_name', 'label', 'description']
        )
        
        assert detected == 'bundles'
    
    def test_detect_fields_by_filename(self):
        """Should detect fields from filename pattern."""
        detected = detect_csv_type(
            filename='UWEC_Fields.csv',
            headers=['field_name', 'field_type', 'bundle']
        )
        
        assert detected == 'fields'
    
    def test_detect_views_by_filename(self):
        """Should detect views from filename pattern."""
        detected = detect_csv_type(
            filename='CustomViews.csv',
            headers=['view_id', 'label', 'base_table']
        )
        
        assert detected == 'views'
    
    def test_detect_type_by_headers_when_filename_ambiguous(self):
        """Should fall back to header analysis for generic filenames."""
        # Generic filename, but has bundle-specific columns
        detected = detect_csv_type(
            filename='export_data.csv',
            headers=['machine_name', 'label', 'description', 'entity_type']
        )
        
        assert detected == 'bundles'
    
    def test_detect_custom_when_unrecognized(self):
        """Should return 'custom' for unrecognized CSV types."""
        detected = detect_csv_type(
            filename='random_data.csv',
            headers=['foo', 'bar', 'baz']
        )
        
        assert detected == 'custom'
    
    @pytest.mark.parametrize("filename,expected_type", [
        ("UWEC_Bundles.csv", "bundles"),
        ("uwec_bundles.csv", "bundles"),  # Case insensitive
        ("Site_Fields.csv", "fields"),
        ("CustomViews.csv", "views"),
        ("ViewDisplays.csv", "view_displays"),
        ("ImageStyles.csv", "image_styles"),
        ("UserRoles.csv", "user_roles"),
        ("Workflows.csv", "workflows"),
        ("WorkflowStates.csv", "workflow_states"),
    ])
    def test_detect_type_from_real_filenames(self, filename, expected_type):
        """Should detect types from realistic filename patterns."""
        detected = detect_csv_type(filename=filename, headers=[])
        
        assert detected == expected_type


class TestRequiredColumns:
    """Test required column definitions."""
    
    def test_bundles_required_columns(self):
        """Bundles should require machine_name and label."""
        columns = get_required_columns('bundles')
        
        assert 'machine_name' in columns
        assert 'label' in columns
    
    def test_fields_required_columns(self):
        """Fields should require field_name, field_type, bundle."""
        columns = get_required_columns('fields')
        
        assert 'field_name' in columns
        assert 'field_type' in columns
        assert 'bundle' in columns
    
    def test_views_required_columns(self):
        """Views should require view_id and label."""
        columns = get_required_columns('views')
        
        assert 'view_id' in columns
        assert 'label' in columns
```

---

## Part 4: CSV Validation Tests

### 4.1 Validation Rule Tests

```python
# tests/phase_3_upload/test_csv_validation.py
import pytest

from app.services.csv.validation import (
    validate_csv_file,
    validate_required_columns,
    validate_cross_file_references,
    ValidationResult,
    ValidationError
)
from app.schemas.base import FileValidationStatus


class TestRequiredColumnValidation:
    """Test validation of required columns."""
    
    def test_valid_bundles_passes(self, valid_bundles_csv):
        """Valid bundles CSV should pass validation."""
        parsed = parse_csv_content(valid_bundles_csv)
        
        errors = validate_required_columns(parsed, csv_type='bundles')
        
        assert len(errors) == 0
    
    def test_missing_required_column_fails(self):
        """Should fail when required column is missing."""
        parsed = {
            'headers': ['machine_name'],  # Missing 'label'
            'rows': [{'machine_name': 'article'}]
        }
        
        errors = validate_required_columns(parsed, csv_type='bundles')
        
        assert len(errors) > 0
        assert any('label' in e.message.lower() for e in errors)
    
    def test_empty_required_value_fails(self):
        """Should fail when required column has empty value."""
        parsed = {
            'headers': ['machine_name', 'label'],
            'rows': [{'machine_name': 'article', 'label': ''}]  # Empty label
        }
        
        errors = validate_required_columns(parsed, csv_type='bundles')
        
        assert len(errors) > 0
        assert any('empty' in e.message.lower() for e in errors)


class TestCrossFileValidation:
    """Test validation of cross-file references."""
    
    def test_fields_reference_valid_bundles(self):
        """Fields referencing existing bundles should pass."""
        bundles_data = {
            'headers': ['machine_name', 'label'],
            'rows': [
                {'machine_name': 'article', 'label': 'Article'},
                {'machine_name': 'page', 'label': 'Page'}
            ]
        }
        fields_data = {
            'headers': ['field_name', 'bundle'],
            'rows': [
                {'field_name': 'body', 'bundle': 'article'},
                {'field_name': 'title', 'bundle': 'page'}
            ]
        }
        
        session_files = {
            'bundles': bundles_data,
            'fields': fields_data
        }
        
        errors = validate_cross_file_references(session_files)
        
        assert len(errors) == 0
    
    def test_fields_reference_missing_bundle_fails(self):
        """Fields referencing non-existent bundles should fail."""
        bundles_data = {
            'headers': ['machine_name', 'label'],
            'rows': [{'machine_name': 'article', 'label': 'Article'}]
        }
        fields_data = {
            'headers': ['field_name', 'bundle'],
            'rows': [
                {'field_name': 'body', 'bundle': 'nonexistent_bundle'}
            ]
        }
        
        session_files = {
            'bundles': bundles_data,
            'fields': fields_data
        }
        
        errors = validate_cross_file_references(session_files)
        
        assert len(errors) > 0
        assert any('nonexistent_bundle' in e.message for e in errors)
    
    def test_cross_validation_skipped_when_reference_file_missing(self):
        """Should skip cross-validation if referenced file not uploaded."""
        fields_data = {
            'headers': ['field_name', 'bundle'],
            'rows': [{'field_name': 'body', 'bundle': 'article'}]
        }
        
        # No bundles file uploaded
        session_files = {'fields': fields_data}
        
        errors = validate_cross_file_references(session_files)
        
        # Should be warning, not error
        assert all(e.severity == 'warning' for e in errors)


class TestFullFileValidation:
    """Test complete file validation flow."""
    
    def test_validate_valid_file(self, valid_bundles_csv):
        """Valid file should pass all validation."""
        result = validate_csv_file(
            content=valid_bundles_csv,
            filename='UWEC_Bundles.csv',
            csv_type='bundles'
        )
        
        assert result.status == FileValidationStatus.VALID
        assert len(result.errors) == 0
    
    def test_validate_broken_file(self, broken_csv_path):
        """Broken file should fail validation with errors."""
        content = broken_csv_path.read_text()
        
        result = validate_csv_file(
            content=content,
            filename='UWEC_Fields_BROKEN.csv',
            csv_type='fields'
        )
        
        assert result.status == FileValidationStatus.INVALID
        assert len(result.errors) > 0
    
    def test_validation_result_includes_row_count(self, valid_bundles_csv):
        """Result should include row count for valid files."""
        result = validate_csv_file(
            content=valid_bundles_csv,
            filename='UWEC_Bundles.csv',
            csv_type='bundles'
        )
        
        assert result.row_count > 0
```

---

## Part 5: Upload Service Tests

### 5.1 UploadService Tests

```python
# tests/phase_3_upload/test_upload_service.py
import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

from app.services.upload_service import UploadService
from app.services.exceptions import UploadError
from app.schemas.base import FileValidationStatus


class TestUploadServiceFileUpload:
    """Test file upload functionality."""
    
    @pytest.fixture
    def service(self, mock_upload_repository, mock_session_repository, mock_error_repository, mock_llm_service):
        return UploadService(
            upload_repo=mock_upload_repository,
            session_repo=mock_session_repository,
            error_repo=mock_error_repository,
            llm_service=mock_llm_service
        )
    
    async def test_upload_file_parses_and_stores(self, service, valid_bundles_csv, mock_upload_repository):
        """Should parse CSV and store in database."""
        session_id = uuid4()
        
        result = await service.upload_file(
            session_id=session_id,
            filename='UWEC_Bundles.csv',
            content=valid_bundles_csv.encode()
        )
        
        assert result.file_id is not None
        mock_upload_repository.create_file.assert_called_once()
        mock_upload_repository.commit.assert_called()
    
    async def test_upload_file_auto_detects_type(self, service, valid_bundles_csv):
        """Should automatically detect CSV type."""
        session_id = uuid4()
        
        result = await service.upload_file(
            session_id=session_id,
            filename='UWEC_Bundles.csv',
            content=valid_bundles_csv.encode()
        )
        
        assert result.detected_type == 'bundles'
    
    async def test_upload_file_rejects_non_csv(self, service):
        """Should reject non-CSV files."""
        session_id = uuid4()
        
        with pytest.raises(UploadError) as exc_info:
            await service.upload_file(
                session_id=session_id,
                filename='document.pdf',
                content=b'%PDF-1.4...'
            )
        
        assert exc_info.value.category == 'user_fixable'
        assert 'csv' in exc_info.value.message.lower()
    
    async def test_upload_file_rejects_oversized(self, service):
        """Should reject files over 2MB."""
        session_id = uuid4()
        large_content = b'x' * (2 * 1024 * 1024 + 1)
        
        with pytest.raises(UploadError) as exc_info:
            await service.upload_file(
                session_id=session_id,
                filename='large.csv',
                content=large_content
            )
        
        assert exc_info.value.category == 'user_fixable'
        assert 'size' in exc_info.value.message.lower()


class TestUploadServiceClassification:
    """Test CSV classification functionality."""
    
    @pytest.fixture
    def service(self, mock_upload_repository, mock_session_repository, mock_error_repository, mock_llm_service):
        return UploadService(
            upload_repo=mock_upload_repository,
            session_repo=mock_session_repository,
            error_repo=mock_error_repository,
            llm_service=mock_llm_service
        )
    
    async def test_classify_file_updates_type(self, service, mock_upload_repository):
        """Should update file with manual classification."""
        file_id = uuid4()
        mock_upload_repository.get_file_by_id.return_value = MagicMock(
            id=file_id,
            csv_type=None
        )
        
        result = await service.classify_file(
            file_id=file_id,
            csv_type='custom'
        )
        
        mock_upload_repository.update_file.assert_called()
    
    async def test_classify_file_rejects_invalid_type(self, service):
        """Should reject unknown CSV types."""
        file_id = uuid4()
        
        with pytest.raises(UploadError) as exc_info:
            await service.classify_file(
                file_id=file_id,
                csv_type='invalid_type_name'
            )
        
        assert exc_info.value.category == 'user_fixable'


class TestUploadServiceValidation:
    """Test validation functionality."""
    
    @pytest.fixture
    def service(self, mock_upload_repository, mock_session_repository, mock_error_repository, mock_llm_service):
        return UploadService(
            upload_repo=mock_upload_repository,
            session_repo=mock_session_repository,
            error_repo=mock_error_repository,
            llm_service=mock_llm_service
        )
    
    async def test_validate_session_files_all_valid(self, service, mock_upload_repository):
        """Should pass when all files are valid."""
        session_id = uuid4()
        mock_upload_repository.get_files_by_session.return_value = [
            MagicMock(
                id=uuid4(),
                filename='bundles.csv',
                csv_type='bundles',
                parsed_content={'headers': ['machine_name', 'label'], 'rows': [{}]}
            )
        ]
        
        result = await service.validate_session_files(session_id)
        
        assert result.all_valid is True
        assert result.can_proceed is True
    
    async def test_validate_session_files_with_errors(self, service, mock_upload_repository):
        """Should report errors when files are invalid."""
        session_id = uuid4()
        mock_upload_repository.get_files_by_session.return_value = [
            MagicMock(
                id=uuid4(),
                filename='fields.csv',
                csv_type='fields',
                parsed_content={'headers': ['field_name'], 'rows': [{}]}  # Missing required columns
            )
        ]
        
        result = await service.validate_session_files(session_id)
        
        assert result.all_valid is False
        assert len(result.file_errors) > 0
    
    async def test_validate_session_no_files(self, service, mock_upload_repository):
        """Should fail when no files uploaded."""
        session_id = uuid4()
        mock_upload_repository.get_files_by_session.return_value = []
        
        result = await service.validate_session_files(session_id)
        
        assert result.can_proceed is False
        assert 'no files' in result.message.lower()


class TestUploadServiceBatchOperations:
    """Test batch upload operations."""
    
    @pytest.fixture
    def service(self, mock_upload_repository, mock_session_repository, mock_error_repository, mock_llm_service):
        return UploadService(
            upload_repo=mock_upload_repository,
            session_repo=mock_session_repository,
            error_repo=mock_error_repository,
            llm_service=mock_llm_service
        )
    
    async def test_upload_multiple_files(self, service, multiple_csv_files):
        """Should handle batch upload of multiple files."""
        session_id = uuid4()
        
        results = await service.upload_files(
            session_id=session_id,
            files=multiple_csv_files
        )
        
        assert len(results.uploaded_files) == len(multiple_csv_files)
    
    async def test_delete_file(self, service, mock_upload_repository):
        """Should delete file from session."""
        file_id = uuid4()
        session_id = uuid4()
        mock_upload_repository.get_file_by_id.return_value = MagicMock(
            id=file_id,
            session_id=session_id
        )
        
        await service.delete_file(file_id, session_id)
        
        mock_upload_repository.delete_file.assert_called_with(file_id)
```

---

## Part 6: API Endpoint Tests

### 6.1 Upload Endpoint Tests

```python
# tests/phase_3_upload/test_api/test_upload_endpoints.py
import pytest
from httpx import AsyncClient
from uuid import uuid4
from io import BytesIO

from app.main import app
from app.api.dependencies.auth import get_current_user
from app.api.dependencies.services import get_upload_service


class TestUploadFileEndpoint:
    """Test POST /api/sessions/{session_id}/files."""
    
    async def test_upload_requires_auth(self):
        """Should require authentication."""
        session_id = uuid4()
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                f"/api/sessions/{session_id}/files",
                files={'file': ('test.csv', b'name,value\na,b', 'text/csv')}
            )
        
        assert response.status_code == 401
    
    async def test_upload_single_file(self, mock_user, mock_upload_service, valid_bundles_csv):
        """Should upload and process single file."""
        session_id = uuid4()
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_upload_service] = lambda: mock_upload_service
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                f"/api/sessions/{session_id}/files",
                files={'file': ('UWEC_Bundles.csv', valid_bundles_csv.encode(), 'text/csv')},
                headers={'Authorization': 'Bearer valid-token'}
            )
        
        assert response.status_code == 201
        data = response.json()
        assert 'file_id' in data
        assert data['detected_type'] == 'bundles'
        
        app.dependency_overrides.clear()
    
    async def test_upload_multiple_files(self, mock_user, mock_upload_service, multiple_csv_files):
        """Should handle batch upload."""
        session_id = uuid4()
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_upload_service] = lambda: mock_upload_service
        
        files = [
            ('files', (f['filename'], f['file'], 'text/csv'))
            for f in multiple_csv_files
        ]
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                f"/api/sessions/{session_id}/files/batch",
                files=files,
                headers={'Authorization': 'Bearer valid-token'}
            )
        
        assert response.status_code == 201
        data = response.json()
        assert len(data['uploaded_files']) == len(multiple_csv_files)
        
        app.dependency_overrides.clear()


class TestListFilesEndpoint:
    """Test GET /api/sessions/{session_id}/files."""
    
    async def test_list_session_files(self, mock_user, mock_upload_service):
        """Should list all files for session."""
        session_id = uuid4()
        mock_upload_service.get_session_files.return_value = [
            {'file_id': str(uuid4()), 'filename': 'bundles.csv', 'csv_type': 'bundles'},
            {'file_id': str(uuid4()), 'filename': 'fields.csv', 'csv_type': 'fields'}
        ]
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_upload_service] = lambda: mock_upload_service
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                f"/api/sessions/{session_id}/files",
                headers={'Authorization': 'Bearer valid-token'}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data['files']) == 2
        
        app.dependency_overrides.clear()


class TestClassifyFileEndpoint:
    """Test PUT /api/sessions/{session_id}/files/{file_id}/classify."""
    
    async def test_classify_file(self, mock_user, mock_upload_service):
        """Should update file classification."""
        session_id = uuid4()
        file_id = uuid4()
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_upload_service] = lambda: mock_upload_service
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.put(
                f"/api/sessions/{session_id}/files/{file_id}/classify",
                json={'csv_type': 'custom'},
                headers={'Authorization': 'Bearer valid-token'}
            )
        
        assert response.status_code == 200
        mock_upload_service.classify_file.assert_called_with(file_id, 'custom')
        
        app.dependency_overrides.clear()


class TestValidateFilesEndpoint:
    """Test POST /api/sessions/{session_id}/files/validate."""
    
    async def test_validate_session_files(self, mock_user, mock_upload_service):
        """Should validate all session files."""
        session_id = uuid4()
        mock_upload_service.validate_session_files.return_value = MagicMock(
            all_valid=True,
            can_proceed=True,
            file_results=[]
        )
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_upload_service] = lambda: mock_upload_service
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                f"/api/sessions/{session_id}/files/validate",
                headers={'Authorization': 'Bearer valid-token'}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data['can_proceed'] is True
        
        app.dependency_overrides.clear()


class TestDeleteFileEndpoint:
    """Test DELETE /api/sessions/{session_id}/files/{file_id}."""
    
    async def test_delete_file(self, mock_user, mock_upload_service):
        """Should delete file from session."""
        session_id = uuid4()
        file_id = uuid4()
        
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_upload_service] = lambda: mock_upload_service
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.delete(
                f"/api/sessions/{session_id}/files/{file_id}",
                headers={'Authorization': 'Bearer valid-token'}
            )
        
        assert response.status_code == 204
        mock_upload_service.delete_file.assert_called()
        
        app.dependency_overrides.clear()
```

---

## Part 7: Implementation Specifications

### 7.1 CSV Parsing Utilities

**File**: `/backend/app/services/csv/parser.py`
- `parse_csv_content()` - Parse CSV string to dict
- `extract_headers()` - Get and normalize headers
- `validate_csv_structure()` - Basic structure validation

### 7.2 CSV Type Registry

**File**: `/backend/app/services/csv/type_registry.py`
- `SUPPORTED_CSV_TYPES` - List of known types
- `detect_csv_type()` - Auto-detection logic
- `get_required_columns()` - Per-type requirements
- `get_type_metadata()` - Entity group mappings

### 7.3 CSV Validation

**File**: `/backend/app/services/csv/validation.py`
- `validate_csv_file()` - Full validation pipeline
- `validate_required_columns()` - Column presence/values
- `validate_cross_file_references()` - Cross-file integrity

### 7.4 UploadService

**File**: `/backend/app/services/upload_service.py`
- `upload_file()` - Single file upload
- `upload_files()` - Batch upload
- `classify_file()` - Manual classification
- `validate_session_files()` - Full session validation
- `get_session_files()` - List files
- `delete_file()` - Remove file

### 7.5 API Endpoints

**File**: `/backend/app/api/routes/upload.py`
- `POST /api/sessions/{id}/files` - Upload single file
- `POST /api/sessions/{id}/files/batch` - Batch upload
- `GET /api/sessions/{id}/files` - List files
- `PUT /api/sessions/{id}/files/{file_id}/classify` - Classify
- `POST /api/sessions/{id}/files/validate` - Validate all
- `DELETE /api/sessions/{id}/files/{file_id}` - Delete

---

## Document References

### Primary References (in project knowledge)
- `fastapi_upload_endpoints.md` - Upload API specifications
- `upload_schemas_models.py` - Pydantic models for upload
- `uploaded_file_model_spec_updated.md` - UploadedFile model
- `upload_service_architecture.md` - UploadService design
- `CSV_Type_Registry_Structure_Specification.md` - Type registry details

### Sample Data
- `/docs/sample_data/uwec_complete/` - Valid CSV examples
- `/docs/sample_data/test_cases/` - Broken CSV for testing

---

## Success Criteria

### All Tests Pass
```bash
pytest tests/phase_3_upload/ -v --cov=app/services/csv --cov=app/services/upload_service --cov-report=term-missing
```

### Coverage Requirements
- CSV parsing: >90% coverage
- Type registry: >85% coverage
- Validation: >85% coverage
- UploadService: >80% coverage
- API endpoints: >80% coverage

### Verification Checklist
- [ ] CSV parsing handles all edge cases
- [ ] Type detection works for all UWEC files
- [ ] Required column validation catches missing columns
- [ ] Cross-file validation detects invalid references
- [ ] Broken CSV file fails validation with clear errors
- [ ] File upload stores parsed content in database
- [ ] Batch upload handles multiple files
- [ ] All API endpoints return correct response schemas
- [ ] All Phase 3 tests pass

### Manual Verification
After tests pass:
1. Upload each UWEC CSV file individually
2. Verify type auto-detection is correct
3. Upload broken CSV â†’ Verify validation errors
4. Upload all files â†’ Run validation â†’ Proceed to processing

---

## Commands to Run

```bash
# Copy sample data to tests directory
cp -r docs/sample_data tests/

# Run Phase 3 tests only
pytest tests/phase_3_upload/ -v

# Run with coverage
pytest tests/phase_3_upload/ -v --cov=app --cov-report=html

# Test with real files
pytest tests/phase_3_upload/test_csv_type_registry.py -v -k "real_filenames"
```
