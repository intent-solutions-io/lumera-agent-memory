# Product Requirements Document: Lumera Agent Memory

**Version**: 0.1.0 (Week 1 Scaffold)
**Status**: Planning
**Owner**: Jeremy Longshore

---

## Product Vision

Enable coding agents to accumulate procedural memory across sessions through a hybrid local-search + remote-storage architecture, integrated with Jeff Emanuel's CASS memory system.

---

## Core Features (Week 1)

### F1: CASS Memory Integration

**Requirement**: Adapter layer that calls `cm` CLI when available, falls back to fixtures in CI.

**Acceptance Criteria**:
- Detects `cm` binary availability at runtime
- Parses `cm context --json` output for rules/history
- Uses test fixtures when `cm` not installed
- CI passes without requiring `cm` installation

### F2: Mock Cascade Connector

**Requirement**: Filesystem-backed blob storage that mimics Cascade put/get semantics.

**Acceptance Criteria**:
- `put(bytes) -> pointer`: Content-addressed storage (SHA-256 hash)
- `get(pointer) -> bytes`: Retrieval by pointer
- Deterministic paths under `.cache/cascade-mock/` (gitignored)
- Compatible with real Cascade API signature (future swap)

### F3: Local SQLite Index

**Requirement**: Fast search layer returning pointers + metadata (never queries Cascade).

**Schema**:
```sql
CREATE TABLE memories (
    id INTEGER PRIMARY KEY,
    pointer TEXT UNIQUE NOT NULL,
    content_hash TEXT NOT NULL,
    tags_json TEXT,
    created_at TEXT NOT NULL,
    schema_version TEXT DEFAULT '0.1.0',
    source_session_id TEXT,
    source_tool TEXT
);
CREATE INDEX idx_tags ON memories(tags_json);
CREATE INDEX idx_created ON memories(created_at);
```

**Acceptance Criteria**:
- Query by tags (exact match + substring)
- Query by creation date range
- Return pointers only (no blob content)
- <100ms query latency

### F4: Fail-Closed Redaction

**Requirement**: Security layer that aborts storage if secrets/PII detected.

**Acceptance Criteria**:
- Detects: API keys, AWS credentials, SSH keys, emails, credit cards
- Test proves "fails closed" (aborts on suspicious content)
- Allowlist approach: only persist known-safe fields
- Clear error messages guide users to fix source data

### F5: Client-Side Encryption

**Requirement**: Symmetric encryption using `LUMERA_MEMORY_KEY` env var.

**Acceptance Criteria**:
- AES-256-GCM encryption (cryptography library)
- Key sourced from `LUMERA_MEMORY_KEY` (never committed)
- Encrypted blobs include IV + auth tag
- Decrypt on retrieval before returning to MCP client
- Documented key setup in CLAUDE.md

### F6: MCP Server with 4 Tools

**Tool 1**: `store_session_to_cascade`
- **Input**: `session_id: str`, `tags?: list[str]`
- **Output**: `{pointer: str, content_hash: str, indexed: bool}`
- **Behavior**: Redact → Encrypt → Store in Cascade → Index locally

**Tool 2**: `query_cascade_memories`
- **Input**: `query: str`, `tags?: list[str]`, `limit?: int`
- **Output**: `[{pointer: str, tags: list[str], created_at: str}]`
- **Behavior**: Query local index ONLY (never Cascade)

**Tool 3**: `retrieve_session_from_cascade`
- **Input**: `pointer: str`
- **Output**: `{session_data: dict}`
- **Behavior**: Fetch from Cascade → Decrypt → Return

**Tool 4**: `estimate_storage_cost`
- **Input**: `bytes: int`, `redundancy?: int = 3`
- **Output**: `{estimated_cost: float, disclaimer: str}`
- **Behavior**: Heuristic calculation (documented as estimate)

### F7: 90-Second Smoke Test

**Requirement**: End-to-end offline test proving core workflow.

**Test Flow**:
1. Store mock session → get pointer
2. Query index → find pointer
3. Retrieve session → decrypt → match original
4. Estimate cost → returns plausible value

**Acceptance Criteria**:
- Runs entirely offline (no network calls)
- Completes in <90 seconds
- Enforced in CI (fail if timeout)

---

## Non-Functional Requirements

| Category | Requirement |
|----------|-------------|
| **Performance** | Query: <100ms, Store: <5s (mock) |
| **Security** | Fail-closed redaction, AES-256-GCM encryption |
| **Testability** | 100% offline CI, no external dependencies |
| **Portability** | Python 3.10+, cross-platform (Linux/macOS/Windows) |
| **Documentation** | CLAUDE.md operator guide, inline docstrings |

---

## Out of Scope (Week 1)

- Real Cascade API integration (use mock)
- Multi-user authentication/RBAC
- Cascade-side search/indexing
- Cost tracking with real pricing data
- Cross-agent collaboration features

---

## Dependencies

**External**:
- Jeff Emanuel's `cass_memory_system` (optional, graceful degradation)
- Lumera Cascade API spec (design mock to match signature)

**Python Libraries**:
- `cryptography` (encryption)
- `sqlite3` (index)
- `mcp` (MCP server framework)

---

## Success Criteria

| Criterion | Definition of Done |
|-----------|-------------------|
| **Functional** | All 4 MCP tools execute successfully in smoke test |
| **Secure** | Redaction test proves fail-closed behavior |
| **Fast** | CI completes in <90 seconds |
| **Documented** | PRD, Architecture, Threat Model, Test Plan exist |

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| CASS CLI changes | High | Version-lock `cm` interface, use fixtures in tests |
| Key management complexity | Medium | Simple env var for MVP, document rotation process |
| Mock-to-real Cascade gap | Low | Design mock to match real API signature from day 1 |

---

**Next Steps**: Architecture design → Threat modeling → Implementation
