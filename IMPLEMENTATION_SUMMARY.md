# Lumera Agent Memory: Implementation Summary

## What Changed

### 1. Fixed MCP Tool Contract ✅

**Tool Names** (now match spec exactly):
- ✅ `store_session_to_cascade` (unchanged)
- ✅ `query_memories` (was `query_cascade_memories`)
- ✅ `retrieve_session_from_cascade` (unchanged)
- ✅ `estimate_storage_cost` (unchanged)

**Parameter Changes**:
- `store_session_to_cascade`: Added `metadata` and `mode` (mock|live) parameters
- `query_memories`: Added `query` (text search), `time_range` (filter), removed `session_id`
- `retrieve_session_from_cascade`: Changed `pointer` to `cascade_uri`, added `mode`
- All tools: `mode=mock` works, `mode=live` returns actionable error

**Return Shape Updates** (now match spec):
- All tools return `{"ok": true/false, ...}` instead of `{"success": true/false}`
- `store_session_to_cascade` returns:
  - `cascade_uri` (was `pointer`)
  - `memory_card` (NEW - WOW factor!)
  - `redaction.rules_fired` (list of redaction events)
  - `crypto` metadata (enc, key_id, hashes, bytes)
- `query_memories` returns:
  - `hits` array with `cascade_uri`, `title`, `snippet`, `score`, `tags`, `created_at`
- `retrieve_session_from_cascade` returns:
  - `cascade_uri`, `session` (payload), `crypto.verified`, `memory_card` (if available)
- `estimate_storage_cost` returns:
  - `bytes`, `gb`, `monthly_storage_usd`, `estimated_request_usd`, `total_estimated_usd`, `assumptions`

### 2. Changed Security Behavior ✅

**Old Behavior** (Week 1):
- Fail-closed on ANY detection
- Single pattern list - all treated as critical
- No redaction report

**New Behavior**:
- **CRITICAL secrets** (private keys, auth headers): FAIL-CLOSED (abort storage)
- **NON-CRITICAL PII** (emails, API keys, phone numbers, JWTs): REDACT with typed placeholders
- Always returns redaction report: `[{rule: "email", count: 2}, {rule: "api_key", count: 1}]`

**Typed Placeholders**:
- `<REDACTED:EMAIL>` - Emails
- `<REDACTED:API_KEY>` - API keys
- `<REDACTED:JWT>` - JSON Web Tokens
- `<REDACTED:CREDIT_CARD>` - Credit cards
- `<REDACTED:PHONE>` - Phone numbers
- `<REDACTED:IP_ADDRESS>` - IP addresses
- `<REDACTED:AWS_ACCESS_KEY>` - AWS access keys
- `<REDACTED:GITHUB_TOKEN>` - GitHub tokens

**Critical Patterns** (fail-closed):
- SSH/PGP private keys (`-----BEGIN RSA PRIVATE KEY-----`)
- Raw Authorization headers (`Authorization: Bearer ...`)

### 3. Added SQLite FTS5 for Local Search ✅

**Schema Changes**:
- Added `title`, `snippet`, `metadata_json` columns
- Created `memories_fts` virtual table using FTS5
- Added triggers to keep FTS in sync
- Schema version bumped to 0.2.0

**Query Improvements**:
- Text search using BM25 ranking (negative scores, lower = better match)
- Time range filtering (`{start: ISO8601, end: ISO8601}`)
- Combined filters: text + tags + time_range
- Returns `score` field in results

**Search Behavior**:
- If `query` provided: FTS5 search with BM25, sorted by score then recency
- If no `query`: Tag/time filtering only, sorted by recency
- NEVER queries Cascade (local index only)

### 4. Added Memory Card Generation (WOW Factor!) ✅

**What is a Memory Card?**
Deterministic NLP enrichment that extracts structured insights from session data WITHOUT network calls or ML models.

**Memory Card Fields**:
```json
{
  "title": "bug-tracker: demo-bug-report",
  "summary_bullets": [
    "Tool: bug-tracker (failed)",
    "Investigated production bug in auth service",
    "Stack trace shows JWT decode error"
  ],
  "decisions": ["roll back to v2.3.1"],
  "todos": ["Fix JWT validation before next deploy"],
  "entities": ["JWT", "API"],
  "keywords": ["bug", "auth", "production", "jwt", "decode", "error"],
  "notable_quotes": ["Invalid token format"]
}
```

