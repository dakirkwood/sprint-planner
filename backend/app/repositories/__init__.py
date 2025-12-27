# app/repositories/__init__.py
"""
Repository layer for data access.
"""
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
    # SQLAlchemy Implementations
    "SQLAlchemySessionRepository",
    "SQLAlchemyUploadRepository",
    "SQLAlchemyTicketRepository",
    "SQLAlchemyAuthRepository",
    "SQLAlchemyErrorRepository",
]
