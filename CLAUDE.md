# CLAUDE.md - Operator Instructions for Lumera Agent Memory

**Project**: Lumera Agent Memory (Week 1 Scaffold)
**Version**: 0.1.0
**Last Updated**: 2025-12-20

---

## Project Overview

This is a **hybrid memory system** for coding agents that integrates Jeff Emanuel's CASS memory system with Lumera Cascade storage. It provides:

- Fast local search via SQLite index
- Durable encrypted storage in Cascade
- Fail-closed security (aborts on ANY secret detection)

**CRITICAL**: This is Week 1 scaffold code. Cascade is MOCKED (filesystem-backed). Real integration comes in Week 2+.

---

## Task Tracking (Beads)

- Use `bd` for ALL tasks/issues (no markdown TODO lists)
- Start of session: `bd ready`
- Create work: `bd create "Title" -p 1 --description "Context + acceptance"`
- Update status: `bd update <id> --status in_progress`
- Finish: `bd close <id> --reason "Done"`
- End of session: `bd sync`

**IMPORTANT**: `.beads/` is in `.gitignore`. Beads is dev-only, NEVER commit.

---

## Directory Structure

```
000-projects/Lumera-Emanuel/
├── 000-docs/                    # All documentation (Doc-Filing v3.0 pattern)
│   ├── planned-plugins/lumera-agent-memory/
│   │   ├── 01-BUSINESS-CASE.md
│   │   ├── 02-PRD.md
│   │   ├── 03-ARCHITECTURE.md
│   │   ├── 04-THREAT-MODEL.md
│   │   ├── 05-TEST-PLAN.md
│   │   └── 06-STATUS.md
│   └── AA-REPT/                 # After-Action Reports
│       └── 001-AA-REPT-week-1-scaffold.md
├── plugins/lumera-agent-memory/ # Plugin implementation
│   ├── .claude-plugin/          # Plugin metadata
│   │   ├── plugin.json
│   │   └── .mcp.json
│   ├── src/                     # Source code
│   │   ├── security/            # Redaction + encryption
│   │   ├── cascade/             # Cascade connector (mock)
│   │   ├── index/               # SQLite index
│   │   ├── adapters/            # CASS integration
│   │   └── mcp_server.py        # MCP server (4 tools)
│   ├── tests/                   # Test suite
│   │   ├── smoke_test_90s.py    # 90-second CI gate
│   │   ├── test_redaction.py    # Security tests
│   │   ├── test_encryption.py
│   │   ├── test_cascade_mock.py
│   │   └── test_index.py
│   └── scripts/                 # Dev automation
│       ├── dev_setup.sh
│       └── run_smoke.sh
├── .github/workflows/           # CI/CD
│   ├── pr.yml                   # PR validation
│   └── main.yml                 # Main branch checks
├── .gitignore                   # Beads + secrets excluded
└── README.md
```

---

## Development Workflow

### Setup

```bash
cd plugins/lumera-agent-memory
./scripts/dev_setup.sh
source .venv/bin/activate

# Set encryption key (REQUIRED for tests)
export LUMERA_MEMORY_KEY=$(openssl rand -hex 32)
```

### Run Tests

```bash
# All tests
pytest tests/ -v

# Security tests only (CRITICAL)
pytest tests/test_redaction.py tests/test_encryption.py -v

# 90-second smoke test
./scripts/run_smoke.sh
```

### Code Changes

1. **Read existing code** before modifying
2. **Follow existing patterns** (fail-closed security, content-addressed storage)
3. **Write tests FIRST** (TDD for security-critical code)
4. **Run smoke test** before committing

---

## Security Rules (NON-NEGOTIABLE)

### Fail-Closed Redaction

**Design**: If ANY secret detected → abort storage, return error.

**NO warnings, NO guessing, NO partial redaction.**

**Detected Secrets**:
- API keys (32+ char alphanumeric)
- AWS keys (`AKIA...`)
- SSH keys (`-----BEGIN RSA PRIVATE KEY-----`)
- Emails (PII)
- Credit cards

**Test**:
```bash
pytest tests/test_redaction.py -v
```

**ALL tests MUST pass**. If a redaction test fails, the system is BROKEN.

### Encryption

**Key Source**: `LUMERA_MEMORY_KEY` environment variable
**Algorithm**: AES-256-GCM
**Key Length**: 32 bytes (256 bits)

**NEVER**:
- Log keys
- Commit keys
- Store keys in code
- Use hardcoded keys

**Test**:
```bash
pytest tests/test_encryption.py -v
```

---

## Architecture Principles

### 1. Local Index for Speed, Cascade for Durability

**Query Flow**:
```
User → query_cascade_memories → SQLite Index → Return POINTERS
```

**NEVER query Cascade for search**. Index returns pointers, user calls `retrieve_session_from_cascade` to fetch.

### 2. Content-Addressed Storage

**Pointer Format**: `cascade://<sha256-hash>`

**Deterministic**: Same blob → same pointer (deduplication)

**Immutability**: Pointers never change (blobs are immutable)

### 3. Fail-Closed Security

**Redaction**: Detect secrets → abort (no storage)
**Encryption**: Missing key → error (no fallback)
**Path Traversal**: Invalid pointer → error (no guessing)

---

## Testing Standards

### 90-Second Smoke Test (CI Gate)

