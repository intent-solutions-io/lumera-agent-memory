# Threat Model: Lumera Agent Memory

**Version**: 0.1.0
**Last Updated**: 2025-12-20

---

## Assets

| Asset | Value | Owner |
|-------|-------|-------|
| **Session Data** | Contains code, commands, decisions | User (developer) |
| **Encryption Keys** | Protects all stored data | User (via env var) |
| **Pointers** | Reference to encrypted blobs | System |
| **Local Index** | Metadata for fast search | System |

---

## Threat Actors

| Actor | Motivation | Capability |
|-------|-----------|------------|
| **Malicious Insider** | Data exfiltration, sabotage | High (code access) |
| **External Attacker** | Credential theft, IP theft | Medium (network access) |
| **Accidental Leakage** | Commits secrets to git | Low (human error) |

---

## Threat Analysis

### T1: Secret Leakage in Stored Sessions

**Scenario**: User stores session containing API keys, AWS credentials, or SSH keys.

**Impact**: CRITICAL - Credential compromise, unauthorized access

**Mitigations**:
1. **Fail-Closed Redaction** (Primary Defense)
   - Regex detection for: API keys, AWS keys, SSH keys, emails, credit cards
   - If ANY secret detected → abort storage with error
   - Test: `test_redaction_fails_on_api_key()` proves fail-closed

2. **Allowlist Approach**
   - Only persist known-safe fields (`session_id`, `timestamp`, `summary`, `tags`)
   - Reject all other fields by default

3. **User Education**
   - CLAUDE.md warns: "Never store sessions with secrets"
   - Error messages guide users to `cm` cleanup commands

**Residual Risk**: LOW (fail-closed design prevents storage)

### T2: Encryption Key Compromise

**Scenario**: `LUMERA_MEMORY_KEY` exposed via process listing, logs, or commits.

**Impact**: HIGH - All stored sessions decryptable

**Mitigations**:
1. **Never Log Keys**
   - Audit all logging calls to exclude `LUMERA_MEMORY_KEY`
   - Environment variables never appear in debug output

2. **Gitignore Enforcement**
   - `.env` and `.env.*` in `.gitignore`
   - Pre-commit hook scans for `LUMERA_MEMORY_KEY=` patterns (future)

3. **Key Rotation Process**
   - Document: "To rotate keys, decrypt all blobs with old key, re-encrypt with new key"
   - Script: `scripts/rotate_keys.py` (future)

4. **Environment Isolation**
   - Recommend: `direnv` for per-project key management
   - Never use global env vars for production keys

**Residual Risk**: MEDIUM (depends on user key hygiene)

### T3: Pointer Enumeration Attack

**Scenario**: Attacker guesses content hashes to retrieve arbitrary sessions.

**Impact**: LOW (blobs still encrypted, requires key)

**Mitigations**:
1. **Encryption Requirement**
   - Even if pointer leaked, blob is encrypted at rest
   - No plaintext available without `LUMERA_MEMORY_KEY`

2. **SHA-256 Hash Space**
   - 2^256 possible pointers = infeasible to brute force

3. **Access Control** (future)
   - Cascade API enforces user-based permissions
   - Pointers scoped to authenticated users

**Residual Risk**: VERY LOW (encryption provides defense-in-depth)

### T4: Local Index SQL Injection

**Scenario**: Malicious tags or query strings exploit SQL injection.

**Impact**: MEDIUM - Database corruption, unauthorized reads

**Mitigations**:
1. **Parameterized Queries**
   - All SQL uses `cursor.execute(query, params)` syntax
   - Never string interpolation for user input

2. **Input Validation**
   - Tags: alphanumeric + hyphens/underscores only (`[a-zA-Z0-9_-]+`)
   - Query strings: sanitized via safe substring matching

3. **Read-Only for Queries**
   - `query_cascade_memories` uses SELECT only
   - No DELETE/UPDATE exposed via MCP tools

**Residual Risk**: VERY LOW (parameterized queries prevent injection)

### T5: Mock Cascade Path Traversal

**Scenario**: Malicious pointer like `cascade://../../../etc/passwd` reads arbitrary files.

**Impact**: HIGH - File system access outside cache dir

