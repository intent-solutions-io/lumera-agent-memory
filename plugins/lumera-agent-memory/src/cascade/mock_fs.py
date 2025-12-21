"""Filesystem-backed mock Cascade connector (Week 1).

Mimics Cascade put/get semantics using local .cache directory.
Content-addressed storage with SHA-256 hashing.
"""

import hashlib
import re
from pathlib import Path
from .interface import CascadeConnector, NotFoundError, ValidationError


POINTER_PATTERN = re.compile(r"^cascade://([a-f0-9]{64})$")


class MockCascadeConnector(CascadeConnector):
    """Mock Cascade connector using filesystem storage."""

    def __init__(self, cache_dir: Path = None):
        """Initialize mock connector.

        Args:
            cache_dir: Directory for blob storage (default: .cache/cascade-mock)
        """
        if cache_dir is None:
            cache_dir = Path(".cache/cascade-mock")
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def put(self, data: bytes) -> str:
        """Store blob with content-addressed pointer.

        Args:
            data: Encrypted blob bytes

        Returns:
            cascade://<sha256-hash>
        """
        # Content-addressed: hash determines location
        content_hash = hashlib.sha256(data).hexdigest()

        # Store in 2-level directory structure (first 2 hex chars)
        blob_dir = self.cache_dir / content_hash[:2]
        blob_dir.mkdir(parents=True, exist_ok=True)

        blob_path = blob_dir / content_hash
        blob_path.write_bytes(data)

        return f"cascade://{content_hash}"

    def get(self, pointer: str) -> bytes:
        """Retrieve blob by pointer.

        Args:
            pointer: cascade://<hash>

        Returns:
            Encrypted blob bytes

        Raises:
            ValidationError: If pointer format invalid
            NotFoundError: If blob not found
        """
        # Validate pointer format
        match = POINTER_PATTERN.match(pointer)
        if not match:
            raise ValidationError(f"Invalid pointer format: {pointer}")

        content_hash = match.group(1)

        # Prevent path traversal
        if ".." in content_hash or "/" in content_hash or "\\" in content_hash:
            raise ValidationError(f"Pointer contains unsafe characters: {pointer}")

        # Resolve blob path
        blob_path = self.cache_dir / content_hash[:2] / content_hash

        # Verify path is within cache_dir (canonical path check)
        try:
            blob_path_resolved = blob_path.resolve()
            cache_dir_resolved = self.cache_dir.resolve()
            if not str(blob_path_resolved).startswith(str(cache_dir_resolved)):
                raise ValidationError(f"Pointer escapes cache directory: {pointer}")
        except Exception as e:
            raise ValidationError(f"Path resolution failed: {e}")

        # Retrieve blob
        if not blob_path.exists():
            raise NotFoundError(f"Blob not found: {pointer}")

        return blob_path.read_bytes()
