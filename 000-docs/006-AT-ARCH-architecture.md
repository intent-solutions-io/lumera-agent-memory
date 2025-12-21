# Architecture: Lumera Agent Memory

**Version**: 0.1.0
**Last Updated**: 2025-12-20

---

## System Overview

Lumera Agent Memory implements a **hybrid memory architecture** with three layers:

```
┌─────────────────────────────────────────────────────┐
│         Claude Code Agent (MCP Client)              │
└────────────────┬────────────────────────────────────┘
                 │ MCP Protocol
                 ▼
┌─────────────────────────────────────────────────────┐
│        MCP Server (lumera_memory_server.py)         │
│  ┌──────────────────────────────────────────────┐   │
│  │  4 Tools: store, query, retrieve, estimate   │   │
│  └───────────┬──────────────────────────────────┘   │
└──────────────┼──────────────────────────────────────┘
               │
       ┌───────┴────────┐
       │                │
       ▼                ▼
┌─────────────┐   ┌─────────────────┐
│  Security   │   │  CASS Adapter   │
│  Layer      │   │  (cm CLI)       │
└──────┬──────┘   └─────────────────┘
       │ Redact + Encrypt
       │
       ▼
┌─────────────────────────────────────────────────────┐
│              Storage Layer                          │
│  ┌──────────────────┐   ┌────────────────────────┐ │
│  │  Local Index     │   │  Cascade Mock          │ │
│  │  (SQLite)        │   │  (.cache/cascade-mock) │ │
│  │  - pointers      │   │  - encrypted blobs     │ │
│  │  - tags/metadata │   │  - content-addressed   │ │
│  └──────────────────┘   └────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

---

## Component Design

### 1. MCP Server (`src/mcp_server.py`)

**Responsibilities**:
- Expose 4 tools via MCP protocol
- Orchestrate calls to security, adapter, storage layers
- Handle errors gracefully with clear messages

**Tools Implemented**:

| Tool | Input | Output | Behavior |
|------|-------|--------|----------|
| `store_session_to_cascade` | session_id, tags | pointer, hash, indexed | Redact → Encrypt → Store → Index |
| `query_cascade_memories` | query, tags, limit | [{pointer, tags, created_at}] | Query local index only |
| `retrieve_session_from_cascade` | pointer | {session_data} | Fetch → Decrypt → Return |
| `estimate_storage_cost` | bytes, redundancy | {cost, disclaimer} | Heuristic calculation |

**Error Handling**:
- Redaction failures: Return clear error, do NOT store
- Encryption failures: Log error, propagate to client
- Storage failures: Retry once, then fail with context

### 2. Security Layer (`src/security/`)

#### `redact.py` (Fail-Closed)

**Design Philosophy**: Default deny. Only persist allowlisted fields.

**Secrets Detection**:
- Regex patterns for: API keys (`[A-Za-z0-9]{32,}`), AWS keys, SSH keys
- Email addresses (PII)
- Credit card numbers
- Environment variable exports (`export SECRET_KEY=...`)

**Behavior**:
```python
def redact_session(session: dict) -> dict:
    """Returns sanitized session OR raises RedactionError"""
    if detect_secrets(session):
        raise RedactionError("Secrets detected, aborting storage")
    return extract_allowlisted_fields(session)
```

**Allowlisted Fields** (MVP):
- `session_id`, `timestamp`, `tool_name`, `success`, `summary`, `tags`

#### `encrypt.py` (AES-256-GCM)

**Key Management**:
- Key sourced from `LUMERA_MEMORY_KEY` env var
- If missing, raise clear error with setup instructions
- Never log or persist keys

**Encryption Flow**:
```python
def encrypt_blob(data: bytes, key: bytes) -> bytes:
    """Returns: IV (12 bytes) + Ciphertext + Auth Tag (16 bytes)"""
    cipher = Cipher(algorithms.AES(key), modes.GCM(iv))
    return iv + ciphertext + tag
```

**Decryption Flow**:
```python
def decrypt_blob(encrypted: bytes, key: bytes) -> bytes:
    """Extract IV/tag, verify auth, return plaintext"""
    iv, ciphertext, tag = parse_encrypted_blob(encrypted)
    cipher = Cipher(algorithms.AES(key), modes.GCM(iv, tag))
    return plaintext
```

### 3. CASS Adapter (`src/adapters/cass_memory_system.py`)

**Purpose**: Bridge to Jeff Emanuel's `cm` CLI.

**Capability Detection**:
```python
def is_cm_available() -> bool:
    return shutil.which("cm") is not None
```

**Session Export**:
```python
def export_session(session_id: str) -> dict:
    if is_cm_available():
        result = subprocess.run(["cm", "context", session_id, "--json"], ...)
        return json.loads(result.stdout)
    else:
        return load_fixture(session_id)  # CI fallback
