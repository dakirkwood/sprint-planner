"""Security utilities for token encryption."""

from cryptography.fernet import Fernet
from typing import Optional
import base64
import hashlib

from app.core.config import settings


def _get_encryption_key() -> bytes:
    """Get or derive encryption key."""
    key = settings.TOKEN_ENCRYPTION_KEY
    if key:
        # If key is provided, ensure it's valid Fernet key format
        if len(key) == 44:
            return key.encode()
        # Otherwise, derive a key from the provided secret
        return base64.urlsafe_b64encode(hashlib.sha256(key.encode()).digest())
    # Generate a deterministic key for development (NOT for production)
    return Fernet.generate_key()


_fernet: Optional[Fernet] = None


def _get_fernet() -> Fernet:
    """Get Fernet instance (singleton)."""
    global _fernet
    if _fernet is None:
        _fernet = Fernet(_get_encryption_key())
    return _fernet


def encrypt_token(token: str) -> str:
    """Encrypt a token for secure storage."""
    fernet = _get_fernet()
    encrypted = fernet.encrypt(token.encode())
    return encrypted.decode()


def decrypt_token(encrypted_token: str) -> str:
    """Decrypt a stored token."""
    fernet = _get_fernet()
    decrypted = fernet.decrypt(encrypted_token.encode())
    return decrypted.decode()
