"""Repository layer for the Drupal Ticket Generator."""

from app.repositories.interfaces import (
    SessionRepositoryInterface,
    UploadRepositoryInterface,
    TicketRepositoryInterface,
    AuthRepositoryInterface,
    ErrorRepositoryInterface,
)

from app.repositories.sqlalchemy import (
    SQLAlchemySessionRepository,
    SQLAlchemyUploadRepository,
    SQLAlchemyTicketRepository,
    SQLAlchemyAuthRepository,
    SQLAlchemyErrorRepository,
)

__all__ = [
    # Interfaces
    "SessionRepositoryInterface",
    "UploadRepositoryInterface",
    "TicketRepositoryInterface",
    "AuthRepositoryInterface",
    "ErrorRepositoryInterface",
    # Implementations
    "SQLAlchemySessionRepository",
    "SQLAlchemyUploadRepository",
    "SQLAlchemyTicketRepository",
    "SQLAlchemyAuthRepository",
    "SQLAlchemyErrorRepository",
]