**Heuristics Used** (all offline):
- **Title**: First sentence of summary or session_id + tool_name
- **Summary**: Key sentences from summary field + metadata
- **Decisions**: Pattern matching for "decided", "chose", "approved", "rejected"
- **Todos**: Pattern matching for "TODO", "need to", "must", "should"
- **Entities**: Capitalized phrases, alphanumeric names
- **Keywords**: Frequency-based after stopword removal (simple RAKE-like)
- **Quotes**: Text in literal quotes (10-160 chars)

**Integration**:
- Generated AFTER redaction (operates on clean data)
- Stored in index `metadata_json` field
- Returned in `store_session_to_cascade` response
- Included in `retrieve_session_from_cascade` if available
- Used for `title` and `snippet` in search results

### 5. Better Fixtures ✅

Added `demo-bug-report` fixture with:
- Email address (redacted to `<REDACTED:EMAIL>`)
- API key (redacted to `<REDACTED:API_KEY>`)
- Decision statement ("Decided to roll back to v2.3.1")
- TODO item ("TODO: Fix JWT validation")
- JWT error context

Perfect for demonstrating:
- Typed redaction with reports
- Memory card generation
- Search with relevant keywords

## How It Works Now

### Store Pipeline

```
1. Export session from CASS (or fixture)
2. Detect CRITICAL secrets → FAIL if found
3. Redact non-critical PII with typed placeholders → Produce report
4. Generate Memory Card (deterministic NLP heuristics)
5. Serialize + Encrypt (AES-256-GCM)
6. Store in Cascade mock (content-addressed: SHA-256)
7. Index: pointer + content_hash + title + snippet + memory_card metadata
8. Return: cascade_uri + memory_card + redaction report + crypto metadata
```

### Query Pipeline

```
1. Parse query parameters (query text, tags, time_range, limit)
2. If query text: FTS5 search with BM25 ranking
3. If no query: Tag/time filtering only
4. Join with main table to get all metadata
5. Return: hits with cascade_uri, title, snippet, score, tags, created_at
```

### Retrieve Pipeline

```
1. Validate cascade_uri format
2. Fetch encrypted blob from Cascade
3. Decrypt + verify hashes
4. Parse session payload
5. Lookup memory_card from index metadata
6. Return: session + crypto verification + memory_card (if available)
```

##Files Changed

**Modified**:
- `src/mcp_server.py` - Tool names, parameter/return shapes, memory card integration
- `src/security/redact.py` - Typed redaction, critical vs non-critical, report generation
- `src/index/index.py` - FTS5 search, title/snippet/metadata fields, BM25 ranking
- `src/index/schema.sql` - FTS5 virtual table, triggers, new columns
- `src/adapters/fixtures.py` - Added demo-bug-report with messy data

**Created**:
- `src/enrich/__init__.py` - Enrichment module exports
- `src/enrich/memory_card.py` - Deterministic NLP heuristics for memory card generation

## Commands to Run

### Setup

```bash
cd plugins/lumera-agent-memory
./scripts/dev_setup.sh
source .venv/bin/activate
export LUMERA_MEMORY_KEY=$(openssl rand -hex 32)
```

### Run Tests

```bash
# All tests
pytest tests/ -v

# Security tests (redaction + encryption)
pytest tests/test_redaction.py tests/test_encryption.py -v

# Smoke test
./scripts/run_smoke.sh
```

### Run MCP Server

```bash
# Direct invocation
python -m src.mcp_server

# Server will listen on stdin/stdout (MCP protocol)
# Use with Claude Code or MCP inspector
```

## Example Usage

### 1. Store Session (with WOW factor!)

**Request**:
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

**Response** (abbreviated):
```json
{
  "ok": true,
  "session_id": "demo-bug-report",
  "cascade_uri": "cascade://abc123...",
  "indexed": true,
  "memory_card": {
    "title": "bug-tracker: demo-bug-report",
    "summary_bullets": [
      "Tool: bug-tracker (failed)",
      "Investigated production bug in auth service"
    ],
    "decisions": ["roll back to v2.3.1"],
    "todos": ["Fix JWT validation before next deploy"],
    "entities": ["JWT"],
    "keywords": ["bug", "auth", "production", "jwt"],
    "notable_quotes": ["Invalid token format"]
  },
  "redaction": {
    "rules_fired": [
      {"rule": "email", "count": 1},
      {"rule": "api_key", "count": 1}
    ]
  },
  "crypto": {
    "enc": "AES-256-GCM",
    "key_id": "env:LUMERA_MEMORY_KEY",
    "plaintext_sha256": "def456...",
    "ciphertext_sha256": "abc123...",
    "bytes": 512
  }
}
```

