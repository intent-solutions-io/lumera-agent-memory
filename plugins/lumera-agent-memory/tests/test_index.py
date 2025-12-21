"""Tests for local SQLite index."""

import pytest
from pathlib import Path
from src.index import MemoryIndex


def test_add_memory_inserts_row(temp_cache_dir):
    """add_memory() should insert row in database."""
    index = MemoryIndex(db_path=temp_cache_dir / "test.db")

    memory_id = index.add_memory(
        pointer="cascade://abc123",
        content_hash="def456",
        tags=["test", "ci"],
        source_session_id="test-001",
        source_tool="forecaster",
    )

    assert memory_id > 0


def test_query_by_tags_exact_match(temp_cache_dir):
    """Query should match tags exactly."""
    index = MemoryIndex(db_path=temp_cache_dir / "test.db")

    index.add_memory("cascade://ptr1", "hash1", tags=["agent", "success"])
    index.add_memory("cascade://ptr2", "hash2", tags=["agent", "failure"])

    results = index.query_memories(tags=["agent", "success"])
    assert len(results) >= 1
    assert any("success" in r["tags"] for r in results)


def test_query_by_tags_substring(temp_cache_dir):
    """Query should support substring matching."""
    index = MemoryIndex(db_path=temp_cache_dir / "test.db")

    index.add_memory("cascade://ptr1", "hash1", tags=["baseline-forecaster"])
    index.add_memory("cascade://ptr2", "hash2", tags=["timegpt-forecaster"])

    results = index.query_memories(tags=["forecaster"])
    assert len(results) >= 2


def test_query_returns_pointers_only(temp_cache_dir):
    """Query should return pointers, not blob content."""
    index = MemoryIndex(db_path=temp_cache_dir / "test.db")

    pointer = "cascade://test123"
    index.add_memory(pointer, "hash1", tags=["test"])

    results = index.query_memories(tags=["test"])
    assert len(results) == 1
    assert "pointer" in results[0]
    assert results[0]["pointer"] == pointer
    assert "content" not in results[0]  # No blob content


def test_query_limit_enforced(temp_cache_dir):
    """Query limit should cap results."""
    index = MemoryIndex(db_path=temp_cache_dir / "test.db")

    for i in range(20):
        index.add_memory(f"cascade://ptr{i}", f"hash{i}", tags=["bulk"])

    results = index.query_memories(tags=["bulk"], limit=5)
    assert len(results) == 5


def test_get_memory_by_pointer(temp_cache_dir):
    """get_memory_by_pointer() should retrieve metadata."""
    index = MemoryIndex(db_path=temp_cache_dir / "test.db")

    pointer = "cascade://specific"
    index.add_memory(pointer, "hash1", tags=["unique"])

    memory = index.get_memory_by_pointer(pointer)
    assert memory is not None
    assert memory["pointer"] == pointer


def test_delete_memory(temp_cache_dir):
    """delete_memory() should remove from index."""
    index = MemoryIndex(db_path=temp_cache_dir / "test.db")

    pointer = "cascade://deleteme"
    index.add_memory(pointer, "hash1", tags=["temp"])

    deleted = index.delete_memory(pointer)
    assert deleted is True

    memory = index.get_memory_by_pointer(pointer)
    assert memory is None