```

**Fixtures** (`src/adapters/fixtures.py`):
- Minimal JSON payloads mimicking `cm context --json`
- Used when `cm` not installed (CI, new users)

### 4. Cascade Connector (`src/cascade/`)

#### `interface.py` (API Contract)

**Abstract Interface**:
```python
class CascadeConnector(ABC):
    @abstractmethod
    def put(self, data: bytes) -> str:
        """Store blob, return content-addressed pointer"""

    @abstractmethod
    def get(self, pointer: str) -> bytes:
        """Retrieve blob by pointer"""
```

#### `mock_fs.py` (Week 1 Implementation)

**Storage Location**: `.cache/cascade-mock/` (gitignored)

**Content Addressing**:
```python
def put(self, data: bytes) -> str:
    content_hash = hashlib.sha256(data).hexdigest()
    path = self.cache_dir / content_hash[:2] / content_hash
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return f"cascade://{content_hash}"
```

**Pointer Format**: `cascade://<sha256-hash>`

**Future Swap**: Replace `MockCascadeConnector` with `LiveCascadeConnector` (same interface).

### 5. Local Index (`src/index/`)

#### `schema.sql`

```sql
CREATE TABLE memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pointer TEXT UNIQUE NOT NULL,
    content_hash TEXT NOT NULL,
    tags_json TEXT,
    created_at TEXT NOT NULL,
    schema_version TEXT DEFAULT '0.1.0',
    source_session_id TEXT,
    source_tool TEXT
);

CREATE INDEX idx_tags ON memories(tags_json);
CREATE INDEX idx_created ON memories(created_at DESC);
CREATE INDEX idx_session ON memories(source_session_id);
```

#### `index.py` (Query Logic)

**Insert**:
```python
def add_memory(pointer: str, content_hash: str, tags: list[str], ...):
    tags_json = json.dumps(tags)
    cursor.execute(
        "INSERT INTO memories (...) VALUES (...)",
        (pointer, content_hash, tags_json, ...)
    )
```

**Query**:
```python
def query_memories(tags: list[str] = None, limit: int = 10) -> list[dict]:
    query = "SELECT pointer, tags_json, created_at FROM memories WHERE 1=1"
    if tags:
        query += " AND tags_json LIKE ?"  # Substring match
    query += " ORDER BY created_at DESC LIMIT ?"
    return [dict(row) for row in cursor.execute(query, params)]
```

---

## Data Flow

### Store Session

```
1. Agent calls store_session_to_cascade(session_id, tags)
2. MCP Server → CASS Adapter: export_session(session_id)
3. MCP Server → Security: redact_session(raw_data)
   - If secrets detected → ABORT with error
4. MCP Server → Security: encrypt_blob(redacted_data, key)
5. MCP Server → Cascade: put(encrypted_blob)
   - Returns pointer (content hash)
6. MCP Server → Index: add_memory(pointer, hash, tags, ...)
7. Return {pointer, content_hash, indexed: true}
```

### Query Memories

```
1. Agent calls query_cascade_memories(tags, limit)
2. MCP Server → Index: query_memories(tags, limit)
3. Return [{pointer, tags, created_at}, ...]
   - NO CASCADE QUERY (local index only)
```

### Retrieve Session

```
1. Agent calls retrieve_session_from_cascade(pointer)
2. MCP Server → Cascade: get(pointer)
   - Returns encrypted_blob
3. MCP Server → Security: decrypt_blob(encrypted_blob, key)
4. Return {session_data: decrypted_json}
```

---

## Schema Versioning

**Version Field**: `schema_version` (default: `"0.1.0"`)

**Migration Strategy** (future):
- Alembic migrations for SQLite schema changes
- Cascade blobs are immutable (schema embedded in blob metadata)

---

## Performance Targets

| Operation | Target (Week 1) | Measurement |
|-----------|-----------------|-------------|
| Query (local) | <100ms | SQLite SELECT with index scan |
| Store (mock) | <5s | Redact + Encrypt + Write to disk |
| Retrieve (mock) | <1s | Read from disk + Decrypt |
| Smoke test | <90s | Full end-to-end cycle |

---

## Security Properties

| Property | Implementation |
|----------|----------------|
| **Confidentiality** | AES-256-GCM encryption at rest |
| **Integrity** | GCM auth tag + content-addressed pointers |
| **Fail-Closed** | Redaction aborts on ANY secret detection |
| **Key Custody** | User-controlled via env var (no cloud keys) |

---

## Future Evolution

### Week 2-3: Live Cascade Integration
- Replace `MockCascadeConnector` with HTTP API client
- Add retry logic, circuit breakers
- Real cost tracking with Cascade pricing API

### Week 4+: Multi-User & RBAC
- User authentication layer
- Encrypted shared memory pools
- Audit logs for compliance

---

**Design Principles**:
1. Local index for speed, Cascade for durability
2. Never search Cascade (pointer-based retrieval only)
3. Fail-closed security (abort on ANY risk)
4. Mock-to-production swap without API changes
