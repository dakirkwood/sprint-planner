"""SQLAlchemy models for the Drupal Ticket Generator."""

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.session import Session, SessionTask, SessionValidation
from app.models.upload import UploadedFile
from app.models.ticket import Ticket, TicketDependency, Attachment
from app.models.auth import JiraAuthToken, JiraProjectContext
from app.models.error import SessionError, AuditLog

__all__ = [
    # Base
    "Base",
    "TimestampMixin",
    "UUIDPrimaryKeyMixin",
    # Session models
    "Session",
    "SessionTask",
    "SessionValidation",
    # Upload models
    "UploadedFile",
    # Ticket models
    "Ticket",
    "TicketDependency",
    "Attachment",
    # Auth models
    "JiraAuthToken",
    "JiraProjectContext",
    # Error models
    "SessionError",
    "AuditLog",
]