**Mitigations**:
1. **Pointer Validation**
   - Only accept pointers matching `^cascade://[a-f0-9]{64}$`
   - Reject any `..`, `/`, or `\` characters

2. **Path Canonicalization**
   - Resolve pointer to absolute path, verify it starts with `.cache/cascade-mock/`
   - Use `Path.resolve()` to prevent symlink attacks

3. **Filesystem Jail**
   - Mock connector only accesses `.cache/cascade-mock/`
   - Read/write operations constrained to cache dir

**Residual Risk**: VERY LOW (strict pointer validation)

### T6: Immutable Storage Hazard

**Scenario**: User stores sensitive data, later wants it deleted, but Cascade is immutable.

**Impact**: MEDIUM - Cannot retract leaked secrets

**Mitigations**:
1. **Fail-Closed Redaction** (Primary Defense)
   - Prevent storage of secrets in the first place
   - Immutability only applies to safe, redacted data

2. **User Warnings**
   - PRD states: "Cascade storage is immutable"
   - Tool docstrings warn: "Cannot delete after storage"

3. **Local Index Deletion**
   - Provide `delete_memory_pointer(pointer)` tool (future)
   - Removes index entry (blob remains in Cascade, but unlinkable)

4. **Encryption Layer**
   - Even if blob is immutable, losing key = data is unrecoverable
   - Key rotation makes old blobs inaccessible

**Residual Risk**: LOW (fail-closed prevents storage, encryption adds defense)

---

## Attack Tree

```
┌─────────────────────────────────────────┐
│  Goal: Exfiltrate User Session Data    │
└───────────────┬─────────────────────────┘
                │
        ┌───────┴────────┐
        │                │
        ▼                ▼
 ┌─────────────┐   ┌──────────────────┐
 │ Steal Key   │   │ Bypass Redaction │
 │ (T2)        │   │ (T1)             │
 └──────┬──────┘   └─────────┬────────┘
        │                    │
   [MEDIUM]             [BLOCKED]
     Risk               (fail-closed)
```

---

## Security Testing Requirements

| Test | Purpose | Expected Result |
|------|---------|-----------------|
| `test_redaction_fails_on_api_key()` | Verify fail-closed | RedactionError raised |
| `test_redaction_fails_on_aws_key()` | Verify AWS credential detection | RedactionError raised |
| `test_pointer_validation_rejects_traversal()` | Prevent path traversal | ValidationError raised |
| `test_sql_injection_in_tags()` | Prevent SQL injection | Query returns empty or errors |
| `test_encryption_roundtrip()` | Verify encrypt/decrypt | Plaintext matches original |
| `test_key_not_logged()` | Audit log output | Key never appears in logs |

---

## Compliance Considerations

| Regulation | Requirement | Implementation |
|------------|-------------|----------------|
| **GDPR** | Data minimization | Redaction removes PII (emails) |
| **GDPR** | Right to erasure | Local index deletion (blob immutable) |
| **SOC 2** | Encryption at rest | AES-256-GCM for all blobs |
| **SOC 2** | Access logging | Future: Cascade API audit logs |

---

## Incident Response Plan

### Scenario: Encryption Key Leaked

**Detection**: User reports key committed to git or posted publicly

**Response**:
1. Immediately rotate key (set new `LUMERA_MEMORY_KEY`)
2. Re-encrypt all blobs with new key using `scripts/rotate_keys.py`
3. Invalidate old pointers in local index (update schema_version)
4. Audit: Determine if any blobs were accessed with old key

**Prevention**: Pre-commit hooks scanning for `LUMERA_MEMORY_KEY=` patterns

### Scenario: Secret Stored Despite Redaction

**Detection**: User reports sensitive data retrieved from memory

**Response**:
1. Identify failing redaction pattern (e.g., custom API key format)
2. Add pattern to `redact.py` regex rules
3. Run `audit_all_memories()` to scan existing index for violations
4. Provide `delete_memory_pointer()` tool to remove from index

**Prevention**: Expand regex coverage, community-contributed patterns

---

## Security Design Principles

1. **Fail Closed**: On ANY doubt, abort storage
2. **Defense in Depth**: Redaction + Encryption + Validation
3. **User Sovereignty**: Keys never leave user control
4. **Immutability Awareness**: Warn users before storage
5. **Auditability**: All operations logged (future)

---

**Next Review**: After Week 1 implementation complete
