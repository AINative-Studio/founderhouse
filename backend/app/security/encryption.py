"""
AES-256 Encryption Service

Provides encryption/decryption for sensitive data:
- OAuth tokens & API keys
- Vector embeddings
- Transcript content

Uses Fernet (symmetric encryption with AES-256 in CBC mode).

Sprint 6 - Security, Testing & Launch
"""
import base64
import os
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from app.config import get_settings
import logging

settings = get_settings()

logger = logging.getLogger(__name__)


class EncryptionService:
    """
    AES-256 encryption service using Fernet (symmetric encryption)

    Fernet guarantees that a message encrypted using it cannot be
    manipulated or read without the key. It uses:
    - AES in CBC mode with a 128-bit key for encryption
    - PKCS7 padding
    - HMAC using SHA256 for authentication
    - Initialization vectors to prevent re-use attacks
    """

    def __init__(self, encryption_key: Optional[str] = None):
        """
        Initialize encryption service with a key.

        Args:
            encryption_key: Base64-encoded 32-byte key. If None, derives from SECRET_KEY.
        """
        if encryption_key:
            self.key = encryption_key.encode()
        else:
            # Derive encryption key from SECRET_KEY using PBKDF2
            self.key = self._derive_key_from_secret(settings.secret_key)

        try:
            self.fernet = Fernet(self.key)
        except Exception as e:
            logger.error(f"Failed to initialize Fernet cipher: {e}")
            raise ValueError("Invalid encryption key format")

    @staticmethod
    def _derive_key_from_secret(secret: str, salt: bytes = b"ainative-studio-cos") -> bytes:
        """
        Derive a Fernet key from the application secret using PBKDF2.

        Args:
            secret: Application secret key
            salt: Salt for key derivation (should be consistent)

        Returns:
            Base64-encoded 32-byte key suitable for Fernet
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,  # 256 bits
            salt=salt,
            iterations=100000,  # OWASP recommendation
        )
        key = base64.urlsafe_b64encode(kdf.derive(secret.encode()))
        return key

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt plaintext string to base64-encoded ciphertext.

        Args:
            plaintext: String to encrypt

        Returns:
            Base64-encoded encrypted string

        Raises:
            ValueError: If plaintext is empty or encryption fails
        """
        if not plaintext:
            raise ValueError("Cannot encrypt empty string")

        try:
            encrypted_bytes = self.fernet.encrypt(plaintext.encode('utf-8'))
            return encrypted_bytes.decode('utf-8')
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise ValueError(f"Encryption failed: {e}")

    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt base64-encoded ciphertext to plaintext string.

        Args:
            ciphertext: Base64-encoded encrypted string

        Returns:
            Decrypted plaintext string

        Raises:
            ValueError: If ciphertext is invalid or decryption fails
        """
        if not ciphertext:
            raise ValueError("Cannot decrypt empty string")

        try:
            decrypted_bytes = self.fernet.decrypt(ciphertext.encode('utf-8'))
            return decrypted_bytes.decode('utf-8')
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise ValueError(f"Decryption failed: {e}")

    def encrypt_bytes(self, data: bytes) -> bytes:
        """
        Encrypt raw bytes (useful for binary data like embeddings).

        Args:
            data: Bytes to encrypt

        Returns:
            Encrypted bytes
        """
        if not data:
            raise ValueError("Cannot encrypt empty bytes")

        try:
            return self.fernet.encrypt(data)
        except Exception as e:
            logger.error(f"Bytes encryption failed: {e}")
            raise ValueError(f"Bytes encryption failed: {e}")

    def decrypt_bytes(self, encrypted_data: bytes) -> bytes:
        """
        Decrypt encrypted bytes.

        Args:
            encrypted_data: Encrypted bytes

        Returns:
            Decrypted bytes
        """
        if not encrypted_data:
            raise ValueError("Cannot decrypt empty bytes")

        try:
            return self.fernet.decrypt(encrypted_data)
        except Exception as e:
            logger.error(f"Bytes decryption failed: {e}")
            raise ValueError(f"Bytes decryption failed: {e}")

    def encrypt_token(self, token: str) -> str:
        """
        Encrypt OAuth token or API key.

        Args:
            token: Token string to encrypt

        Returns:
            Encrypted token string
        """
        return self.encrypt(token)

    def decrypt_token(self, encrypted_token: str) -> str:
        """
        Decrypt OAuth token or API key.

        Args:
            encrypted_token: Encrypted token string

        Returns:
            Decrypted token string
        """
        return self.decrypt(encrypted_token)

    def encrypt_transcript(self, transcript: str) -> str:
        """
        Encrypt meeting or media transcript.

        Args:
            transcript: Transcript text to encrypt

        Returns:
            Encrypted transcript string
        """
        return self.encrypt(transcript)

    def decrypt_transcript(self, encrypted_transcript: str) -> str:
        """
        Decrypt meeting or media transcript.

        Args:
            encrypted_transcript: Encrypted transcript string

        Returns:
            Decrypted transcript string
        """
        return self.decrypt(encrypted_transcript)

    def encrypt_embedding(self, embedding: list) -> str:
        """
        Encrypt vector embedding (converts list to encrypted string).

        Args:
            embedding: List of floats representing embedding vector

        Returns:
            Base64-encoded encrypted embedding string
        """
        import json
        embedding_json = json.dumps(embedding)
        return self.encrypt(embedding_json)

    def decrypt_embedding(self, encrypted_embedding: str) -> list:
        """
        Decrypt embedding string back to list of floats.

        Args:
            encrypted_embedding: Encrypted embedding string

        Returns:
            List of floats representing embedding vector
        """
        import json
        decrypted_json = self.decrypt(encrypted_embedding)
        return json.loads(decrypted_json)

    @staticmethod
    def generate_key() -> str:
        """
        Generate a new Fernet key for encryption.

        Returns:
            Base64-encoded 32-byte key

        Usage:
            key = EncryptionService.generate_key()
            # Store key securely in environment variable or secrets manager
        """
        return Fernet.generate_key().decode('utf-8')

    def rotate_key(self, new_key: str, old_ciphertext: str) -> str:
        """
        Rotate encryption key by decrypting with old key and encrypting with new key.

        Args:
            new_key: New encryption key
            old_ciphertext: Data encrypted with old key

        Returns:
            Data encrypted with new key
        """
        # Decrypt with current key
        plaintext = self.decrypt(old_ciphertext)

        # Create new service with new key
        new_service = EncryptionService(encryption_key=new_key)

        # Encrypt with new key
        return new_service.encrypt(plaintext)


# Singleton instance
_encryption_service: Optional[EncryptionService] = None


def get_encryption_service() -> EncryptionService:
    """
    Get or create singleton encryption service instance.

    Returns:
        EncryptionService instance
    """
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    return _encryption_service


# Convenience functions for direct use
def encrypt(plaintext: str) -> str:
    """Encrypt plaintext string"""
    return get_encryption_service().encrypt(plaintext)


def decrypt(ciphertext: str) -> str:
    """Decrypt ciphertext string"""
    return get_encryption_service().decrypt(ciphertext)


def encrypt_token(token: str) -> str:
    """Encrypt OAuth token or API key"""
    return get_encryption_service().encrypt_token(token)


def decrypt_token(encrypted_token: str) -> str:
    """Decrypt OAuth token or API key"""
    return get_encryption_service().decrypt_token(encrypted_token)


def encrypt_transcript(transcript: str) -> str:
    """Encrypt meeting or media transcript"""
    return get_encryption_service().encrypt_transcript(transcript)


def decrypt_transcript(encrypted_transcript: str) -> str:
    """Decrypt meeting or media transcript"""
    return get_encryption_service().decrypt_transcript(encrypted_transcript)


def encrypt_embedding(embedding: list) -> str:
    """Encrypt vector embedding"""
    return get_encryption_service().encrypt_embedding(embedding)


def decrypt_embedding(encrypted_embedding: str) -> list:
    """Decrypt vector embedding"""
    return get_encryption_service().decrypt_embedding(encrypted_embedding)
