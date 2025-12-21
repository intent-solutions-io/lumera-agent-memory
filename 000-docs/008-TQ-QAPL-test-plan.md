# Test Plan: Lumera Agent Memory

**Version**: 0.1.0
**Last Updated**: 2025-12-20

---

## Test Strategy

### Pyramid Structure

```
         /\
        /  \  E2E (Smoke Test)
       /────\
      / Unit \  Component Tests
     /────────\
    / Security \ Fail-Closed Tests
   /────────────\
```

**Priorities**:
1. Security tests (fail-closed redaction, encryption)
2. Component tests (adapters, index, cascade)
3. Integration tests (MCP tools)
4. E2E smoke test (90-second CI gate)

---

## Test Levels

### L1: Security Tests (CRITICAL)

**Purpose**: Prove fail-closed behavior and encryption integrity.

#### Test Suite: Redaction

| Test | Input | Expected Output |
|------|-------|-----------------|
| `test_redaction_passes_safe_data()` | Session with only allowlisted fields | Redacted dict (no error) |
| `test_redaction_fails_on_api_key()` | Session with `API_KEY=abc123...` | `RedactionError` raised |
| `test_redaction_fails_on_aws_key()` | Session with `AKIAIOSFODNN7EXAMPLE` | `RedactionError` raised |
| `test_redaction_fails_on_ssh_key()` | Session with `-----BEGIN RSA PRIVATE KEY-----` | `RedactionError` raised |
| `test_redaction_fails_on_email()` | Session with `user@example.com` | `RedactionError` (PII) |
| `test_redaction_fails_on_credit_card()` | Session with `4111-1111-1111-1111` | `RedactionError` raised |

**Assertion Style**: Ensure `pytest.raises(RedactionError)`

#### Test Suite: Encryption

| Test | Input | Expected Output |
|------|-------|-----------------|
| `test_encrypt_decrypt_roundtrip()` | `b"test data"` | Decrypted matches original |
| `test_encryption_produces_different_ciphertext()` | Same plaintext, different IV | Ciphertexts differ |
| `test_decryption_fails_with_wrong_key()` | Decrypt with different key | `DecryptionError` raised |
| `test_decryption_fails_with_tampered_data()` | Modify ciphertext byte | `DecryptionError` (auth tag fail) |

### L2: Component Tests

#### CASS Adapter (`test_cass_adapter.py`)

| Test | Mocked | Expected Behavior |
|------|--------|-------------------|
| `test_cm_available_detection()` | `shutil.which("cm")` | Returns `True` if found |
| `test_export_session_with_cm()` | `subprocess.run()` | Parses JSON output |
| `test_export_session_fallback_fixture()` | No `cm` binary | Returns fixture data |

#### Cascade Connector (`test_cascade_mock.py`)

| Test | Input | Expected Output |
|------|-------|-----------------|
| `test_put_returns_content_hash()` | `b"test"` | `cascade://9f86d08...` |
| `test_get_retrieves_blob()` | Valid pointer | Original bytes |
| `test_get_fails_on_invalid_pointer()` | `cascade://invalid` | `NotFoundError` |
| `test_pointer_validation_rejects_traversal()` | `cascade://../etc/passwd` | `ValidationError` |

#### Local Index (`test_index.py`)

| Test | Input | Expected Output |
|------|-------|-----------------|
| `test_add_memory_inserts_row()` | Pointer + metadata | Row in `memories` table |
| `test_query_by_tags_exact_match()` | Tags: `["agent", "success"]` | Matching memories |
| `test_query_by_tags_substring()` | Tags: `["agent"]` | Memories with "agent" tag |
| `test_query_returns_pointers_only()` | Any query | No blob content in results |
| `test_query_limit_enforced()` | Limit: 5 | Max 5 results |

### L3: Integration Tests (MCP Tools)

#### Tool: `store_session_to_cascade`

| Test | Input | Expected Output |
|------|-------|-----------------|
| `test_store_session_success()` | Valid session | `{pointer, content_hash, indexed: true}` |
| `test_store_session_fails_on_secrets()` | Session with API key | Error response |

#### Tool: `query_cascade_memories`

| Test | Input | Expected Output |
|------|-------|-----------------|
| `test_query_returns_pointers()` | Tags: `["test"]` | List of pointer dicts |
| `test_query_empty_results()` | Tags: `["nonexistent"]` | Empty list |

#### Tool: `retrieve_session_from_cascade`

| Test | Input | Expected Output |
|------|-------|-----------------|
| `test_retrieve_decrypts_blob()` | Valid pointer | Decrypted session data |
| `test_retrieve_fails_on_bad_pointer()` | Invalid pointer | Error response |

#### Tool: `estimate_storage_cost`

