"""
Tests for AES-256 Encryption Service

Sprint 6 - Security, Testing & Launch
"""
import pytest
import base64
import json
from cryptography.fernet import Fernet

from app.security.encryption import (
    EncryptionService,
    get_encryption_service,
    encrypt,
    decrypt,
    encrypt_token,
    decrypt_token,
    encrypt_transcript,
    decrypt_transcript,
    encrypt_embedding,
    decrypt_embedding,
)


class TestEncryptionService:
    """Test EncryptionService class"""

    def test_initialization_with_custom_key(self):
        """Test service initializes with custom key"""
        custom_key = Fernet.generate_key().decode('utf-8')
        service = EncryptionService(encryption_key=custom_key)
        assert service.key == custom_key.encode()

    def test_initialization_with_default_key(self):
        """Test service initializes with derived key from settings"""
        service = EncryptionService()
        assert service.key is not None
        assert isinstance(service.key, bytes)

    def test_invalid_key_raises_error(self):
        """Test initialization with invalid key raises error"""
        with pytest.raises(ValueError, match="Invalid encryption key format"):
            EncryptionService(encryption_key="invalid-key")

    def test_key_derivation_is_deterministic(self):
        """Test key derivation from same secret produces same key"""
        secret = "test-secret-key-for-derivation"
        key1 = EncryptionService._derive_key_from_secret(secret)
        key2 = EncryptionService._derive_key_from_secret(secret)
        assert key1 == key2

    def test_key_derivation_different_secrets(self):
        """Test different secrets produce different keys"""
        key1 = EncryptionService._derive_key_from_secret("secret1")
        key2 = EncryptionService._derive_key_from_secret("secret2")
        assert key1 != key2

class TestBasicEncryption:
    """Test basic encrypt/decrypt functionality"""

    @pytest.fixture
    def service(self):
        """Create encryption service instance"""
        return EncryptionService()

    def test_encrypt_decrypt_string(self, service):
        """Test encrypting and decrypting a string"""
        plaintext = "This is a secret message"
        encrypted = service.encrypt(plaintext)

        # Encrypted should be different from plaintext
        assert encrypted != plaintext

        # Decryption should restore original
        decrypted = service.decrypt(encrypted)
        assert decrypted == plaintext

    def test_encrypt_returns_base64(self, service):
        """Test encrypted output is valid base64"""
        plaintext = "Test message"
        encrypted = service.encrypt(plaintext)

        # Should be valid base64 (will raise if invalid)
        try:
            base64.urlsafe_b64decode(encrypted.encode())
        except Exception:
            pytest.fail("Encrypted output is not valid base64")

    def test_encrypt_empty_string_raises_error(self, service):
        """Test encrypting empty string raises error"""
        with pytest.raises(ValueError, match="Cannot encrypt empty string"):
            service.encrypt("")

    def test_decrypt_empty_string_raises_error(self, service):
        """Test decrypting empty string raises error"""
        with pytest.raises(ValueError, match="Cannot decrypt empty string"):
            service.decrypt("")

    def test_decrypt_invalid_ciphertext_raises_error(self, service):
        """Test decrypting invalid ciphertext raises error"""
        with pytest.raises(ValueError, match="Decryption failed"):
            service.decrypt("invalid-ciphertext")

    def test_same_plaintext_different_ciphertexts(self, service):
        """Test same plaintext produces different ciphertexts (IV protection)"""
        plaintext = "Repeated message"
        encrypted1 = service.encrypt(plaintext)
        encrypted2 = service.encrypt(plaintext)

        # Different ciphertexts (due to random IV)
        assert encrypted1 != encrypted2

        # But both decrypt to same plaintext
        assert service.decrypt(encrypted1) == plaintext
        assert service.decrypt(encrypted2) == plaintext

    def test_encrypt_unicode_characters(self, service):
        """Test encrypting text with unicode characters"""
        plaintext = "Hello 世界 🌍 Привет"
        encrypted = service.encrypt(plaintext)
        decrypted = service.decrypt(encrypted)
        assert decrypted == plaintext

    def test_encrypt_long_text(self, service):
        """Test encrypting long text (>10KB)"""
        plaintext = "A" * 50000  # 50KB of text
        encrypted = service.encrypt(plaintext)
        decrypted = service.decrypt(encrypted)
        assert decrypted == plaintext
        assert len(decrypted) == 50000