**File**: `tests/smoke_test_90s.py`

**Workflow**:
1. Store session (redact + encrypt + index)
2. Query index (find pointer)
3. Retrieve session (decrypt + verify)
4. Estimate cost

**Timeout**: 90 seconds (enforced via `pytest.mark.timeout(90)`)

**Run**:
```bash
./scripts/run_smoke.sh
```

**CI Requirement**: MUST pass on every PR.

### Security Tests

**Redaction** (`tests/test_redaction.py`):
- Proves fail-closed on API keys, AWS keys, SSH keys, emails, credit cards
- ALL tests MUST pass

**Encryption** (`tests/test_encryption.py`):
- Roundtrip encrypt/decrypt
- Fails with wrong key
- Fails with tampered data

**CI Requirement**: Zero failures allowed.

---

## Common Tasks

### Add New Secret Pattern

1. Edit `src/security/redact.py`
2. Add regex to `PATTERNS` dict:
   ```python
   "new_secret": re.compile(r"your-pattern-here"),
   ```
3. Add test to `tests/test_redaction.py`:
   ```python
   def test_redaction_fails_on_new_secret():
       session = {"session_id": "test", "summary": "SECRET_VALUE"}
       with pytest.raises(RedactionError):
           redact_session(session)
   ```
4. Run: `pytest tests/test_redaction.py -v`

### Add MCP Tool

1. Edit `src/mcp_server.py`
2. Add tool definition to `list_tools()`
3. Add handler function (follow existing pattern)
4. Add tests to `tests/test_mcp_tools.py` (future)
5. Update docs: `000-docs/planned-plugins/lumera-agent-memory/02-PRD.md`

### Swap Mock → Live Cascade

**Week 2 Task**:
1. Create `src/cascade/live_cascade.py` implementing `CascadeConnector` interface
2. Update `src/mcp_server.py`:
   ```python
   # from .cascade import MockCascadeConnector
   from .cascade import LiveCascadeConnector
   cascade = LiveCascadeConnector(api_key=os.getenv("CASCADE_API_KEY"))
   ```
3. Update tests (add live integration tests, keep mock for unit tests)

---

## CI/CD

### PR Workflow (`.github/workflows/pr.yml`)

**Runs on**: Every pull request

**Steps**:
1. Security tests (redaction + encryption)
2. Component tests (cascade + index)
3. 90-second smoke test (timeout enforced)
4. Lint checks (black, isort, flake8)

**Failure = PR blocked**

### Main Branch Workflow (`.github/workflows/main.yml`)

**Runs on**: Every push to main

**Steps**:
- All PR checks
- Coverage reports
- Artifact uploads

---

## Troubleshooting

### `EncryptionError: LUMERA_MEMORY_KEY environment variable not set`

**Fix**:
```bash
export LUMERA_MEMORY_KEY=$(openssl rand -hex 32)
```

**Persist** (optional, DO NOT COMMIT):
```bash
echo "LUMERA_MEMORY_KEY=$(openssl rand -hex 32)" > .env
source .env
```

### Smoke test timeout (>90 seconds)

**Causes**:
- Slow disk I/O
- Debug logging enabled
- Network calls (should be offline)

**Fix**:
1. Check: `rm -rf .cache` (clean cache)
2. Profile: `pytest tests/smoke_test_90s.py -v -s --durations=10`
3. Optimize slowest operations

### Redaction test fails

**CRITICAL**: This means secrets are NOT being detected.

**Fix**:
1. Review regex pattern in `src/security/redact.py`
2. Add test case for the failing secret
3. Verify `detect_secrets()` recursion covers all data types

---

## Git Workflow

### Commit Messages

**Pattern**: `<type>(<scope>): <message>`

**Examples**:
```
feat(security): add GitHub token redaction pattern
fix(cascade): prevent path traversal in pointer validation
test(smoke): optimize query to reduce runtime
docs(prd): clarify immutability constraints
```

### Atomic Commits

**DO**:
- One logical change per commit
- Tests pass after each commit
- Clear, descriptive messages

**DON'T**:
- Combine unrelated changes
- Commit broken code
- Use vague messages like "fix stuff"

---

## Upstream References

### CASS Memory System
- **Repo**: https://github.com/Dicklesworthstone/cass_memory_system
- **CLI**: `cm context <session-id> --json`
- **Integration**: `src/adapters/cass_memory_system.py`

### Beads
- **Repo**: https://github.com/steveyegge/beads
- **Installed**: `bd --version` (0.30.6+)
- **Usage**: `.beads/` (gitignored, dev-only)

### Nixtla Plugin Template
- **Location**: `/home/jeremy/000-projects/nixtla/005-plugins/nixtla-baseline-lab/`
- **Pattern**: Used as scaffold template

---

## Week 1 Deliverables (COMPLETE)

✅ Documentation (6 planning docs)
✅ Security layer (redaction + encryption)
✅ Storage layer (mock Cascade + SQLite index)
✅ CASS adapter (with fixtures)
✅ MCP server (4 tools)
✅ Tests (35+ tests, <90s smoke test)
✅ CI/CD (PR + main workflows)
✅ README + CLAUDE.md
✅ AA-REPT (week 1 scaffold report)

**Next**: Week 2 - Live Cascade integration

---

## Questions?

Contact: Jeremy Longshore (jeremy@intentsolutions.io)
