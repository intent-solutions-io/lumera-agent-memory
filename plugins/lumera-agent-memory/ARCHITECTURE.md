# Lumera Agent Memory - Architecture

## CEO Feedback: Privacy-First Design

> **"No one should be able to see what happens in my sessions. Too much liability."**
>
> **"Even with encryption, it's easy to mess up."**

Therefore: We do NOT build "export raw sessions" as the default product. We build a **safe-by-default system** that stores ONLY sanitized, derived artifacts unless the user explicitly opts into storing raw content.

## System Architecture

```
┌─────────────────────────────────────────┐
│    Claude Code Agent (MCP Client)       │
└───────────────┬─────────────────────────┘
                │ MCP Protocol
                ▼
┌─────────────────────────────────────────┐
│  MCP Server (4 Tools)                   │
│  ├─ store_session_to_cascade            │
│  ├─ query_memories                      │
│  ├─ retrieve_session_from_cascade       │
│  └─ estimate_storage_cost               │
└───────────────┬─────────────────────────┘
                │
     ┌──────────┴──────────────────────────────┐
     │                                         │
     ▼                                         ▼
┌──────────────────────────┐        ┌──────────────────────────┐
│  Derivation + Safety Gate │        │       CASS Adapter       │
│  - redact (always)        │        │  (cm CLI + fixtures)     │
│  - memory_card (default)  │        └──────────────────────────┘
│  - CRITICAL fail-closed   │
│  - dry_run preview        │
│  - raw export OPT-IN gate │
└──────────────┬───────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────────┐
│ Storage + Index                                              │
│  ┌─────────────────────────┐   ┌─────────────────────────┐   │
│  │ Local Index (SQLite/FTS)│   │ Cascade (Mock/Live)     │   │
│  │ - stores URIs + metadata│   │ - stores encrypted blob │   │
│  │ - stores memory_card    │   │ - DEFAULT: artifact only│   │
│  └─────────────────────────┘   └─────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

## Data Flow

### Default Flow (Artifact-Only)

```
Session Data → Redact → Memory Card → Encrypt → Cascade
                  ↓
            Index (URI + card)
```

**What gets stored in Cascade (DEFAULT)**:
- Memory Card: { title, summary_bullets, decisions, todos, entities, keywords, notable_quotes }
- Redaction report: { rules_fired: [...] }
- Minimal metadata: { session_id, timestamp, tags }

**What does NOT get stored**: Raw session transcript

### Opt-In Raw Export Flow

```
Session Data + allow_raw_export=true + raw_export_ack →
  Redact → Memory Card + Raw Session → Encrypt → Cascade
                  ↓
            Index (URI + card + artifact_type)
```

**Requirements for raw export**:
1. `metadata.allow_raw_export === true`
2. `metadata.raw_export_ack === "I understand the risk"`

Without BOTH conditions, raw transcript is NOT uploaded.

### Dry-Run Preview Flow

```
Session Data + dry_run=true →
  Redact → Memory Card → Preview (no upload) → Return preview object
