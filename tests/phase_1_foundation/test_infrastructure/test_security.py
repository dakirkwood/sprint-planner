"""Tests for security utilities."""

import pytest

from app.core.security import encrypt_token, decrypt_token


class TestTokenEncryption:
    """Test token encryption and decryption."""

    def test_encrypt_token(self):
        """Test token encryption."""
        original = "my_secret_token"

        encrypted = encrypt_token(original)

        assert encrypted != original
        assert len(encrypted) > 0

    def test_decrypt_token(self):
        """Test token decryption."""
        original = "my_secret_token"

        encrypted = encrypt_token(original)
        decrypted = decrypt_token(encrypted)

        assert decrypted == original

    def test_encrypt_decrypt_roundtrip(self):
        """Test encryption and decryption roundtrip."""
        tokens = [
            "simple_token",
            "token_with_special_chars!@#$%^&*()",
            "unicode_token_日本語",
            "very_long_token_" * 100,
            "",
        ]

        for original in tokens:
            encrypted = encrypt_token(original)
            decrypted = decrypt_token(encrypted)
            assert decrypted == original, f"Failed for token: {original[:50]}"

    def test_encrypt_produces_different_output_each_time(self):
        """Test that encryption is not deterministic (uses random IV)."""
        original = "test_token"

        encrypted1 = encrypt_token(original)
        encrypted2 = encrypt_token(original)

        # Fernet uses random IV so encrypted values should differ
        assert encrypted1 != encrypted2

        # But both should decrypt to the same value
        assert decrypt_token(encrypted1) == original
        assert decrypt_token(encrypted2) == original

    def test_decrypt_invalid_token_raises_error(self):
        """Test that decrypting invalid token raises error."""
        with pytest.raises(Exception):
            decrypt_token("invalid_encrypted_token")

    def test_decrypt_tampered_token_raises_error(self):
        """Test that decrypting tampered token raises error."""
        original = "test_token"
        encrypted = encrypt_token(original)

        # Tamper with the encrypted value
        tampered = encrypted[:-5] + "XXXXX"

        with pytest.raises(Exception):
            decrypt_token(tampered)
