"""Security layer: fail-closed redaction + AES-256-GCM encryption."""

from .redact import redact_session, RedactionError
from .encrypt import encrypt_blob, decrypt_blob, get_encryption_key, EncryptionError

__all__ = [
    "redact_session",
    "RedactionError",
    "encrypt_blob",
    "decrypt_blob",
    "get_encryption_key",
    "EncryptionError",
]
