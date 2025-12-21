"""Tests for mock Cascade connector."""

import pytest
from pathlib import Path
from src.cascade import MockCascadeConnector, NotFoundError, ValidationError


def test_put_returns_content_hash(temp_cache_dir):
    """put() should return content-addressed pointer."""
    cascade = MockCascadeConnector(cache_dir=temp_cache_dir)

    data = b"test data"
    pointer = cascade.put(data)

    assert pointer.startswith("cascade://")
    assert len(pointer) == len("cascade://") + 64  # SHA-256 hex


def test_get_retrieves_blob(temp_cache_dir):
    """get() should retrieve original blob."""
    cascade = MockCascadeConnector(cache_dir=temp_cache_dir)

    data = b"test data"
    pointer = cascade.put(data)
    retrieved = cascade.get(pointer)

    assert retrieved == data


def test_get_fails_on_invalid_pointer(temp_cache_dir):
    """Invalid pointer format should raise ValidationError."""
    cascade = MockCascadeConnector(cache_dir=temp_cache_dir)

    with pytest.raises(ValidationError, match="Invalid pointer format"):
        cascade.get("invalid-pointer")


def test_pointer_validation_rejects_traversal(temp_cache_dir):
    """Path traversal attempts should raise ValidationError."""
    cascade = MockCascadeConnector(cache_dir=temp_cache_dir)

    malicious_pointers = [
        "cascade://../../../etc/passwd",
        "cascade://../etc/passwd",
        "cascade://../../sensitive",
    ]

    for pointer in malicious_pointers:
        with pytest.raises(ValidationError, match="unsafe characters|Invalid pointer"):
            cascade.get(pointer)


def test_get_fails_on_nonexistent_blob(temp_cache_dir):
    """get() for non-existent blob should raise NotFoundError."""
    cascade = MockCascadeConnector(cache_dir=temp_cache_dir)

    # Valid pointer format but doesn't exist
    fake_pointer = "cascade://" + "a" * 64

    with pytest.raises(NotFoundError, match="Blob not found"):
        cascade.get(fake_pointer)


def test_content_addressing_deterministic(temp_cache_dir):
    """Same data should produce same pointer."""
    cascade = MockCascadeConnector(cache_dir=temp_cache_dir)

    data = b"deterministic data"
    pointer1 = cascade.put(data)
    pointer2 = cascade.put(data)

    assert pointer1 == pointer2