class TestBytesEncryption:
    """Test encrypt/decrypt for binary data"""

    @pytest.fixture
    def service(self):
        return EncryptionService()

    def test_encrypt_decrypt_bytes(self, service):
        """Test encrypting and decrypting bytes"""
        data = b"Binary data \x00\x01\x02\xff"
        encrypted = service.encrypt_bytes(data)
        decrypted = service.decrypt_bytes(encrypted)
        assert decrypted == data

    def test_encrypt_empty_bytes_raises_error(self, service):
        """Test encrypting empty bytes raises error"""
        with pytest.raises(ValueError, match="Cannot encrypt empty bytes"):
            service.encrypt_bytes(b"")

    def test_decrypt_empty_bytes_raises_error(self, service):
        """Test decrypting empty bytes raises error"""
        with pytest.raises(ValueError, match="Cannot decrypt empty bytes"):
            service.decrypt_bytes(b"")


class TestTokenEncryption:
    """Test token encryption (OAuth tokens, API keys)"""

    @pytest.fixture
    def service(self):
        return EncryptionService()

    def test_encrypt_decrypt_oauth_token(self, service):
        """Test encrypting OAuth token"""
        oauth_token = "ya29.a0AfH6SMBx..."  # Example OAuth token
        encrypted = service.encrypt_token(oauth_token)
        decrypted = service.decrypt_token(encrypted)
        assert decrypted == oauth_token

    def test_encrypt_decrypt_api_key(self, service):
        """Test encrypting API key"""
        api_key = "sk_test_REDACTED_EXAMPLE_KEY"  # Example API key (redacted)
        encrypted = service.encrypt_token(api_key)
        decrypted = service.decrypt_token(encrypted)
        assert decrypted == api_key

    def test_encrypted_token_different_from_plaintext(self, service):
        """Test encrypted token is different from plaintext"""
        token = "secret-api-key-12345"
        encrypted = service.encrypt_token(token)
        assert encrypted != token
        assert token not in encrypted  # Plaintext not visible in ciphertext


class TestTranscriptEncryption:
    """Test transcript encryption (meetings, media)"""

    @pytest.fixture
    def service(self):
        return EncryptionService()

    def test_encrypt_decrypt_meeting_transcript(self, service):
        """Test encrypting meeting transcript"""
        transcript = """
        [00:00:15] Speaker 1: Let's discuss Q4 financials.
        [00:00:30] Speaker 2: Revenue is up 25% year over year.
        [00:00:45] Speaker 1: Great! What about expenses?
        """
        encrypted = service.encrypt_transcript(transcript)
        decrypted = service.decrypt_transcript(encrypted)
        assert decrypted == transcript

    def test_encrypt_decrypt_loom_transcript(self, service):
        """Test encrypting Loom video transcript"""
        transcript = "Hi team, in this Loom I'm going to show you the new feature..."
        encrypted = service.encrypt_transcript(transcript)
        decrypted = service.decrypt_transcript(encrypted)
        assert decrypted == transcript

    def test_transcript_with_sensitive_content(self, service):
        """Test encrypting transcript with sensitive business data"""
        transcript = "Our burn rate is $500K/month. Runway: 18 months. Confidential!"
        encrypted = service.encrypt_transcript(transcript)

        # Sensitive data not visible in ciphertext
        assert "$500K" not in encrypted
        assert "burn rate" not in encrypted
        assert "Confidential" not in encrypted

        # But decrypts correctly
        decrypted = service.decrypt_transcript(encrypted)
        assert "$500K" in decrypted
        assert "Confidential" in decrypted


