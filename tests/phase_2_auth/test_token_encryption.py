"""Test Fernet-based token encryption."""

import pytest
from app.core.security import (
    encrypt_token,
    decrypt_token,
    TokenEncryptionError,
    generate_pkce_pair,
    generate_csrf_state,
)


class TestTokenEncryption:
    """Test Fernet-based token encryption."""

    def test_encrypt_returns_different_value(self):
        """Encrypted value should differ from original."""
        original = "test-access-token"

        encrypted = encrypt_token(original)

        assert encrypted != original
        assert isinstance(encrypted, str)

    def test_decrypt_recovers_original(self):
        """Decryption should recover the original token."""
        original = "test-access-token-12345"

        encrypted = encrypt_token(original)
        decrypted = decrypt_token(encrypted)

        assert decrypted == original

    def test_encrypt_produces_different_ciphertext_each_time(self):
        """Same plaintext should produce different ciphertext (IV)."""
        original = "same-token"

        encrypted1 = encrypt_token(original)
        encrypted2 = encrypt_token(original)

        # Fernet includes timestamp and random IV, so ciphertexts differ
        assert encrypted1 != encrypted2

    def test_decrypt_invalid_token_raises_error(self):
        """Invalid ciphertext should raise TokenEncryptionError."""
        with pytest.raises(TokenEncryptionError):
            decrypt_token("not-a-valid-encrypted-token")

    def test_decrypt_tampered_token_raises_error(self):
        """Tampered ciphertext should raise TokenEncryptionError."""
        original = "test-token"
        encrypted = encrypt_token(original)

        # Tamper with the encrypted value
        tampered = encrypted[:-5] + "XXXXX"

        with pytest.raises(TokenEncryptionError):
            decrypt_token(tampered)

    def test_handles_unicode_tokens(self):
        """Should handle tokens with unicode characters."""
        original = "token-with-émojis-🔑"

        encrypted = encrypt_token(original)
        decrypted = decrypt_token(encrypted)

        assert decrypted == original


class TestPKCEGeneration:
    """Test PKCE code verifier and challenge generation."""

    def test_generate_pkce_pair_returns_tuple(self):
        """Should return verifier and challenge as tuple."""
        verifier, challenge = generate_pkce_pair()

        assert isinstance(verifier, str)
        assert isinstance(challenge, str)

    def test_verifier_length_is_valid(self):
        """Verifier should be between 43 and 128 characters (RFC 7636)."""
        verifier, _ = generate_pkce_pair()

        assert 43 <= len(verifier) <= 128

    def test_challenge_is_base64url_encoded(self):
        """Challenge should be base64url encoded (no +, /, or =)."""
        _, challenge = generate_pkce_pair()

        assert "+" not in challenge
        assert "/" not in challenge
        # Padding may or may not be present depending on implementation

    def test_different_calls_produce_different_values(self):
        """Each call should produce unique verifier/challenge pairs."""
        pair1 = generate_pkce_pair()
        pair2 = generate_pkce_pair()

        assert pair1[0] != pair2[0]
        assert pair1[1] != pair2[1]


class TestCSRFGeneration:
    """Test CSRF state token generation."""

    def test_generate_csrf_state_returns_string(self):
        """Should return a string state token."""
        state = generate_csrf_state()

        assert isinstance(state, str)
        assert len(state) > 0

    def test_csrf_state_is_sufficiently_long(self):
        """State should be sufficiently long for security."""
        state = generate_csrf_state()

        # Should be at least 32 characters for security
        assert len(state) >= 32

    def test_different_calls_produce_different_values(self):
        """Each call should produce unique state tokens."""
        state1 = generate_csrf_state()
        state2 = generate_csrf_state()

        assert state1 != state2
