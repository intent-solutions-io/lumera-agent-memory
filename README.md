# Lumera Agent Memory

**Hybrid local-search + Cascade-storage memory system for coding agents**

Version: 0.1.0 (Week 1 Scaffold)

---

## Overview

Lumera Agent Memory bridges Jeff Emanuel's [CASS memory system](https://github.com/Dicklesworthstone/cass_memory_system) to Lumera Cascade, creating a hybrid architecture where:

- **Fast local search** queries a SQLite index for pointers
- **Durable encrypted storage** persists session blobs in Cascade
- **Fail-closed security** prevents secrets from ever being stored

**Key Principle**: Search NEVER queries Cascade. Only local index returns pointers for retrieval.

---

## Features (Week 1)

✅ **4 MCP Tools**
- `store_session_to_cascade` - Redact + encrypt + store
- `query_cascade_memories` - Search local index (pointers only)
- `retrieve_session_from_cascade` - Fetch + decrypt by pointer
- `estimate_storage_cost` - Heuristic cost calculation

✅ **Security**
- Fail-closed redaction (aborts on ANY secret detection)
- AES-256-GCM client-side encryption
- User-controlled keys via `LUMERA_MEMORY_KEY` env var

✅ **Storage**
- Mock Cascade connector (filesystem-backed, Week 1)
- SQLite local index with tag-based queries
- Content-addressed pointers (SHA-256)

✅ **CASS Integration**
- Adapter for `cm` CLI (graceful degradation if not installed)
- Test fixtures for CI

✅ **Testing**
- 90-second smoke test (CI gate)
- Security tests (redaction + encryption)
- Component tests (storage + index)

---

## Quick Start

### Setup

```bash
cd plugins/lumera-agent-memory
./scripts/dev_setup.sh

# Activate virtual environment
source .venv/bin/activate

# Set encryption key
export LUMERA_MEMORY_KEY=$(openssl rand -hex 32)

# Optional: Save to .env (DO NOT COMMIT)
echo "LUMERA_MEMORY_KEY=$(openssl rand -hex 32)" > .env
```

### Run Tests

```bash
# All tests
pytest tests/ -v

# Security tests only
pytest tests/test_redaction.py tests/test_encryption.py -v

# 90-second smoke test
./scripts/run_smoke.sh
```

### Run MCP Server

```bash
# Start server
python -m src.mcp_server

# Or via Claude Code:
# Add to .claude/mcp.json, then invoke via MCP tools
```

---

## Architecture

```
┌─────────────────────────────────────────┐
│    Claude Code Agent (MCP Client)       │
└───────────────┬─────────────────────────┘
                │ MCP Protocol
                ▼
┌─────────────────────────────────────────┐
│  MCP Server (4 Tools)                   │
│  ├─ store_session_to_cascade            │
│  ├─ query_cascade_memories              │
│  ├─ retrieve_session_from_cascade       │
│  └─ estimate_storage_cost               │
└───────────────┬─────────────────────────┘
                │
       ┌────────┴────────┐
       │                 │
       ▼                 ▼
┌─────────────┐   ┌────────────────┐
│  Security   │   │  CASS Adapter  │
│  (Redact +  │   │  (cm CLI)      │
│   Encrypt)  │   │                │
└──────┬──────┘   └────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│  Storage Layer                          │
│  ┌──────────────┐   ┌────────────────┐ │
│  │ Local Index  │   │ Cascade Mock   │ │
│  │ (SQLite)     │   │ (Filesystem)   │ │
│  └──────────────┘   └────────────────┘ │
└─────────────────────────────────────────┘
```

---

## Documentation

All planning docs are in `000-docs/planned-plugins/lumera-agent-memory/`:

- **01-BUSINESS-CASE.md** - Why this exists, target users, success metrics
- **02-PRD.md** - Product requirements, features, non-goals
- **03-ARCHITECTURE.md** - System design, data flow, components
- **04-THREAT-MODEL.md** - Security threats, mitigations, incident response
- **05-TEST-PLAN.md** - Test strategy, levels, success criteria
- **06-STATUS.md** - Week 1 checklist, progress tracking

---

## Security

**Fail-Closed Design**: If ANY secret or PII is detected during redaction, storage is aborted with a clear error. No guessing, no warnings—just fail.

**Secrets Detected**:
- API keys (32+ char alphanumeric)
- AWS access keys (`AKIA...`)
- SSH private keys (`-----BEGIN...`)
- Email addresses (PII)
- Credit card numbers

**Encryption**: AES-256-GCM with user-controlled keys. Blobs stored encrypted at rest. Keys NEVER leave your machine.

**Key Management**:
```bash
# Generate key
export LUMERA_MEMORY_KEY=$(openssl rand -hex 32)

# Persist (DO NOT COMMIT .env)
echo "LUMERA_MEMORY_KEY=$(openssl rand -hex 32)" > .env
source .env
```

---

## CI/CD

**PR Validation** (`.github/workflows/pr.yml`):
- Security tests (redaction + encryption)
- Component tests (cascade + index)
- 90-second smoke test (timeout enforced)
- Lint checks (black, isort, flake8)

**Main Branch** (`.github/workflows/main.yml`):
- All PR checks
- Coverage reports
- Artifact uploads

**CI Gate**: Smoke test MUST complete in <90 seconds.

---

## Week 1 Status

| Component | Status |
|-----------|--------|
| Documentation | ✅ Complete |
| Security Layer | ✅ Complete |
| Storage Layer | ✅ Complete |
| CASS Adapter | ✅ Complete |
| MCP Server | ✅ Complete |
| Tests (35+) | ✅ Complete |
| CI/CD | ✅ Complete |

**Next**: Week 2 - Live Cascade integration

---

## Beads Integration

```bash
# Initialize Beads
cd /home/jeremy/000-projects/Lumera-Emanuel
bd quickstart

# Create tasks
bd create "Week 1: Scaffold complete" --status done
bd create "Week 2: Live Cascade integration" --status open
```

---

## Contributing

This is a prototype/experimental project for business development with Jeff Emanuel and Lumera.

**Standards**:
- Follow existing code patterns
- All security tests must prove fail-closed
- Smoke test must stay <90 seconds
- Document architectural decisions

---

## License

MIT

---

## Contact

Jeremy Longshore
Email: jeremy@intentsolutions.io
GitHub: [@intent-solutions-io](https://github.com/intent-solutions-io)
