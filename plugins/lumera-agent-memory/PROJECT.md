# Lumera Agent Memory

A hybrid local-search + Cascade-storage memory system for coding agents. Integrates with Jeff Emanuel's CASS memory system to provide durable, encrypted, searchable session storage. The workflow: export session from CASS → redact secrets/PII with typed placeholders → encrypt client-side (AES-256-GCM) → store blob in Cascade → index pointer + metadata in local SQLite. Search queries NEVER hit Cascade—only the local FTS5 index returns pointers. Retrieval fetches encrypted blobs by URI, decrypts client-side, and returns the session payload. Includes deterministic NLP enrichment (Memory Card generation) for intelligent summaries without network calls.

---

## Quickstart (Offline Demo)

```bash
# 1. Install dependencies
cd plugins/lumera-agent-memory
./scripts/dev_setup.sh
source .venv/bin/activate

# 2. Set encryption key (required)
export LUMERA_MEMORY_KEY=$(openssl rand -hex 32)

# 3. Run tests
pytest tests/ -v

# 4. Run 90-second smoke test
./scripts/run_smoke.sh

# 5. Start MCP server (stdio mode)
python -m src.mcp_server
```

---

## Project Tree

```
plugins/lumera-agent-memory/
├── .claude-plugin/
│   └── plugin.json                 [CFG] (plugin manifest)
├── .mcp.json                       [CFG] (MCP server config)
├── pyproject.toml                  [CFG] (Python project metadata)
├── scripts/
│   ├── dev_setup.sh                [SCRIPT] (environment setup)
│   ├── requirements.txt            [CFG] (Python dependencies)
│   ├── run_smoke.sh                [SCRIPT] (smoke test runner)
│   └── validate_standards.py       [SCRIPT] (standards validator)
├── src/
│   ├── __init__.py
│   ├── mcp_server.py               [MCP] (stdio server, 4 tools)
│   ├── adapters/
│   │   ├── __init__.py
│   │   ├── cass_memory_system.py   [DATA] (CASS integration)
│   │   └── fixtures.py             [DATA] (test session fixtures)
│   ├── cascade/
│   │   ├── __init__.py
│   │   ├── interface.py            [MOCK] (Cascade connector interface)
│   │   └── mock_fs.py              [MOCK] (filesystem-backed storage)
│   ├── enrich/
│   │   ├── __init__.py
│   │   └── memory_card.py          [WOW] (NLP enrichment, deterministic)
│   ├── index/
│   │   ├── __init__.py
│   │   ├── index.py                [IDX] (SQLite + FTS5 search)
│   │   └── schema.sql              [IDX] (database schema v0.2.0)
│   └── security/
│       ├── __init__.py
│       ├── encrypt.py              [SEC] (AES-256-GCM encryption)
│       └── redact.py               [SEC] (typed redaction + reports)
└── tests/
    ├── conftest.py                 [TEST] (pytest fixtures)
    ├── smoke_test_90s.py           [TEST] (E2E smoke, <90s timeout)
    ├── test_cascade_mock.py        [TEST] (mock storage tests)
    ├── test_encryption.py          [TEST] (crypto roundtrip tests)
    ├── test_index.py               [TEST] (SQLite index tests)
    └── test_redaction.py           [TEST] (security tests)
```

---

## Key Entrypoints

- `src/mcp_server.py` — [MCP] Main stdio server; registers 4 tools and routes calls
- `src/security/redact.py` — [SEC] Typed redaction with rules report (critical vs non-critical)
- `src/security/encrypt.py` — [SEC] Client-side AES-256-GCM envelope encryption/decryption
- `src/cascade/mock_fs.py` — [MOCK] Filesystem-backed Cascade implementation (content-addressed)
- `src/cascade/interface.py` — [MOCK] Abstract connector interface (mock vs live)
- `src/index/index.py` — [IDX] SQLite index with FTS5 full-text search + BM25 ranking
- `src/index/schema.sql` — [IDX] Database schema with FTS5 virtual table + triggers
- `src/enrich/memory_card.py` — [WOW] Deterministic NLP heuristics for memory card generation
- `src/adapters/cass_memory_system.py` — [DATA] CASS integration adapter
- `src/adapters/fixtures.py` — [DATA] Test session fixtures with messy real-world data
- `tests/smoke_test_90s.py` — [TEST] End-to-end smoke test: store → query → retrieve
- `scripts/validate_standards.py` — [SCRIPT] Standards compliance validator

---

## Tool Surface (4 Tools)

### 1. store_session_to_cascade

**Input**: `session_id` (required), `tags` (optional array), `metadata` (optional object), `mode` (mock|live, default: mock)

**Returns**: `{ok, session_id, cascade_uri, indexed, memory_card, redaction, crypto}`

**Example**:
```json
{
  "tool": "store_session_to_cascade",
  "arguments": {
    "session_id": "demo-bug-report",
    "tags": ["demo", "production"],
    "mode": "mock"
  }
}
```

### 2. query_memories

**Input**: `query` (optional text), `tags` (optional array), `time_range` (optional {start, end}), `limit` (default: 10)

**Returns**: `{ok, hits: [{cass_session_id, cascade_uri, title, snippet, tags, created_at, score}]}`

**Example**:
```json
{
  "tool": "query_memories",
  "arguments": {
    "query": "JWT auth bug",
    "tags": ["production"],
    "limit": 5
  }
}
```

### 3. retrieve_session_from_cascade

**Input**: `cascade_uri` (required), `mode` (mock|live, default: mock)

**Returns**: `{ok, cascade_uri, session, memory_card, crypto}`

**Example**:
```json
{
  "tool": "retrieve_session_from_cascade",
  "arguments": {
    "cascade_uri": "cascade://abc123...",
    "mode": "mock"
  }
}
```

### 4. estimate_storage_cost

**Input**: `bytes` (required), `redundancy` (optional, default: 3), `pricing_inputs` (optional object)

**Returns**: `{ok, bytes, gb, monthly_storage_usd, estimated_request_usd, total_estimated_usd, assumptions}`

**Example**:
```json
{
  "tool": "estimate_storage_cost",
  "arguments": {
    "bytes": 1048576,
    "redundancy": 3
  }
}
```

---

## Notes: Mock vs Live

- [STAR] **Mock mode works offline**: Cascade storage is filesystem-backed at `.cache/cascade-mock/`
- [STAR] **Search never queries Cascade**: Only local SQLite FTS5 index (fast, offline)
- [STAR] **Content-addressed storage**: Pointers are `cascade://<sha256-hash>` (deterministic)
- [STAR] **Live mode not implemented**: Returns actionable error message listing missing env vars (CASCADE_API_ENDPOINT, CASCADE_API_KEY)
- [STAR] **Security model**: CRITICAL secrets (private keys, auth headers) fail-closed; non-critical PII (emails, API keys) redacted with typed placeholders
- [STAR] **Memory Card generation**: Deterministic NLP heuristics extract title, summary, decisions, todos, entities, keywords, quotes (no network, no ML)
- [STAR] **Encryption**: Client-side AES-256-GCM with user-controlled keys (LUMERA_MEMORY_KEY env var)
- [STAR] **Index schema v0.2.0**: Includes FTS5 virtual table for BM25-ranked full-text search
