"""Client-side encryption using AES-256-GCM.

Key sourced from LUMERA_MEMORY_KEY environment variable.
"""

import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class EncryptionError(Exception):
    """Raised when encryption/decryption fails."""
    pass


def get_encryption_key() -> bytes:
    """Get encryption key from environment variable.

    Returns:
        32-byte encryption key

    Raises:
        EncryptionError: If LUMERA_MEMORY_KEY not set or invalid
    """
    key_hex = os.getenv("LUMERA_MEMORY_KEY")
    if not key_hex:
        raise EncryptionError(
            "LUMERA_MEMORY_KEY environment variable not set. "
            "Generate a key with: openssl rand -hex 32"
        )

    try:
        key = bytes.fromhex(key_hex)
    except ValueError:
        raise EncryptionError("LUMERA_MEMORY_KEY must be a hex-encoded 32-byte key")

    if len(key) != 32:
        raise EncryptionError(f"LUMERA_MEMORY_KEY must be 32 bytes (got {len(key)})")

    return key


def encrypt_blob(data: bytes, key: bytes = None) -> bytes:
    """Encrypt data using AES-256-GCM.

    Args:
        data: Plaintext bytes to encrypt
        key: 32-byte encryption key (uses env var if None)

    Returns:
        IV (12 bytes) + Ciphertext + Auth Tag (16 bytes)

    Raises:
        EncryptionError: If encryption fails
    """
    if key is None:
        key = get_encryption_key()

    try:
        aesgcm = AESGCM(key)
        nonce = os.urandom(12)  # 96-bit IV for GCM
        ciphertext = aesgcm.encrypt(nonce, data, None)
        return nonce + ciphertext  # nonce + ciphertext + tag
    except Exception as e:
        raise EncryptionError(f"Encryption failed: {e}")


def decrypt_blob(encrypted: bytes, key: bytes = None) -> bytes:
    """Decrypt AES-256-GCM encrypted data.

    Args:
        encrypted: IV + Ciphertext + Auth Tag
        key: 32-byte encryption key (uses env var if None)

    Returns:
        Plaintext bytes

    Raises:
        EncryptionError: If decryption fails (wrong key or tampered data)
    """
    if key is None:
        key = get_encryption_key()

    try:
        aesgcm = AESGCM(key)
        nonce = encrypted[:12]
        ciphertext = encrypted[12:]
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext
    except Exception as e:
        raise EncryptionError(f"Decryption failed (wrong key or tampered data): {e}")
