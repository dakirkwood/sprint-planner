# Attachment Model - SQLAlchemy Implementation Specification

## 1. Class Name
**Attachment** - Auto-generated attachments for oversized ticket content

## 2. Directory Path
`/backend/app/models/ticket.py` (same file as other ticket-related models)

## 3. Purpose & Responsibilities
- Store attachment content when ticket descriptions exceed Jira character limits
- Handle attachment metadata for Jira upload integration
- Track attachment upload status and Jira references
- Enable attachment content recovery and debugging

## 4. Methods and Properties

### Core Fields (9 total)
```python
id: UUID (primary key)
session_id: UUID (foreign key to sessions)
ticket_id: UUID (foreign key to tickets)
filename: str  # e.g., "configure_product_fields_analysis.md"
content: str  # Markdown content only
file_size_bytes: int
jira_attachment_id: Optional[str]  # Set after successful upload to Jira
jira_upload_status: JiraUploadStatus = 'pending'  # enum
created_at: datetime
```

### Enum Definition
```python
class JiraUploadStatus(str, Enum):
    PENDING = "pending"
    UPLOADED = "uploaded" 
    FAILED = "failed"
```

### Instance Methods
```python
def mark_uploaded_to_jira(self, jira_attachment_id: str) -> None:
    # Set upload status and Jira reference after successful upload

def mark_upload_failed(self) -> None:
    # Set failed status, clear any partial Jira references

@classmethod
def find_pending_uploads(cls, session_id: UUID) -> List['Attachment']:
    # Get attachments that need to be uploaded to Jira

@classmethod
def get_total_attachment_size(cls, session_id: UUID) -> int:
    # Total size of all attachments for session (for limits/debugging)
```

### Properties
```python
@property
def file_size_kb(self) -> float:
    # File size in kilobytes for display

@property
def is_uploaded_to_jira(self) -> bool:
    # True if successfully uploaded to Jira

@property
def content_preview(self) -> str:
    # First 200 characters of content for UI preview
```

## 5. Dependencies/Imports
```python
from sqlalchemy import Column, String, Text, Integer, ForeignKey, DateTime, Enum as SQLEnum, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
from enum import Enum
from typing import List, Optional
import uuid
```

## 6. Database Integration

### Table Definition
```python
__tablename__ = "attachments"
__table_args__ = (
    Index('idx_attachments_session_id', 'session_id'),
    Index('idx_attachments_ticket_id', 'ticket_id'),
    Index('idx_attachments_jira_upload_status', 'jira_upload_status')
)
```

### Relationships
```python
ticket = relationship("Ticket", back_populates="attachment")
```

### Foreign Keys
```python
session_id = Column(UUID(as_uuid=True), ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False)
ticket_id = Column(UUID(as_uuid=True), ForeignKey('tickets.id', ondelete='CASCADE'), nullable=False)
```

### Transaction Strategy
- Participates in repository-managed transactions
- Created when ticket content exceeds character limits (~30,000 characters)
- Cascading delete with both session and ticket

### Content Size Validation
```python
# Application-level validation
MAX_ATTACHMENT_SIZE = 1024 * 1024  # 1MB

def create_attachment(content: str, filename: str) -> Attachment:
    if len(content.encode('utf-8')) > MAX_ATTACHMENT_SIZE:
        raise AttachmentValidationError(
            message=f"Attachment content too large: {len(content)} characters",
            category="admin_required"  # Likely a bug in generation
        )
```

## 7. Logging Events

### Attachment Lifecycle
- **INFO**: Attachment creation and Jira upload events with session context
- **DEBUG**: Content size tracking and upload progress
- **AUDIT**: Upload status changes and Jira integration success/failure

### Specific Logging
- **INFO**: `Attachment created for session {session_id}: {filename} ({file_size_kb}KB)`
- **INFO**: `Attachment uploaded to Jira: {filename} → {jira_attachment_id} (session: {session_id})`
- **WARNING**: `Attachment upload failed for session {session_id}: {filename} - {error_details}`
- **DEBUG**: Content generation details and size optimization

## 8. Error Handling

### Error Categories
- **user_fixable**: Generally none - attachments are auto-generated
- **admin_required**: Content size issues, generation failures, Jira upload configuration
- **temporary**: Network timeouts during Jira upload, service unavailable

### Specific Error Patterns
```python
# Content size validation
if len(content.encode('utf-8')) > MAX_ATTACHMENT_SIZE:
    raise AttachmentValidationError(
        message=f"Attachment content too large: {len(content)} characters",
        category="admin_required"  # Likely a bug in generation
    )

# Jira upload failure
if upload_failed:
    raise AttachmentUploadError(
        message=f"Failed to upload attachment {filename} to Jira",
        category="temporary"  # Most upload failures are transient
    )
```

## Key Design Decisions

### Database Storage
- Content stored in database TEXT field rather than file system
- Simplifies backup/restore and deployment (no persistent volumes needed)
- Automatic cascading cleanup with sessions (7-day retention)
- Consistent with operational simplicity approach throughout application

### Markdown Only Format
- Single content format reduces complexity
- Sufficient for generated ticket content (no user uploads)
- Easy to read and debug when needed

### One Attachment Per Ticket
- Simplified 1:1 relationship via attachment_id foreign key on tickets table
- UI complexity reduced - single attachment download/view per ticket
- Adequate for auto-generated content from single source (ticket description)

### Cascading Delete Strategy
- Attachments cleaned up automatically when sessions or tickets deleted
- No orphaned files or complex cleanup jobs needed
- Maintains referential integrity across all relationships