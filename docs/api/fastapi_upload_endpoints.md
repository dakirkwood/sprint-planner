# FastAPI Upload Endpoints - Implementation Specification

## Overview

The Upload stage handles CSV file ingestion, classification, validation, and preparation for ticket generation. This stage follows an all-or-nothing validation approach with comprehensive error feedback, maintaining consistency with the overall application architecture.

## Architectural Decisions

### Core Principles
- **All-or-nothing validation**: Complete success or clean failure with detailed error guidance
- **Registry pattern for CSV types**: Simple, maintainable classification system without plugin complexity
- **Cross-file relationship validation**: Mapping table approach for maintainability
- **Explicit user progression**: Users must confirm readiness before expensive LLM processing

### File Handling Strategy
- **Multi-file upload**: Single endpoint accepting up to 25 files
- **File size limits**: 2MB per file, 50MB total (2MB handles hundreds of thousands of CSV rows)
- **File name normalization**: Strip prefixes, normalize special characters (`UWEC_Bundles.csv` → `bundles.csv`)

## Endpoint Specifications

### 1. Multi-File Upload with Validation
```python
POST /api/upload/files/{session_id}
Content-Type: multipart/form-data
```

**Request:**
- `files[]`: Array of UploadFile objects (max 25 files, 2MB each)

**Response:**
```python
class FileUploadResponse(BaseModel):
    success: bool
    files_processed: List[UploadedFileInfo]
    available_classifications: List[CsvTypeOption]  # From registry
    errors: List[FileValidationError]  # Empty if success=True

class UploadedFileInfo(BaseModel):
    file_id: UUID
    original_filename: str
    normalized_filename: str
    file_size_bytes: int
    row_count: int
    detected_csv_type: Optional[str]  # Auto-detected classification

class CsvTypeOption(BaseModel):
    value: str      # "bundles"
    label: str      # "Content Types (Bundles)"

class FileValidationError(BaseModel):
    filename: str
    error_category: str  # "user_fixable", "admin_required", "temporary"
    row_errors: List[RowValidationError]
    file_level_errors: List[str]  # Missing columns, malformed CSV

class RowValidationError(BaseModel):
    row_number: int
    field_name: Optional[str]
    error_message: str
    current_value: Optional[str]
```

**Validation Process:**
1. **Immediate validation**: File format, size limits, basic CSV structure
2. **Auto-classification**: Detect CSV type based on filename/content patterns
3. **Comprehensive validation**: Schema validation, data types, required columns
4. **Row-level error collection**: Report all validation issues across all files

### 2. Classification Review and Override
```python
PUT /api/upload/classifications/{session_id}
```

**Request:**
```python
class ClassificationUpdateRequest(BaseModel):
    file_classifications: List[FileClassification]

class FileClassification(BaseModel):
    file_id: UUID
    csv_type: str  # Must be valid key from CSV_TYPE_REGISTRY
```

**Response:**
```python
class ClassificationUpdateResponse(BaseModel):
    success: bool
    files_updated: List[UploadedFileInfo]  # Re-validated files
    errors: List[FileValidationError]  # Any new validation failures
```

**Behavior:**
- Complete replacement of all classifications (not incremental)
- Re-validation for files with changed classifications
- Same validation depth as initial upload

### 3. Custom Entity Dependencies (Conditional)
```python
PUT /api/upload/custom-dependencies/{session_id}
```

**Request:**
```python
class CustomDependencyRequest(BaseModel):
    custom_relationships: List[CustomRelationship]

class CustomRelationship(BaseModel):
    dependent_file_id: UUID      # File that depends on another
    dependency_file_id: UUID     # File it depends on
    relationship_column: str     # Column name containing the reference
```

**Response:**
```python
class CustomDependencyResponse(BaseModel):
    success: bool
    relationships_configured: int
    ready_for_validation: bool
```

**UI Pattern:** Dropdown selection
```
FGTypeFields depends on: [FundingGoalTypes ▼]
OrderItemFields depends on: [OrderItemTypes ▼]
```

### 4. Final Cross-File Validation
```python
POST /api/upload/validate/{session_id}
```

**Request:** Empty body `{}`

**Response:**
```python
class ValidationResponse(BaseModel):
    success: bool
    ready_for_processing: bool
    summary: ValidationSummary
    errors: List[RelationshipError]  # Empty if success=True

class ValidationSummary(BaseModel):
    total_files: int
    total_entities: int
    relationship_checks_passed: int
    ready_message: str  # "Ready to generate 23 tickets from 5 CSV files"

class RelationshipError(BaseModel):
    relationship_type: str  # "bundle_references", "view_references"
    description: str        # "Fields referencing non-existent bundles"
    affected_files: List[str]
    specific_errors: List[RelationshipErrorDetail]

class RelationshipErrorDetail(BaseModel):
    source_file: str
    row_number: int
    column_name: str
    invalid_reference: str
    available_options: List[str]  # Valid reference options
```

## CSV Type Registry

