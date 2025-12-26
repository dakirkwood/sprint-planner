"""Security utilities for token encryption and OAuth helpers."""

import base64
import hashlib
import secrets
from typing import Optional, Tuple

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


class TokenEncryptionError(Exception):
    """Raised when token encryption or decryption fails."""

    pass


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
    """Decrypt a stored token.

    Raises:
        TokenEncryptionError: If decryption fails due to invalid or tampered token.
    """
    try:
        fernet = _get_fernet()
        decrypted = fernet.decrypt(encrypted_token.encode())
        return decrypted.decode()
    except (InvalidToken, ValueError, TypeError) as e:
        raise TokenEncryptionError(f"Failed to decrypt token: {e}") from e


def generate_pkce_pair() -> Tuple[str, str]:
    """Generate PKCE code verifier and challenge pair.

    Returns:
        Tuple of (code_verifier, code_challenge).
        The verifier is a random 64-character string.
        The challenge is the base64url-encoded SHA256 hash of the verifier.
    """
    # Generate a random 64-character code verifier (within RFC 7636 bounds of 43-128)
    code_verifier = secrets.token_urlsafe(48)  # 48 bytes = 64 chars base64url

    # Create code challenge as base64url(sha256(code_verifier))
    verifier_bytes = code_verifier.encode("ascii")
    sha256_hash = hashlib.sha256(verifier_bytes).digest()
    code_challenge = base64.urlsafe_b64encode(sha256_hash).decode("ascii").rstrip("=")

    return code_verifier, code_challenge


def generate_csrf_state() -> str:
    """Generate a cryptographically secure CSRF state token.

    Returns:
        A 43-character base64url-encoded random string.
    """
    return secrets.token_urlsafe(32)  # 32 bytes = 43 chars base64url