```

**Dry-run preview returns**:
- Exact payload that would be uploaded
- Byte size, field list
- Redaction report (what was removed)
- NO cascade_uri (no upload occurred)

## Security Posture

### Three-Tier Safety Model

1. **CRITICAL patterns** (fail-closed):
   - Private keys (SSH, PGP)
   - Authorization headers
   - Raw bearer tokens
   - **Action**: Abort durable storage entirely
   - **Local-only**: May still generate memory_card if clean

2. **Non-critical PII** (redact-and-continue):
   - Emails, phone numbers, names, API keys, JWTs
   - **Action**: Replace with typed placeholders
   - **Example**: `john.doe@example.com` → `<REDACTED:EMAIL>`

3. **Opt-in raw export** (explicit acknowledgment):
   - User must set BOTH flags
   - Raw transcript stored alongside artifact
   - **Default**: Blocked

### Encryption: Defense-in-Depth

- **Algorithm**: AES-256-GCM
- **Key source**: LUMERA_MEMORY_KEY environment variable
- **Posture**: Since raw transcripts are NOT stored by default, encryption is defense-in-depth rather than sole safety net
- **Logging**: All logging avoids sensitive content

## Storage Types

### Artifact-Only (DEFAULT)

```json
{
  "artifact_type": "artifact_only",
  "session_id": "demo-001",
  "timestamp": "2025-12-21T12:00:00Z",
  "memory_card": {
    "title": "Bug fix: JWT validation",
    "summary_bullets": ["Fixed auth service bug", "Rolled back to v2.3.1"],
    "decisions": ["Roll back to stable version"],
    "todos": ["Fix JWT validation before next deploy"],
    "entities": ["JWT", "auth-service"],
    "keywords": ["bug", "auth", "jwt", "rollback"],
    "notable_quotes": ["Invalid token format"]
  },
  "redaction_report": [
    {"rule": "email", "count": 1},
    {"rule": "api_key", "count": 1}
  ],
  "tags": ["production", "bug-fix"]
}
```

**Size**: ~1-2 KB (compact, sanitized)

### Raw + Artifact (OPT-IN ONLY)

```json
{
  "artifact_type": "raw_plus_artifact",
  "session_id": "demo-001",
  "timestamp": "2025-12-21T12:00:00Z",
  "memory_card": { ... },
  "redaction_report": [ ... ],
  "raw_session": {
    "tool_name": "bug-tracker",
    "summary": "Investigated production bug... <REDACTED:EMAIL> ...",
    "success": false,
    "error_message": "...",
    "output": "..."
  },
  "tags": ["production", "bug-fix"]
}
```

**Size**: ~10-100 KB (includes full redacted transcript)

**Requirements**: User must provide:
- `metadata.allow_raw_export = true`
- `metadata.raw_export_ack = "I understand the risk"`

## MCP Tool Reference

### 1. store_session_to_cascade

**Input**:
```json
{
  "session_id": "demo-001",
  "tags": ["production"],
  "metadata": {
    "dry_run": false,
    "allow_raw_export": false,
    "raw_export_ack": null
  },
  "mode": "mock"
}
```

**Output (artifact-only)**:
```json
{
  "ok": true,
  "session_id": "demo-001",
  "cascade_uri": "cascade://abc123...",
  "artifact_type": "artifact_only",
  "indexed": true,
  "memory_card": { ... },
  "redaction": {
    "rules_fired": [
      {"rule": "email", "count": 1}
    ]
  },
  "crypto": {
    "enc": "AES-256-GCM",
    "bytes": 1024
  }
}
```

**Output (dry-run)**:
```json
{
  "ok": true,
  "dry_run": true,
  "preview": {
    "artifact_type": "artifact_only",
    "fields": ["session_id", "memory_card", "redaction_report", "tags"],
    "bytes": 1024,
    "would_upload": false
  },
  "memory_card": { ... },
  "redaction": { ... }
}
```

### 2. query_memories

**Input**:
```json
{
  "query": "JWT auth bug",
  "tags": ["production"],
  "limit": 5
}
```

**Output**:
```json
{
  "ok": true,
  "hits": [
    {
      "cass_session_id": "demo-001",
      "cascade_uri": "cascade://abc123...",
      "artifact_type": "artifact_only",
      "title": "Bug fix: JWT validation",
      "snippet": "Fixed auth service bug | Rolled back to v2.3.1",
      "tags": ["production", "bug-fix"],
      "created_at": "2025-12-21T12:00:00Z",
      "score": -2.34
    }
  ]
}
```

### 3. retrieve_session_from_cascade

**Input**:
```json
{
  "cascade_uri": "cascade://abc123...",
  "mode": "mock"
}
```

**Output (artifact-only)**:
```json
{
  "ok": true,
  "cascade_uri": "cascade://abc123...",
  "artifact_type": "artifact_only",
  "artifact": {
    "session_id": "demo-001",
    "memory_card": { ... },
    "redaction_report": [ ... ],
    "tags": ["production"]
  },
  "crypto": {
    "verified": true
  }
}
```

**Output (raw + artifact)**:
```json
{
  "ok": true,
  "cascade_uri": "cascade://abc123...",
  "artifact_type": "raw_plus_artifact",
  "artifact": {
    "session_id": "demo-001",
    "memory_card": { ... },
    "redaction_report": [ ... ],
    "raw_session": { ... },
    "tags": ["production"]
  },
  "crypto": {
    "verified": true
  }
}
```

### 4. estimate_storage_cost

**Input**:
```json
{
  "bytes": 1024,
  "redundancy": 3
}
```

**Output**:
```json
{
  "ok": true,
  "bytes": 1024,
  "gb": 0.000001,
  "monthly_storage_usd": 0.00003,
  "estimated_request_usd": 0.001,
  "total_estimated_usd": 0.00103
}
```

## Local Index Schema

```sql
CREATE TABLE memories (
  id INTEGER PRIMARY KEY,
  pointer TEXT NOT NULL,           -- cascade://...
  content_hash TEXT NOT NULL,      -- SHA-256 of encrypted blob
  artifact_type TEXT NOT NULL,     -- "artifact_only" | "raw_plus_artifact"
  tags_json TEXT NOT NULL,
  source_session_id TEXT,
  source_tool TEXT,
  title TEXT,                      -- from memory_card
  snippet TEXT,                    -- from memory_card
  metadata_json TEXT,              -- includes memory_card + redaction_report
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
```

## Privacy Guarantees

1. **Default: No raw sessions stored** - Only sanitized Memory Cards
2. **Opt-in required for raw** - Explicit acknowledgment + flag
3. **Dry-run preview** - See exactly what would be uploaded before commitment
4. **Fail-closed on CRITICAL** - Private keys/auth headers block durable storage
5. **Local search only** - Search never queries Cascade (privacy + performance)
6. **Client-side encryption** - User-controlled keys
7. **Logging safety** - No sensitive content in logs

## Development Status

**NOT PRODUCTION READY** - This is an early-stage development project:

- ✅ Privacy-first artifact-only storage
- ✅ Opt-in gate for raw export
- ✅ Dry-run preview mode
- ✅ Security features implemented
- ❌ NO security audit performed
- ❌ NO penetration testing conducted
- ❌ NO formal cryptographic review
- ❌ NO production hardening

**Use for development/testing purposes only.**
