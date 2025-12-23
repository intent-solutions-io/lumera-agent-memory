# Changelog

All notable changes to lumera-agent-memory will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2025-12-22

### Summary
Privacy-first storage architecture based on CEO feedback. Default behavior now stores only sanitized artifacts (no raw sessions).

### Changed
- **BREAKING**: Default storage mode changed to artifact-only (no raw session transcripts)
- **BREAKING**: Raw export requires explicit opt-in with TWO flags: `allow_raw_export=true` AND `raw_export_ack="I understand the risk"`
- Schema updated to v0.3.0 with `artifact_type` column (`artifact_only` | `raw_plus_artifact`)
- MCP tool `query_cascade_memories` renamed to `query_memories`

### Added
- Dry-run preview mode: See what would be stored without uploading (`metadata.dry_run=true`)
- Memory Card enrichment: Deterministic NLP extracts title, summary, decisions, todos, entities, keywords, quotes
- Privacy-first validation: 15 new tests proving artifact-only defaults and opt-in gates
- ARCHITECTURE.md with CEO feedback context and data flow diagrams
- Comprehensive README with usage examples

### Security
- Fail-closed on CRITICAL patterns (private keys, auth headers, bearer tokens)
- Typed redaction for non-critical PII (emails → `<REDACTED:EMAIL>`, API keys → `<REDACTED:API_KEY>`)
- Client-side AES-256-GCM encryption (user-controlled keys)
- No sensitive data in logs or examples

### Fixed
- SQLite index schema now properly tracks artifact type
- Query results include artifact_type field
- Retrieve responses return proper artifact structure based on type

### Code Metrics
- Lines of Code: ~2,000
- Test Coverage: 15 new privacy-first tests (100% pass rate)
- Security Patterns: 8 redaction rules (2 critical, 6 non-critical)

### Privacy-First Validation
- ✅ Artifact-only storage is default
- ✅ Opt-in gate for raw export enforced
- ✅ Dry-run preview mode operational
- ✅ No raw sessions in default examples

## [0.1.0] - 2025-12-21

### Summary
Initial scaffold implementation with mock Cascade, security layer, and local search.

### Added
- MCP server with 4 tools: `store_session_to_cascade`, `query_cascade_memories`, `retrieve_session_from_cascade`, `estimate_storage_cost`
- Security layer: Redaction patterns and AES-256-GCM encryption
- Storage layer: Mock Cascade (filesystem-backed) with content-addressed pointers
- Search layer: SQLite with FTS5 full-text search and BM25 ranking
- CASS adapter for session export
- Test suite with 35+ tests and 90-second smoke test
- CI/CD: GitHub Actions workflows for PR and main branch

### Security
- Redaction for API keys, emails, credit cards, phone numbers, etc.
- Client-side encryption with user-controlled keys (LUMERA_MEMORY_KEY env var)
- Fail-closed on secret detection (original v0.1.0 behavior)

### Development
- Python 3.10+ support
- Virtual environment setup scripts
- Black, isort, flake8 code quality tools
