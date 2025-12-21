# Lumera Agent Memory

> **⚠️ ACTIVE DEVELOPMENT** - This project is under active development. Features and APIs are subject to change.
>
> **🔒 SECURITY NOTICE**: This is a developmental project. While security features are implemented (AES-256-GCM encryption, fail-closed redaction), this software has NOT been audited for production use. Use at your own risk.

A hybrid local-search + Cascade-storage memory system for coding agents. **Privacy-first design**: stores ONLY sanitized artifacts by default (no raw sessions).

## CEO Feedback-Driven Design

> **"No one should be able to see what happens in my sessions. Too much liability."**
>
> **"Even with encryption, it's easy to mess up."**

**Our Response**: We do NOT build "export raw sessions" as the default product. We build a **safe-by-default system** that stores ONLY sanitized, derived artifacts unless you explicitly opt into storing raw content.

**Default Behavior**:
- ✅ Stores Memory Card (title, summary, decisions, todos, entities, keywords)
- ✅ Stores redaction report (what was removed)
- ✅ Stores minimal metadata (timestamps, tags)
- ❌ Does NOT store raw session transcript

**Opt-In for Raw Export** (requires BOTH):
1. `metadata.allow_raw_export = true`
2. `metadata.raw_export_ack = "I understand the risk"`

Without BOTH conditions, raw transcript is NOT uploaded (even encrypted).

## Status

- ✅ **Privacy-First**: Artifact-only storage by default (CEO feedback incorporated)
- ✅ **Opt-In Gate**: Raw export requires explicit acknowledgment
- ✅ **Dry-Run Preview**: See exactly what would be stored before committing
- ✅ **Security Layer**: Client-side AES-256-GCM encryption, typed redaction with fail-closed on critical secrets
- ✅ **Storage Layer**: Mock Cascade (filesystem-backed), content-addressed pointers
- ✅ **Search Layer**: SQLite FTS5 with BM25 ranking (local index, never queries Cascade)
- ✅ **Enrichment**: Deterministic NLP-based Memory Card generation (offline)
- ✅ **MCP Server**: 4 tools (store, query, retrieve, estimate_cost)
- 🚧 **Live Cascade**: Stubbed (returns actionable error)
- 🚧 **Production Tests**: In progress

## Quick Start

```bash
# 1. Install dependencies
cd plugins/lumera-agent-memory
./scripts/dev_setup.sh
source .venv/bin/activate

# 2. Set encryption key (required)
export LUMERA_MEMORY_KEY=$(openssl rand -hex 32)

# 3. Run tests
pytest tests/ -v

# 4. Start MCP server
python -m src.mcp_server
```

## Architecture

```
CASS Session → Redact (typed PII) → Encrypt (AES-256-GCM) →
Store in Cascade → Index (SQLite FTS5) → Search (local only)
```

**Key Design Principles**:
- Search NEVER queries Cascade (local SQLite index only)
- Content-addressed storage (`cascade://<sha256-hash>`)
- Fail-closed security (critical secrets abort storage)
- Client-side encryption (user-controlled keys)

## Security

### ⚠️ Development Status

**NOT PRODUCTION READY** - This is an early-stage development project:

- ✅ Security features implemented: AES-256-GCM encryption, typed redaction, fail-closed on critical secrets
- ❌ NO security audit performed
- ❌ NO penetration testing conducted
- ❌ NO formal cryptographic review
- ❌ NO production hardening

**Use for development/testing purposes only.** Do not store sensitive production data.

### Security Model

**Two-Tier Redaction**:
1. **Critical Secrets** (fail-closed): SSH keys, PGP keys, Authorization headers → Abort storage
2. **Non-Critical PII** (redact-and-continue): Emails, API keys, JWTs, credit cards → Typed placeholders

Example: `john.doe@example.com` → `<REDACTED:EMAIL>`

**Encryption**: Client-side AES-256-GCM with user-controlled keys (LUMERA_MEMORY_KEY env var)

**Key Management**: Keys are NOT managed by this system. Users must securely store and rotate their own keys.

## Example Usage

### 1. Store Artifact-Only (DEFAULT - Privacy-First)

```json
{
  "tool": "store_session_to_cascade",
  "arguments": {
    "session_id": "demo-bug-report",
    "tags": ["production", "bug-fix"],
    "mode": "mock"
  }
}
```

**Result**: Stores ONLY Memory Card + redaction report (NO raw transcript)

### 2. Dry-Run Preview (See What Would Be Stored)

```json
{
  "tool": "store_session_to_cascade",
  "arguments": {
    "session_id": "demo-bug-report",
    "tags": ["production"],
    "metadata": {
      "dry_run": true
    },
    "mode": "mock"
  }
}
```

**Result**: Preview object showing fields, byte size, what would be uploaded. NO upload occurs.

### 3. Opt-In Raw Export (Explicit Acknowledgment Required)

```json
{
  "tool": "store_session_to_cascade",
  "arguments": {
    "session_id": "demo-bug-report",
    "tags": ["production"],
    "metadata": {
      "allow_raw_export": true,
      "raw_export_ack": "I understand the risk"
    },
    "mode": "mock"
  }
}
```

**Result**: Stores Memory Card + redacted raw session transcript

### 4. Query Memories (Local Search Only)

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

**Result**: Hits with `cascade_uri`, `artifact_type`, title, snippet, BM25 score

### 5. Retrieve Artifact

```json
{
  "tool": "retrieve_session_from_cascade",
  "arguments": {
    "cascade_uri": "cascade://abc123...",
    "mode": "mock"
  }
}
```

**Result**: Decrypted artifact (type: `artifact_only` or `raw_plus_artifact`)

## MCP Tools

1. `store_session_to_cascade` - Store session with privacy-first artifact design
2. `query_memories` - Search local index (FTS5 + BM25 ranking)
3. `retrieve_session_from_cascade` - Fetch and decrypt artifact by URI
4. `estimate_storage_cost` - Heuristic cost calculation

## Development

**Requirements**: Python 3.10+

```bash
# Install in editable mode
pip install -e .

# Run tests
pytest tests/ -v

# Format code
black src/ tests/
isort src/ tests/

# Lint
flake8 src/ tests/
```

## Documentation

- **[PROJECT.md](PROJECT.md)** - Detailed project tree and tool documentation
- **[IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)** - Week 1 implementation changes

## Roadmap

**Week 1** ✅ - Scaffold with mock Cascade, security layer, local search
**Week 2** 🚧 - Live Cascade HTTP API integration
**Week 3** 📋 - Retry logic, circuit breakers, production monitoring
**Week 4** 📋 - Docker deployment, observability, real cost tracking

## License

MIT

## Contact

Jeremy Longshore - jeremy@intentsolutions.io