**Registry Implementation:**
```python
CSV_TYPE_REGISTRY = {
    "bundles": {"label": "Content Types (Bundles)", "processor": BundleProcessor},
    "fields": {"label": "Fields", "processor": FieldProcessor},
    "views": {"label": "Views", "processor": ViewProcessor},
    "view_displays": {"label": "View Displays", "processor": ViewDisplayProcessor},
    "view_modes": {"label": "View Modes", "processor": ViewModeProcessor},
    "image_styles": {"label": "Image Styles", "processor": ImageStyleProcessor},
    "responsive_image_styles": {"label": "Responsive Image Styles", "processor": ResponsiveImageStyleProcessor},
    "workflows": {"label": "Workflows", "processor": WorkflowProcessor},
    "workflow_states": {"label": "Workflow States", "processor": WorkflowStateProcessor},
    "workflow_transitions": {"label": "Workflow Transitions", "processor": WorkflowTransitionProcessor},
    "migrations": {"label": "Migrations", "processor": MigrationProcessor},
    "migration_mappings": {"label": "Migration Mappings", "processor": MigrationMappingProcessor},
    "user_roles": {"label": "User Roles", "processor": UserRoleProcessor},
    "custom": {"label": "Custom Entity", "processor": CustomEntityProcessor}
}
```

## Cross-File Relationship Validation

**Standard Relationship Mapping:**
```python
CROSS_FILE_RELATIONSHIPS = {
    "fields": [
        {"column": "bundle", "references_csv_type": "bundles", "references_column": "machine_name"},
        {"column": "ref_bundle", "references_csv_type": "bundles", "references_column": "machine_name"}
    ],
    "view_displays": [
        {"column": "view", "references_csv_type": "views", "references_column": "machine_name"}
    ],
    "workflow_states": [
        {"column": "workflow", "references_csv_type": "workflows", "references_column": "machine_name"}
    ],
    "workflow_transitions": [
        {"column": "workflow", "references_csv_type": "workflows", "references_column": "machine_name"},
        {"column": "from_state", "references_csv_type": "workflow_states", "references_column": "machine_name"},
        {"column": "to_state", "references_csv_type": "workflow_states", "references_column": "machine_name"}
    ]
}
```

**Validation Process:**
1. **Individual file validation first** (structure, data types, required columns)
2. **Relationship validation second** (cross-file reference checking)
3. **Standard entities**: Use mapping table automatically
4. **Custom entities**: Use user-specified relationships

**Reference Resolution Strategy:**
- Check only within uploaded files (build specs contain everything needed)
- All required entities will be present in the uploaded CSV set
- No external system lookups needed

## Error Handling Strategy

### Validation Error Categories
- **user_fixable**: CSV format issues, missing required data, invalid references
- **admin_required**: System configuration issues, file processing failures
- **temporary**: Network issues, service unavailable

### Error Reporting Principles
- **Row-level granularity**: Report every validation issue with specific location
- **Grouped by relationship type**: Bundle references, view references, etc.
- **Actionable guidance**: Show available options for invalid references
- **Complete error collection**: All-or-nothing approach with comprehensive feedback

### Example Error Display
```
❌ Bundle Reference Errors (3 issues found)
Fields referencing bundles that don't exist:

• fields.csv row 5: "missing_bundle" not found in bundles.csv
• fields.csv row 12: "old_bundle" not found in bundles.csv
Available bundles: product_bundle, event_bundle, page_bundle

❌ Workflow State References (1 issue found)
• workflow_transitions.csv row 8: "invalid_state" not found in workflow_states.csv
Available states: draft, review, published
```

## Workflow Progression

### Stage Transitions
1. **Entry**: `sessions.current_stage = 'upload'`
2. **During upload/validation**: Stage remains 'upload'
3. **Exit**: User confirmation transitions to processing domain
4. **Database state**: All uploaded files, classifications, and validation results stored

### Transition to Processing
- **No pre-flight re-validation**: Trust completed upload validation
- **Simple trigger**: `POST /api/processing/generate-tickets/{session_id}`
- **Session context**: All processing context (files, LLM provider choice) stored in database
- **Clean handoff**: Upload domain responsibilities end, processing domain begins

## Database Integration

### Tables Used
- **uploaded_files**: File metadata, parsed content, validation status
- **sessions**: Current stage tracking, validation gates
- **session_errors**: Detailed error storage with file/row context

### Validation Gates
- **ADF validation gate**: Not in upload stage (handled in review stage)
- **Processing gate**: Successful cross-file validation required
- **Stage progression**: Explicit user confirmation required to advance

## Implementation Priority

### Core Upload Workflow
1. Multi-file upload with immediate validation and auto-classification
2. Classification review interface with registry-driven options
3. Cross-file validation with relationship mapping
4. Clean transition to processing domain

### Enhanced Features (Later)
1. Custom entity dependency configuration UI
2. Advanced error recovery workflows
3. Validation progress indicators for large file sets

## Success Criteria
- ✅ All-or-nothing validation provides comprehensive error feedback
- ✅ Registry pattern enables maintainable CSV type management
- ✅ Cross-file validation catches relationship issues early
- ✅ Custom entity handling accommodates non-standard CSV types
- ✅ Clean separation between upload and processing domains
- ✅ Row-level error reporting enables precise issue resolution
- ✅ Explicit user progression prevents accidental expensive operations