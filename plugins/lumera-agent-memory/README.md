# Lumera Agent Memory

> This project is under active development. Features and APIs may change.
>
> This is a developmental project. Security features are implemented but the software has not been audited for production use. Use at your own risk.

A memory storage system for coding agents. Stores sanitized artifacts by default.

## Design Approach

The system stores only sanitized data by default (no raw session transcripts). This approach reduces liability and simplifies security.

**Default Storage**:
- Memory Card: title, summary, decisions, todos, entities, keywords
- Redaction report: what was removed
- Minimal metadata: timestamps, tags

Raw session transcripts are not stored by default.

**Raw Export Option**:
If you need to store raw sessions, you must provide both:
1. `metadata.allow_raw_export = true`
2. `metadata.raw_export_ack = "I understand the risk"`

Without both flags, only sanitized artifacts are stored.

## Current Status

- Artifact-only storage by default
- Opt-in gate for raw export
- Dry-run preview mode
- Client-side AES-256-GCM encryption
- Mock Cascade storage (filesystem-backed)
- SQLite FTS5 search (local only)
- Deterministic Memory Card generation
- 4 MCP tools
- Live Cascade: not yet implemented
- Production testing: in progress

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

## How It Works

```
CASS Session → Redact → Encrypt → Store in Cascade → Index in SQLite → Local Search
```

**Design notes**:
- Search queries local SQLite index only (never queries Cascade)
- Content-addressed storage using SHA-256 hashes
- Critical secrets abort storage
- Encryption uses user-controlled keys

## Security Notes

This is early development software. Not ready for production use.

- Security features are implemented
- No security audit has been performed
- No penetration testing conducted
- No formal cryptographic review
- Not production-hardened

Use for development and testing only.

### Redaction Approach

Two levels:
1. Critical secrets (SSH keys, PGP keys, auth headers): Storage aborted
2. Non-critical PII (emails, API keys, JWTs): Replaced with typed placeholders

Example: `john.doe@example.com` becomes `<REDACTED:EMAIL>`

### Encryption

Client-side AES-256-GCM with user-controlled keys via LUMERA_MEMORY_KEY environment variable. Keys are not managed by this system.

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

Result: Stores only Memory Card and redaction report.

### 2. Dry-Run Preview

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

Result: Preview object showing what would be uploaded. No actual upload occurs.

### 3. Opt-In Raw Export

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

Result: Stores Memory Card plus redacted session transcript.

### 4. Query Memories

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

Result: Hits with cascade_uri, artifact_type, title, snippet, and BM25 relevance score.

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

Result: Decrypted artifact (artifact_only or raw_plus_artifact type).

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
