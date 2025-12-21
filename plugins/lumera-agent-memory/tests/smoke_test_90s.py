"""90-second smoke test for Lumera Agent Memory.

Tests complete end-to-end workflow:
1. Store session (redact + encrypt + index)
2. Query local index
3. Retrieve session (decrypt)
4. Estimate cost

Must complete in <90 seconds for CI gate.
"""

import os
import json
import pytest
from pathlib import Path

# Add src to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.security import redact_session, encrypt_blob, decrypt_blob
from src.cascade import MockCascadeConnector
from src.index import MemoryIndex
from src.adapters import CASSAdapter


@pytest.mark.timeout(90)
def test_full_workflow(tmp_path, monkeypatch):
    """End-to-end smoke test (<90 seconds)."""

    # Setup: Generate test key
    test_key = os.urandom(32)
    monkeypatch.setenv("LUMERA_MEMORY_KEY", test_key.hex())

    # Setup: Temporary storage
    cascade_dir = tmp_path / "cascade"
    index_path = tmp_path / "index.db"

    cascade = MockCascadeConnector(cache_dir=cascade_dir)
    index = MemoryIndex(db_path=index_path)
    cass = CASSAdapter()

    # STEP 1: Store session
    print("\n[STEP 1] Storing session...")

    session_id = "test-session-001"
    session_data = cass.export_session(session_id)
    assert session_data is not None, "Session export failed"

    # Redact
    redacted = redact_session(session_data)
    assert "session_id" in redacted
    assert redacted["session_id"] == session_id

    # Encrypt
    plaintext = json.dumps(redacted).encode("utf-8")
    encrypted_blob = encrypt_blob(plaintext, key=test_key)
    assert len(encrypted_blob) > len(plaintext), "Encryption failed"

    # Store in Cascade
    pointer = cascade.put(encrypted_blob)
    assert pointer.startswith("cascade://"), f"Invalid pointer: {pointer}"
    print(f"  ✓ Stored with pointer: {pointer}")

    # Index
    import hashlib
    content_hash = hashlib.sha256(encrypted_blob).hexdigest()
    memory_id = index.add_memory(
        pointer=pointer,
        content_hash=content_hash,
        tags=["smoke-test", "ci"],
        source_session_id=session_id,
        source_tool="baseline-forecaster",
    )
    assert memory_id > 0, "Index insertion failed"
    print(f"  ✓ Indexed with ID: {memory_id}")

    # STEP 2: Query index
    print("\n[STEP 2] Querying index...")

    memories = index.query_memories(tags=["smoke-test"], limit=10)
    assert len(memories) == 1, f"Expected 1 memory, got {len(memories)}"
    assert memories[0]["pointer"] == pointer
    assert "smoke-test" in memories[0]["tags"]
    print(f"  ✓ Found {len(memories)} memory")

    # STEP 3: Retrieve session
    print("\n[STEP 3] Retrieving session...")

    encrypted_blob_retrieved = cascade.get(pointer)
    assert encrypted_blob_retrieved == encrypted_blob, "Blob mismatch"

    decrypted_plaintext = decrypt_blob(encrypted_blob_retrieved, key=test_key)
    retrieved_session = json.loads(decrypted_plaintext.decode("utf-8"))

    assert retrieved_session["session_id"] == session_id
    assert retrieved_session["summary"] == redacted["summary"]
    print(f"  ✓ Retrieved and decrypted session: {session_id}")

    # STEP 4: Estimate cost
    print("\n[STEP 4] Estimating cost...")

    bytes_count = len(encrypted_blob)
    redundancy = 3
    kb = bytes_count / 1024
    monthly_cost = kb * 0.00003 * redundancy

    assert monthly_cost > 0, "Cost estimate failed"
    print(f"  ✓ Estimated cost: ${monthly_cost:.6f}/month for {bytes_count} bytes")

    # STEP 5: Data integrity check
    print("\n[STEP 5] Data integrity check...")

    assert retrieved_session == redacted, "Data integrity failed"
    print("  ✓ Retrieved data matches original")

    print("\n✅ SMOKE TEST PASSED (all steps successful)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--timeout=90"])
