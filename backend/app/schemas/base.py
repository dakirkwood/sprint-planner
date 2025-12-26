"""Base Pydantic models and all enums."""

from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Generic, TypeVar
from datetime import datetime
from uuid import UUID
from enum import Enum

# Generic type for paginated responses
T = TypeVar("T")


# =============================================================================
# SESSION & WORKFLOW ENUMS
# =============================================================================


class SessionStage(str, Enum):
    """Workflow stage progression for sessions."""

    SITE_INFO_COLLECTION = "site_info_collection"
    UPLOAD = "upload"
    PROCESSING = "processing"
    REVIEW = "review"
    JIRA_EXPORT = "jira_export"
    COMPLETED = "completed"


class SessionStatus(str, Enum):
    """Overall session status."""

    ACTIVE = "active"
    EXPORTING = "exporting"
    FAILED = "failed"
    COMPLETED = "completed"


# =============================================================================
# VALIDATION ENUMS
# =============================================================================


class AdfValidationStatus(str, Enum):
    """ADF validation task lifecycle states (used by SessionValidation model)."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class FileValidationStatus(str, Enum):
    """CSV file validation result states (used by UploadedFile model)."""

    PENDING = "pending"
    VALID = "valid"
    INVALID = "invalid"


# =============================================================================
# BACKGROUND TASK ENUMS
# =============================================================================


class TaskType(str, Enum):
    """Background task types tracked in SessionTask model."""

    PROCESSING = "processing"
    EXPORT = "export"
    ADF_VALIDATION = "adf_validation"


class TaskStatus(str, Enum):
    """Background task lifecycle states."""

    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# =============================================================================
# JIRA INTEGRATION ENUMS
# =============================================================================


class JiraUploadStatus(str, Enum):
    """Attachment upload status to Jira (used by Attachment model)."""

    PENDING = "pending"
    UPLOADED = "uploaded"
    FAILED = "failed"


# =============================================================================
# ERROR HANDLING ENUMS
# =============================================================================


class ErrorCategory(str, Enum):
    """Error categorization based on 'who can fix it' strategy."""

    USER_FIXABLE = "user_fixable"
    ADMIN_REQUIRED = "admin_required"
    TEMPORARY = "temporary"


class ErrorSeverity(str, Enum):
    """Error severity levels for UI treatment."""

    BLOCKING = "blocking"
    WARNING = "warning"
    INFO = "info"


# =============================================================================
# AUDIT LOG ENUMS
# =============================================================================


class EventCategory(str, Enum):
    """Audit log event categories aligned with workflow stages."""

    SESSION = "session"
    UPLOAD = "upload"
    PROCESSING = "processing"
    REVIEW = "review"
    JIRA_EXPORT = "jira_export"
    SYSTEM = "system"


class AuditLevel(str, Enum):
    """Audit log detail levels for filtering and cleanup."""

    BASIC = "basic"
    COMPREHENSIVE = "comprehensive"


# =============================================================================
# BASE CLASSES
# =============================================================================


class BaseRequest(BaseModel):
    """Base class for all API requests with common configuration."""

    model_config = ConfigDict(str_strip_whitespace=True)


class BaseResponse(BaseModel):
    """Base class for all API responses with correlation tracking."""

    request_id: Optional[str] = None


# =============================================================================
# ERROR HANDLING MODELS
# =============================================================================


class ErrorResponse(BaseModel):
    """Standardized error response following 'who can fix it' pattern."""

    error_category: ErrorCategory
    user_message: str
    recovery_actions: List[str]
    technical_details: Optional[dict] = None
    error_code: Optional[str] = None


# =============================================================================
# COMMON ENTITY PATTERNS
# =============================================================================


class EntityReference(BaseModel):
    """Generic entity reference with UUID and display label."""

    id: UUID
    label: str


# =============================================================================
# PAGINATION MODELS
# =============================================================================


class PaginationInfo(BaseModel):
    """Pagination metadata for paginated responses."""

    page: int
    limit: int
    total: int
    has_next: bool


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper for any entity type."""

    items: List[T]
    pagination: PaginationInfo


# =============================================================================
# COMMON FIELD PATTERNS
# =============================================================================


class ValidationWarning(BaseModel):
    """Non-blocking validation warnings."""

    warning_type: str
    message: str
    affected_entities: Optional[List[str]] = None


class CsvSourceReference(BaseModel):
    """References to source CSV files for debugging."""

    filename: str
    rows: List[int]