### 2. Query Memories (FTS5 + BM25)

**Request**:
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

**Response**:
```json
{
  "ok": true,
  "hits": [
    {
      "cass_session_id": "demo-bug-report",
      "cascade_uri": "cascade://abc123...",
      "title": "bug-tracker: demo-bug-report",
      "snippet": "Tool: bug-tracker (failed) | Investigated production bug in auth service",
      "tags": ["demo", "production", "bug", "auth", "jwt"],
      "created_at": "2025-12-21T08:00:00",
      "score": -2.34
    }
  ]
}
```

### 3. Retrieve Session (with Memory Card)

**Request**:
```json
{
  "tool": "retrieve_session_from_cascade",
  "arguments": {
    "cascade_uri": "cascade://abc123...",
    "mode": "mock"
  }
}
```

**Response** (abbreviated):
```json
{
  "ok": true,
  "cascade_uri": "cascade://abc123...",
  "session": {
    "session_id": "demo-bug-report",
    "tool_name": "bug-tracker",
    "summary": "Investigated production bug... <REDACTED:EMAIL> ... <REDACTED:API_KEY>",
    "success": false
  },
  "memory_card": {
    "title": "bug-tracker: demo-bug-report",
    "summary_bullets": [...],
    "decisions": [...],
    "todos": [...]
  },
  "crypto": {
    "verified": true,
    "plaintext_sha256": "def456...",
    "ciphertext_sha256": "abc123...",
    "key_id": "env:LUMERA_MEMORY_KEY"
  }
}
```

### 4. Estimate Cost

**Request**:
```json
{
  "tool": "estimate_storage_cost",
  "arguments": {
    "bytes": 1048576,
    "redundancy": 3
  }
}
```

**Response**:
```json
{
  "ok": true,
  "bytes": 1048576,
  "gb": 0.001,
  "monthly_storage_usd": 0.00009,
  "estimated_request_usd": 0.001,
  "total_estimated_usd": 0.00109,
  "assumptions": {
    "redundancy": 3,
    "estimated_requests_per_month": 100,
    "note": "Heuristic estimate. Not based on real Cascade pricing."
  }
}
```

## What's Still Mock/Stubbed

- **Cascade connector**: Still filesystem-backed (`MockCascadeConnector`)
- **Live mode**: Returns actionable error message (not implemented)
- **CASS integration**: Uses fixtures (graceful degradation if `cm` CLI not found)
- **Cost estimation**: Heuristic pricing (not real Cascade API)

## Next Steps (Week 2+)

1. **Live Cascade integration**: Replace `MockCascadeConnector` with HTTP API client
2. **Real cost tracking**: Query Cascade pricing API
3. **Retry logic**: Add exponential backoff for network failures
4. **Circuit breakers**: Protect against Cascade outages
5. **Production deployment**: Docker, monitoring, alerting

## Design Compliance

✅ **Search NEVER queries Cascade** - Local SQLite FTS5 only
✅ **Tool names match spec** - Exact 4 tools with correct names
✅ **Return shapes match spec** - `ok`, `cascade_uri`, structured responses
✅ **Security pipeline** - Redact → Encrypt → Store → Index
✅ **Fail-closed for critical secrets** - Private keys, auth headers abort
✅ **Redact-and-continue for PII** - Typed placeholders with reports
✅ **Memory Card WOW factor** - Deterministic NLP enrichment
✅ **FTS5 search** - BM25 ranking with time/tag filters
✅ **Mode support** - `mock` works, `live` returns clear error

## Testing Status

**Tests to Update**:
- `test_redaction.py` - Update to test typed redaction (not fail-on-any)
- Add `test_memory_card.py` - Test deterministic output
- Add `test_fts_search.py` - Test FTS5 queries with BM25
- Update `smoke_test_90s.py` - Test full store → query → retrieve with memory card

**Expected Behavior**:
- Security tests: Critical secrets fail, non-critical get redacted with report
- Memory card tests: Stable output for same input (deterministic)
- FTS tests: BM25 scores, time range filtering, tag + text combo
- Smoke test: Complete e2e with memory card present in all responses
