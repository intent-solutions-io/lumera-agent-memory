"""Pytest configuration and fixtures."""

import os
import pytest
import tempfile
import shutil
from pathlib import Path


@pytest.fixture
def test_encryption_key():
    """Generate test encryption key."""
    return os.urandom(32)


@pytest.fixture
def mock_env_key(monkeypatch, test_encryption_key):
    """Set LUMERA_MEMORY_KEY environment variable for tests."""
    monkeypatch.setenv("LUMERA_MEMORY_KEY", test_encryption_key.hex())
    yield test_encryption_key


@pytest.fixture
def temp_cache_dir():
    """Create temporary cache directory for tests."""
    temp_dir = tempfile.mkdtemp(prefix="lumera_test_")
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def clean_cache():
    """Clean .cache directory before and after test."""
    cache_dir = Path(".cache")
    if cache_dir.exists():
        shutil.rmtree(cache_dir)
    yield
    if cache_dir.exists():
        shutil.rmtree(cache_dir)