class TestEmbeddingEncryption:
    """Test vector embedding encryption"""

    @pytest.fixture
    def service(self):
        return EncryptionService()

    def test_encrypt_decrypt_embedding(self, service):
        """Test encrypting vector embedding"""
        embedding = [0.1, 0.2, 0.3, -0.5, 0.8, -0.2]
        encrypted = service.encrypt_embedding(embedding)
        decrypted = service.decrypt_embedding(encrypted)

        # Should match original embedding
        assert len(decrypted) == len(embedding)
        for i, val in enumerate(embedding):
            assert abs(decrypted[i] - val) < 1e-9  # Float precision

    def test_encrypt_large_embedding(self, service):
        """Test encrypting 1536-dimension embedding (OpenAI ada-002)"""
        import random
        embedding = [random.random() for _ in range(1536)]
        encrypted = service.encrypt_embedding(embedding)
        decrypted = service.decrypt_embedding(encrypted)

        assert len(decrypted) == 1536
        # Check first and last values
        assert abs(decrypted[0] - embedding[0]) < 1e-9
        assert abs(decrypted[-1] - embedding[-1]) < 1e-9

    def test_embedding_encryption_format(self, service):
        """Test embedding is stored as encrypted JSON"""
        embedding = [1.0, 2.0, 3.0]
        encrypted = service.encrypt_embedding(embedding)

        # Should not contain plaintext numbers
        assert "1.0" not in encrypted
        assert "2.0" not in encrypted
        assert "[" not in encrypted  # No JSON structure visible


class TestConvenienceFunctions:
    """Test module-level convenience functions"""

    def test_convenience_encrypt_decrypt(self):
        """Test convenience functions for encrypt/decrypt"""
        plaintext = "Test message"
        encrypted = encrypt(plaintext)
        decrypted = decrypt(encrypted)
        assert decrypted == plaintext

    def test_convenience_token_functions(self):
        """Test convenience functions for tokens"""
        token = "api-key-12345"
        encrypted = encrypt_token(token)
        decrypted = decrypt_token(encrypted)
        assert decrypted == token

    def test_convenience_transcript_functions(self):
        """Test convenience functions for transcripts"""
        transcript = "Meeting transcript content"
        encrypted = encrypt_transcript(transcript)
        decrypted = decrypt_transcript(encrypted)
        assert decrypted == transcript

    def test_convenience_embedding_functions(self):
        """Test convenience functions for embeddings"""
        embedding = [0.5, -0.3, 0.8]
        encrypted = encrypt_embedding(embedding)
        decrypted = decrypt_embedding(encrypted)
        assert decrypted == embedding

    def test_get_encryption_service_singleton(self):
        """Test get_encryption_service returns same instance"""
        service1 = get_encryption_service()
        service2 = get_encryption_service()
        assert service1 is service2  # Same object


class TestKeyRotation:
    """Test encryption key rotation"""

    def test_rotate_key(self):
        """Test rotating encryption key"""
        # Original service with old key
        old_key = Fernet.generate_key().decode('utf-8')
        old_service = EncryptionService(encryption_key=old_key)

        # Encrypt with old key
        plaintext = "Sensitive data"
        old_ciphertext = old_service.encrypt(plaintext)

        # Generate new key
        new_key = Fernet.generate_key().decode('utf-8')

        # Rotate
        new_ciphertext = old_service.rotate_key(new_key, old_ciphertext)

        # New ciphertext should be different
        assert new_ciphertext != old_ciphertext

        # But decrypts correctly with new key
        new_service = EncryptionService(encryption_key=new_key)
        decrypted = new_service.decrypt(new_ciphertext)
        assert decrypted == plaintext

        # Old key can no longer decrypt new ciphertext
        with pytest.raises(ValueError):
            old_service.decrypt(new_ciphertext)

    def test_rotate_key_for_tokens(self):
        """Test rotating key for stored tokens"""
        old_key = Fernet.generate_key().decode('utf-8')
        old_service = EncryptionService(encryption_key=old_key)

        # Multiple tokens
        tokens = {
            "zoom": "zoom-oauth-token-abc123",
            "slack": "xoxb-slack-token-456",
            "discord": "discord-bot-token-789",
        }

        # Encrypt all with old key
        encrypted_tokens = {
            name: old_service.encrypt_token(token) for name, token in tokens.items()
        }

        # Rotate to new key
        new_key = Fernet.generate_key().decode('utf-8')
        rotated_tokens = {
            name: old_service.rotate_key(new_key, enc_token)
            for name, enc_token in encrypted_tokens.items()
        }

        # Decrypt with new key
        new_service = EncryptionService(encryption_key=new_key)
        decrypted_tokens = {
            name: new_service.decrypt_token(enc_token)
            for name, enc_token in rotated_tokens.items()
        }

        # All tokens match originals
        assert decrypted_tokens == tokens


