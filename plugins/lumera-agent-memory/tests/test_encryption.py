"""Security tests for AES-256-GCM encryption."""

import os
import pytest
from src.security import encrypt_blob, decrypt_blob, get_encryption_key, EncryptionError


def test_encrypt_decrypt_roundtrip(mock_env_key):
    """Encrypt then decrypt should return original data."""
    plaintext = b"test data for encryption"

    encrypted = encrypt_blob(plaintext)
    decrypted = decrypt_blob(encrypted)

    assert decrypted == plaintext


def test_encryption_produces_different_ciphertext(mock_env_key):
    """Same plaintext should produce different ciphertext (random IV)."""
    plaintext = b"test data"

    ciphertext1 = encrypt_blob(plaintext)
    ciphertext2 = encrypt_blob(plaintext)

    assert ciphertext1 != ciphertext2, "IV should randomize ciphertext"


def test_decryption_fails_with_wrong_key():
    """Decryption with wrong key should raise EncryptionError."""
    key1 = os.urandom(32)
    key2 = os.urandom(32)

    plaintext = b"test data"
    encrypted = encrypt_blob(plaintext, key=key1)

    with pytest.raises(EncryptionError, match="Decryption failed"):
        decrypt_blob(encrypted, key=key2)


def test_decryption_fails_with_tampered_data(mock_env_key):
    """Tampered ciphertext should fail authentication."""
    plaintext = b"test data"
    encrypted = encrypt_blob(plaintext)

    # Tamper with ciphertext
    tampered = bytearray(encrypted)
    tampered[20] ^= 0xFF  # Flip bits in ciphertext
    tampered = bytes(tampered)

    with pytest.raises(EncryptionError, match="Decryption failed"):
        decrypt_blob(tampered)


def test_get_encryption_key_from_env(monkeypatch):
    """get_encryption_key should read from LUMERA_MEMORY_KEY."""
    test_key = os.urandom(32)
    monkeypatch.setenv("LUMERA_MEMORY_KEY", test_key.hex())

    key = get_encryption_key()
    assert key == test_key


def test_get_encryption_key_fails_if_not_set(monkeypatch):
    """Missing LUMERA_MEMORY_KEY should raise EncryptionError."""
    monkeypatch.delenv("LUMERA_MEMORY_KEY", raising=False)

    with pytest.raises(EncryptionError, match="LUMERA_MEMORY_KEY environment variable not set"):
        get_encryption_key()


def test_get_encryption_key_validates_length(monkeypatch):
    """Invalid key length should raise EncryptionError."""
    invalid_key = os.urandom(16)  # Only 128-bit, need 256-bit
    monkeypatch.setenv("LUMERA_MEMORY_KEY", invalid_key.hex())

    with pytest.raises(EncryptionError, match="must be 32 bytes"):
        get_encryption_key()
