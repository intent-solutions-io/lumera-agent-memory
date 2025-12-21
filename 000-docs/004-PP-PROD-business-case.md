# Business Case: Lumera Agent Memory

## Executive Summary

**Lumera Agent Memory** bridges Jeff Emanuel's CASS (Coding Agent Session Storage) memory system to Lumera Cascade, creating a hybrid architecture where:
- Fast local search queries execute against a SQLite index
- Encrypted session blobs persist durably in Cascade storage
- Agents gain procedural memory without vendor lock-in

This enables coding agents to learn from past sessions across projects while maintaining data sovereignty through client-side encryption.

## Problem Statement

Current agent memory systems face three core challenges:

1. **Ephemeral Context**: Each coding session starts fresh with no institutional memory
2. **Vendor Lock-In**: Cloud-based memory systems trap user data
3. **Security Exposure**: Unencrypted session logs leak sensitive code/credentials

## Proposed Solution

A dual-tier memory architecture:

**Local Tier (Fast)**:
- SQLite index with pointers, tags, metadata
- CASS integration for rules/playbook/diary extraction
- Query responses in <100ms

**Remote Tier (Durable)**:
- Encrypted blobs stored in Lumera Cascade
- Content-addressed storage (deterministic pointers)
- Retrieval on-demand via pointer lookup

**Key Principle**: Search NEVER queries Cascade. Only local index returns pointers for retrieval.

## Target Users

1. **Individual Developers**: Using Claude Code + CASS locally
2. **Enterprise Teams**: Shared memory pools with RBAC (future)
3. **Jeff Emanuel's Ecosystem**: Native integration with cass_memory_system

## Success Metrics

| Metric | Target (Week 1) | Target (Production) |
|--------|-----------------|---------------------|
| Query latency | <100ms | <50ms |
| Store latency | <5s (mock) | <2s (real Cascade) |
| Storage cost | $0 (mock) | <$0.01/GB/month |
| Encryption overhead | <10% | <5% |
| CI test duration | <90s | <90s (strict) |

## Non-Goals (Week 1)

- ❌ Cascade search/indexing (local index only)
- ❌ Live Cascade API integration (filesystem mock)
- ❌ Multi-user RBAC
- ❌ Cross-agent collaboration features

## Investment & ROI

**Week 1 Deliverable**: Fully tested scaffold with:
- 4 working MCP tools
- 90-second CI smoke test
- Security-first architecture (fail-closed redaction + encryption)

**Timeline**: 1 week for scaffold → 2 weeks for live Cascade integration

**Value**: Transforms agent memory from "per-session" to "permanent institutional knowledge"