class TestKeyGeneration:
    """Test key generation utilities"""

    def test_generate_key(self):
        """Test generating new encryption key"""
        key = EncryptionService.generate_key()

        # Should be valid base64
        assert isinstance(key, str)
        try:
            base64.urlsafe_b64decode(key.encode())
        except Exception:
            pytest.fail("Generated key is not valid base64")

        # Should be 32 bytes (256 bits) when decoded
        decoded = base64.urlsafe_b64decode(key.encode())
        assert len(decoded) == 32

    def test_generated_key_works(self):
        """Test generated key works for encryption"""
        key = EncryptionService.generate_key()
        service = EncryptionService(encryption_key=key)

        plaintext = "Test message"
        encrypted = service.encrypt(plaintext)
        decrypted = service.decrypt(encrypted)
        assert decrypted == plaintext

    def test_each_generated_key_is_unique(self):
        """Test generate_key produces unique keys"""
        key1 = EncryptionService.generate_key()
        key2 = EncryptionService.generate_key()
        key3 = EncryptionService.generate_key()

        assert key1 != key2
        assert key2 != key3
        assert key1 != key3


class TestCrossServiceDecryption:
    """Test data encrypted with one service can be decrypted by another with same key"""

    def test_cross_service_with_same_key(self):
        """Test two services with same key can decrypt each other's data"""
        shared_key = Fernet.generate_key().decode('utf-8')

        service1 = EncryptionService(encryption_key=shared_key)
        service2 = EncryptionService(encryption_key=shared_key)

        plaintext = "Shared secret"

        # Encrypt with service1
        encrypted = service1.encrypt(plaintext)

        # Decrypt with service2
        decrypted = service2.decrypt(encrypted)

        assert decrypted == plaintext

    def test_cross_service_with_different_keys_fails(self):
        """Test services with different keys cannot decrypt each other's data"""
        key1 = Fernet.generate_key().decode('utf-8')
        key2 = Fernet.generate_key().decode('utf-8')

        service1 = EncryptionService(encryption_key=key1)
        service2 = EncryptionService(encryption_key=key2)

        plaintext = "Secret message"
        encrypted = service1.encrypt(plaintext)

        # Service2 cannot decrypt service1's data
        with pytest.raises(ValueError, match="Decryption failed"):
            service2.decrypt(encrypted)


class TestSecurityProperties:
    """Test security properties of encryption"""

    @pytest.fixture
    def service(self):
        return EncryptionService()

    def test_encrypted_data_not_readable(self, service):
        """Test encrypted data does not contain readable plaintext"""
        sensitive_data = "SSN: 123-45-6789, Password: SuperSecret123!"
        encrypted = service.encrypt(sensitive_data)

        # Plaintext keywords not visible
        assert "SSN" not in encrypted
        assert "123-45-6789" not in encrypted
        assert "Password" not in encrypted
        assert "SuperSecret123" not in encrypted

    def test_ciphertext_appears_random(self, service):
        """Test ciphertext has high entropy (appears random)"""
        plaintext = "A" * 100  # Repetitive input
        encrypted = service.encrypt(plaintext)

        # Encrypted should not have obvious patterns
        assert encrypted.count("A") < 10  # Very few 'A's in ciphertext
        assert len(set(encrypted)) > 20  # High character diversity

    def test_tampered_ciphertext_fails_decryption(self, service):
        """Test tampered ciphertext cannot be decrypted"""
        plaintext = "Original message"
        encrypted = service.encrypt(plaintext)

        # Tamper with ciphertext (change one character)
        tampered = encrypted[:-1] + ("X" if encrypted[-1] != "X" else "Y")

        # Decryption should fail
        with pytest.raises(ValueError, match="Decryption failed"):
            service.decrypt(tampered)

    def test_encryption_is_deterministic_with_same_iv(self, service):
        """Test encryption uses random IV (non-deterministic)"""
        plaintext = "Test"

        # Encrypt same plaintext multiple times
        results = [service.encrypt(plaintext) for _ in range(5)]

        # All ciphertexts should be different (due to random IV)
        assert len(set(results)) == 5

    def test_partial_ciphertext_cannot_be_decrypted(self, service):
        """Test partial ciphertext fails decryption (integrity check)"""
        plaintext = "Complete message"
        encrypted = service.encrypt(plaintext)

        # Take only first half
        partial = encrypted[:len(encrypted) // 2]

        # Should fail to decrypt
        with pytest.raises(ValueError, match="Decryption failed"):
            service.decrypt(partial)