| Test | Input | Expected Output |
|------|-------|-----------------|
| `test_estimate_returns_plausible_cost()` | bytes: 1024 | `{cost: 0.00003, disclaimer: "..."}` |

### L4: End-to-End Smoke Test (CI Gate)

**File**: `tests/smoke_test_90s.py`

**Timeout**: 90 seconds (enforced with `pytest.mark.timeout(90)`)

**Test Flow**:
```python
def test_full_workflow():
    # Setup
    setup_test_env()  # Create temp dirs, mock key

    # Step 1: Store session
    result = store_session_to_cascade(
        session_id="test-session-001",
        tags=["smoke-test", "ci"]
    )
    assert result["indexed"] is True
    pointer = result["pointer"]

    # Step 2: Query index
    memories = query_cascade_memories(tags=["smoke-test"], limit=10)
    assert len(memories) == 1
    assert memories[0]["pointer"] == pointer

    # Step 3: Retrieve session
    session_data = retrieve_session_from_cascade(pointer)
    assert session_data["session_id"] == "test-session-001"

    # Step 4: Estimate cost
    cost = estimate_storage_cost(bytes=len(session_data))
    assert cost["estimated_cost"] > 0

    # Cleanup
    teardown_test_env()
```

**Assertions**:
- All operations succeed
- Data integrity (retrieved matches stored)
- No network calls (offline mode)

---

## Test Fixtures

### Fixture: CASS Session Export

**File**: `src/adapters/fixtures.py`

```python
FIXTURE_SESSION_001 = {
    "session_id": "test-session-001",
    "timestamp": "2025-12-20T10:00:00Z",
    "tool_name": "baseline-forecaster",
    "success": True,
    "summary": "Ran M4 baseline forecast",
    "tags": ["baseline", "m4", "statsforecast"]
}
```

### Fixture: Encryption Key

**File**: `tests/conftest.py`

```python
@pytest.fixture
def test_encryption_key():
    return os.urandom(32)  # 256-bit key

@pytest.fixture
def mock_env_key(monkeypatch, test_encryption_key):
    monkeypatch.setenv("LUMERA_MEMORY_KEY", test_encryption_key.hex())
    yield test_encryption_key
```

---

## CI/CD Integration

### PR Workflow (`.github/workflows/pr.yml`)

```yaml
name: PR Validation

on: [pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python 3.10
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          cd plugins/lumera-agent-memory
          pip install -r scripts/requirements.txt
          pip install pytest pytest-timeout

      - name: Run security tests
        run: pytest tests/test_redaction.py -v

      - name: Run component tests
        run: pytest tests/ -v --ignore=tests/smoke_test_90s.py

      - name: Run 90-second smoke test
        run: pytest tests/smoke_test_90s.py -v --timeout=90
```

**Fail Conditions**:
- Any test failure
- Smoke test exceeds 90 seconds
- Code coverage <80% (future)

### Main Branch Workflow (`.github/workflows/main.yml`)

- Same tests as PR
- Additional: lint checks (black, isort, flake8)
- Artifact upload: coverage reports

---

## Manual Testing (Local)

### Setup

```bash
cd /home/jeremy/000-projects/Lumera-Emanuel/plugins/lumera-agent-memory

# Create venv
python3.10 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r scripts/requirements.txt

# Set encryption key
export LUMERA_MEMORY_KEY=$(openssl rand -hex 32)
```

### Run Tests

```bash
# All tests
pytest tests/ -v

# Security tests only
pytest tests/test_redaction.py tests/test_encryption.py -v

# Smoke test
pytest tests/smoke_test_90s.py -v --timeout=90

# With coverage
pytest --cov=src --cov-report=html tests/
```

---

## Success Criteria

| Category | Criterion | Status |
|----------|-----------|--------|
| **Security** | All redaction tests pass (fail-closed proven) | ✅ Required |
| **Security** | All encryption tests pass | ✅ Required |
| **Component** | CASS adapter works with/without `cm` | ✅ Required |
| **Component** | Cascade mock stores/retrieves correctly | ✅ Required |
| **Component** | Index queries return pointers only | ✅ Required |
| **Integration** | All 4 MCP tools execute successfully | ✅ Required |
| **E2E** | Smoke test completes in <90s | ✅ Required (CI gate) |

---

## Test Metrics (Week 1 Target)

- **Coverage**: >80% (excluding fixtures)
- **Security Tests**: 10+ (redaction + encryption)
- **Component Tests**: 15+ (adapters + storage)
- **Integration Tests**: 8+ (4 tools × 2 scenarios)
- **E2E Tests**: 1 (smoke test)

**Total**: ~35 tests minimum

---

**Execution**: Tests run on every commit via GitHub Actions
