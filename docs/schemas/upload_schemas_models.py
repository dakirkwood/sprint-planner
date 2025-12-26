# Upload Stage Pydantic Models
# /backend/app/schemas/upload_schemas.py

from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID

# Import base models
from .base_schemas import BaseRequest, BaseResponse, ErrorCategory


# File Upload Models
class FileUploadResponse(BaseResponse):
    success: bool
    files_processed: List['UploadedFileInfo']
    available_classifications: List['CsvTypeOption']
    detection_errors: List['FileDetectionError']


class UploadedFileInfo(BaseModel):
    file_id: UUID
    original_filename: str
    normalized_filename: str  # Cleaned up for consistency
    file_size_bytes: int
    row_count: int
    detected_csv_type: Optional[str]  # Auto-detected classification
    detection_confidence: str  # "high", "medium", "low", "unknown"


class CsvTypeOption(BaseModel):
    value: str      # "bundles"
    label: str      # "Content Types (Bundles)"


class FileDetectionError(BaseModel):
    filename: str
    error_message: str  # Non-blocking detection issues


# Classification Models
class ClassificationUpdateRequest(BaseRequest):
    file_classifications: List['FileClassification']


class FileClassification(BaseModel):
    file_id: UUID
    csv_type: str  # Must be valid key from CSV_TYPE_REGISTRY


class ClassificationUpdateResponse(BaseResponse):
    success: bool
    files_updated: List[UploadedFileInfo]
    ready_for_validation: bool  # All files have classifications


# Validation Models
class ValidationResponse(BaseResponse):
    success: bool
    ready_for_processing: bool
    summary: 'ValidationSummary'
    errors: List['ValidationError']  # Empty if success=True


class ValidationSummary(BaseModel):
    total_files: int
    total_entities: int
    schema_checks_passed: int
    content_checks_passed: int
    relationship_checks_passed: int
    ready_message: str  # "Ready to generate 23 tickets from 5 CSV files"


class ValidationError(BaseModel):
    file_id: UUID
    filename: str
    declared_csv_type: str  # What user said it was
    error_category: ErrorCategory
    error_phase: str        # "schema", "content", "relationships"
    error_summary: str      # Pattern-detected summary
    detailed_errors: List['DetailedError']
    llm_explanation_available: bool


class DetailedError(BaseModel):
    error_type: str         # "missing_column", "invalid_value", "missing_reference"
    row_number: Optional[int]  # None for schema errors
    column_name: Optional[str]
    error_message: str
    current_value: Optional[str]
    suggested_values: List[str]  # For reference errors


# Custom Entity Dependencies Models
class CustomDependencyRequest(BaseRequest):
    custom_relationships: List['CustomRelationship']


class CustomRelationship(BaseModel):
    dependent_file_id: UUID      # File that depends on another
    dependency_file_id: UUID     # File it depends on
    relationship_column: str     # Column name containing the reference


class CustomDependencyResponse(BaseResponse):
    success: bool
    relationships_configured: int
    ready_for_validation: bool


# Optional LLM Enhancement Model
class ErrorExplanationResponse(BaseResponse):
    error_id: UUID
    llm_explanation: str
    suggested_actions: List[str]
    processing_time_ms: int