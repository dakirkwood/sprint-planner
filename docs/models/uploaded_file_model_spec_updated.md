# UploadedFile Model - SQLAlchemy Implementation Specification

## UPDATED: December 25, 2025
- Renamed `ValidationStatus` enum to `FileValidationStatus` to avoid conflict with `AdfValidationStatus`
- Updated imports and references throughout

---

## 1. Class Name
**UploadedFile** - CSV file metadata and parsed content storage

## 2. Directory Path
`/backend/app/models/upload.py` (new file for upload-related models)

## 3. Purpose & Responsibilities
- Store uploaded CSV file metadata (filename, size, type)
- Hold parsed CSV content as JSON for processing
- Track validation status and classification
- Enable file classification and content queries

## 4. Methods and Properties

### Core Fields (10 total)
```python
id: UUID (primary key)
session_id: UUID (foreign key to sessions)
filename: str
file_size_bytes: int
csv_type: Optional[str]  # Final classification: 'bundles', 'fields', 'custom', etc.
parsed_content: dict  # JSON: CSV data with headers and rows
validation_status: FileValidationStatus  # enum: 'pending' | 'valid' | 'invalid'
row_count: int
uploaded_at: datetime
processed_at: Optional[datetime]
```

### Enum Definition
```python
# Defined in /backend/app/schemas/base_schemas.py
class FileValidationStatus(str, Enum):
    """CSV file validation result states"""
    PENDING = "pending"
    VALID = "valid"
    INVALID = "invalid"
```

### Instance Methods
```python
def mark_validated(self, is_valid: bool) -> None:
    # Set validation status and processed_at timestamp
    self.validation_status = FileValidationStatus.VALID if is_valid else FileValidationStatus.INVALID
    self.processed_at = datetime.utcnow()

def get_csv_headers(self) -> List[str]:
    # Extract column headers from parsed_content

def get_row_data(self) -> List[dict]:
    # Extract row data from parsed_content

@classmethod
def find_by_csv_type(cls, session_id: UUID, csv_type: str) -> List['UploadedFile']:
    # Find all files of specific type for session

@classmethod
def get_total_entities(cls, session_id: UUID) -> int:
    # Count total entities across all files for progress estimation
```

### Properties
```python
@property
def is_classified(self) -> bool:
    # True if csv_type is not None

@property
def is_valid(self) -> bool:
    # True if validation_status == FileValidationStatus.VALID

@property
def entity_count(self) -> int:
    # Number of entities (rows) in this file

@property
def file_size_mb(self) -> float:
    # File size in megabytes for display
```

## 5. Dependencies/Imports
```python
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import List, Dict, Optional
import uuid

# Enum imported for type hints (actual DB storage is string)
from app.schemas.base_schemas import FileValidationStatus
```

## 6. Database Integration

### Table Definition
```python
__tablename__ = "uploaded_files"
__table_args__ = (
    Index('idx_uploaded_files_session_id', 'session_id'),
    Index('idx_uploaded_files_csv_type', 'csv_type'),
    Index('idx_uploaded_files_validation_status', 'validation_status')
)
```

### Relationships
```python
session = relationship("Session", back_populates="uploaded_files")
```

### Foreign Key
```python
session_id = Column(UUID(as_uuid=True), ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False)
```

### Transaction Strategy
- Participates in repository-managed transactions
- Created during file upload, updated during classification and validation
- Cascading delete with parent session

## 7. Logging Events

### File Lifecycle
- **INFO**: File upload and classification events with session context
- **DEBUG**: File processing details (parsing time, content analysis)
- **AUDIT**: File validation results and classification changes

### Specific Logging
- **INFO**: `File uploaded for session {session_id}: {filename} ({file_size_mb}MB, {row_count} rows)`
- **INFO**: `File classified as {csv_type} for session {session_id}: {filename}`
- **WARNING**: `File validation failed for session {session_id}: {filename} - {validation_errors}`
- **DEBUG**: File parsing performance and content analysis details

## 8. Error Handling

### Error Categories
- **user_fixable**: File format issues, invalid CSV structure, classification errors
- **admin_required**: File processing failures, storage issues
- **temporary**: Upload timeouts, processing service unavailable

### Specific Error Patterns
```python
# File size validation
if self.file_size_bytes > 2_097_152:  # 2MB
    raise FileValidationError(
        message=f"File {self.filename} exceeds 2MB limit",
        category="user_fixable"
    )

# CSV parsing validation
if not self.parsed_content or 'headers' not in self.parsed_content:
    raise FileValidationError(
        message=f"Invalid CSV structure in {self.filename}",
        category="user_fixable"
    )
```

## Key Design Decisions

### JSON Content Storage
- Flexible storage for CSV data without requiring normalized row tables
- Sufficient for 2MB file size limits
- Simplifies recovery - single query gets all file content
- Avoids complexity of separate CSV rows model

### Simple Validation Enum
- Three-state validation (pending/valid/invalid) rather than complex tracking
- Covers essential workflow needs without over-engineering
- Easy to understand and debug

### File-Level Classification
- csv_type stored directly on file rather than separate classification table
- Simpler model with fewer JOINs for common operations
- Adequate for single-organization use case

### Enum Naming Convention
- `FileValidationStatus` clearly distinguishes from `AdfValidationStatus` used in SessionValidation model
- Both enums defined centrally in `base_schemas.py` to prevent duplication
