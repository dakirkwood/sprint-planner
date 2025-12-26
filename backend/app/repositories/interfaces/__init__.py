"""Repository interfaces."""

from app.repositories.interfaces.session_repository import SessionRepositoryInterface
from app.repositories.interfaces.upload_repository import UploadRepositoryInterface
from app.repositories.interfaces.ticket_repository import TicketRepositoryInterface
from app.repositories.interfaces.auth_repository import AuthRepositoryInterface
from app.repositories.interfaces.error_repository import ErrorRepositoryInterface

__all__ = [
    "SessionRepositoryInterface",
    "UploadRepositoryInterface",
    "TicketRepositoryInterface",
    "AuthRepositoryInterface",
    "ErrorRepositoryInterface",
]
