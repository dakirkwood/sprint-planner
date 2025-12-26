# UploadService Architecture Decisions

## Method Signatures

```python
class UploadService:
    def __init__(self, 
                 upload_repo: UploadRepositoryInterface,
                 session_repo: SessionRepositoryInterface, 
                 error_repo: ErrorRepositoryInterface,
                 csv_registry: CSVTypeRegistry,
                 llm_service: LLMService):

    # File Upload & Auto-Detection (handles CSV parsing internally)
    async def upload_files(self, session_id: UUID, files: List[UploadFile]) -> FileUploadResponse
    
    # Classification Management
    async def update_classifications(self, session_id: UUID, classifications: List[FileClassification]) -> ClassificationUpdateResponse
    
    # Two-Phase Validation (single public method, calls both phases internally)
    async def validate_files(self, session_id: UUID) -> ValidationResponse
    
    # Custom Entity Dependencies
    async def configure_custom_dependencies(self, session_id: UUID, relationships: List[CustomRelationship]) -> CustomDependencyResponse
    
    # Optional LLM Enhancement
    async def explain_error(self, error_id: UUID) -> ErrorExplanationResponse
```

## Key Decisions Made

### 1. CSV Parsing Handled Internally
- **Decision**: `upload_files` handles CSV parsing internally rather than delegating to separate component
- **Rationale**: Simple parsing (just reading content) doesn't warrant additional component complexity

### 2. Two-Phase Validation with Single Public Method
- **Decision**: Internal `validate_schema()` and `validate_content()` methods called by single public `validate_files()` method
- **Rationale**: Maintains clean API while enabling proper two-phase validation flow

### 3. CSV Type Registry via Dependency Injection
- **Decision**: Inject `CSVTypeRegistry` as simple dict/dataclass rather than direct import
- **Structure**: 
  ```python
  @dataclass
  class CSVTypeDefinition:
      label: str
      required_columns: List[str]
      optional_columns: List[str]
      detection_patterns: dict
  
  CSVTypeRegistry = Dict[str, CSVTypeDefinition]
  ```
- **Rationale**: Testable, configurable, follows DI patterns

### 4. Error Pattern Detection in Repository
- **Decision**: Error repository handles pattern detection with single method `store_errors_with_pattern_detection()`
- **Rationale**: Encapsulates pattern detection logic where it belongs, service gets back consolidated errors

### 5. Consistent Response Types
- **Decision**: Use `ValidationResponse` for all validation methods (internal and public)
- **Rationale**: Consistency in API contracts, easier testing and debugging

## Dependencies
- **UploadRepositoryInterface**: File metadata and content storage
- **SessionRepositoryInterface**: Session stage transitions
- **ErrorRepositoryInterface**: Error storage with pattern detection
- **CSVTypeRegistry**: CSV type definitions and validation rules
- **LLMService**: Optional error explanation enhancement