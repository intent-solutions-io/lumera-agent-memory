"""MCP Server for Lumera Agent Memory.

Exposes 4 tools:
1. store_session_to_cascade - Store session with redaction + encryption
2. query_cascade_memories - Search local index (never queries Cascade)
3. retrieve_session_from_cascade - Fetch and decrypt by pointer
4. estimate_storage_cost - Heuristic cost estimation
"""

import json
import hashlib
from typing import Any, Dict, List
from pathlib import Path

from mcp.server import Server
from mcp.types import Tool, TextContent

from .security import redact_session, encrypt_blob, decrypt_blob, RedactionError, EncryptionError
from .cascade import MockCascadeConnector, NotFoundError, ValidationError
from .index import MemoryIndex
from .adapters import CASSAdapter
from .enrich import generate_memory_card


# Initialize components
cascade = MockCascadeConnector()
index = MemoryIndex()
cass = CASSAdapter()

# Create MCP server
app = Server("lumera-agent-memory")


@app.list_tools()
async def list_tools() -> List[Tool]:
    """List available MCP tools."""
    return [
        Tool(
            name="store_session_to_cascade",
            description="Store session data to Cascade with redaction and encryption. "
            "Returns pointer for later retrieval. WARNING: Storage is immutable.",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Session ID to store (from CASS or custom)",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tags for categorization (optional)",
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Additional metadata (optional)",
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["mock", "live"],
                        "description": "Storage mode: mock (filesystem) or live (Cascade API)",
                        "default": "mock",
                    },
                },
                "required": ["session_id"],
            },
        ),
        Tool(
            name="query_memories",
            description="Query local index for memory pointers. "
            "CRITICAL: Does NOT query Cascade (local index only). "
            "Returns pointers for use with retrieve_session_from_cascade.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Free-text search query (optional)",
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Filter by tags (substring match)",
                    },
                    "time_range": {
                        "type": "object",
                        "properties": {
                            "start": {"type": "string", "description": "ISO 8601 start time"},
                            "end": {"type": "string", "description": "ISO 8601 end time"},
                        },
                        "description": "Filter by time range (optional)",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results (default: 10)",
                        "default": 10,
                    },
                },
            },
        ),
        Tool(
            name="retrieve_session_from_cascade",
            description="Retrieve and decrypt session data from Cascade by pointer.",
            inputSchema={
                "type": "object",
                "properties": {
                    "cascade_uri": {
                        "type": "string",
                        "description": "Cascade URI (cascade://...)",
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["mock", "live"],
                        "description": "Storage mode: mock (filesystem) or live (Cascade API)",
                        "default": "mock",
                    },
                },
                "required": ["cascade_uri"],
            },
        ),
        Tool(
            name="estimate_storage_cost",
            description="Estimate Cascade storage cost (heuristic calculation). "
            "Week 1: Mock data, not based on real pricing.",
            inputSchema={
                "type": "object",
                "properties": {
                    "bytes": {
                        "type": "integer",
                        "description": "Data size in bytes",
                    },
                    "redundancy": {
                        "type": "integer",
                        "description": "Replication factor (default: 3)",
                        "default": 3,
                    },
                },
                "required": ["bytes"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> List[TextContent]:
    """Handle tool calls."""

    if name == "store_session_to_cascade":
        return await _store_session(arguments)
    elif name == "query_memories":
        return await _query_memories(arguments)
    elif name == "retrieve_session_from_cascade":
        return await _retrieve_session(arguments)
    elif name == "estimate_storage_cost":
        return await _estimate_cost(arguments)
    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def _store_session(args: Dict[str, Any]) -> List[TextContent]:
    """Store session to Cascade with redaction + encryption."""
    try:
        session_id = args["session_id"]
        tags = args.get("tags", [])
        mode = args.get("mode", "mock")

        # Check live mode
        if mode == "live":
            return [
                TextContent(
                    type="text",
                    text=json.dumps({
                        "ok": False,
                        "error": "Live Cascade mode not yet implemented. Missing: CASCADE_API_ENDPOINT and CASCADE_API_KEY environment variables. Use mode=mock for now.",
                    }),
                )
            ]

        # Step 1: Export session from CASS (or fixture)
        session_data = cass.export_session(session_id)
        if session_data is None:
            return [
                TextContent(
                    type="text",
                    text=json.dumps({
                        "ok": False,
                        "error": f"Session not found: {session_id}",
                    }),
                )
            ]

        # Step 2: Redact (with report)
        try:
            redacted, redaction_report = redact_session(session_data)
        except RedactionError as e:
            return [
                TextContent(
                    type="text",
                    text=json.dumps({
                        "ok": False,
                        "error": f"Redaction failed (critical secrets detected): {str(e)}",
                    }),
                )
            ]

        # Step 3: Generate Memory Card
        memory_card = generate_memory_card(session_data)

        # Step 4: Serialize and encrypt
        plaintext = json.dumps(redacted).encode("utf-8")
        plaintext_sha256 = hashlib.sha256(plaintext).hexdigest()
        encrypted_blob = encrypt_blob(plaintext)
        ciphertext_sha256 = hashlib.sha256(encrypted_blob).hexdigest()

        # Step 5: Store in Cascade
        cascade_uri = cascade.put(encrypted_blob)

        # Step 6: Add to local index (with memory card metadata)
        index.add_memory(
            pointer=cascade_uri,
            content_hash=ciphertext_sha256,
            tags=tags,
            source_session_id=session_id,
            source_tool=session_data.get("tool_name", "unknown"),
            title=memory_card["title"],
            snippet=" | ".join(memory_card["summary_bullets"][:2]),  # First 2 bullets
            metadata={"memory_card": memory_card},
        )

        return [
            TextContent(
                type="text",
                text=json.dumps({
                    "ok": True,
                    "session_id": session_id,
                    "cascade_uri": cascade_uri,
                    "indexed": True,
                    "memory_card": memory_card,
                    "redaction": {
                        "rules_fired": redaction_report,
                    },
                    "crypto": {
                        "enc": "AES-256-GCM",
                        "key_id": "env:LUMERA_MEMORY_KEY",
                        "plaintext_sha256": plaintext_sha256,
                        "ciphertext_sha256": ciphertext_sha256,
                        "bytes": len(encrypted_blob),
                    },
                }),
            )
        ]

    except EncryptionError as e:
        return [
            TextContent(
                type="text",
                text=json.dumps({
                    "ok": False,
                    "error": f"Encryption failed: {str(e)}",
                }),
            )
        ]
    except Exception as e:
        return [
            TextContent(
                type="text",
                text=json.dumps({
                    "ok": False,
                    "error": f"Storage failed: {str(e)}",
                }),
            )
        ]


async def _query_memories(args: Dict[str, Any]) -> List[TextContent]:
    """Query local index for memory pointers."""
    try:
        query_text = args.get("query")
        tags = args.get("tags")
        time_range = args.get("time_range")
        limit = args.get("limit", 10)

        memories = index.query_memories(
            query=query_text,
            tags=tags,
            time_range=time_range,
            limit=limit
        )

        # Return hits with cascade_uri + metadata
        hits = [
            {
                "cass_session_id": m.get("source_session_id"),
                "cascade_uri": m["pointer"],
                "title": m.get("title", f"Session {m.get('source_session_id', 'unknown')}"),
                "snippet": m.get("snippet", m.get("source_tool", "")),
                "tags": m.get("tags", []),
                "created_at": m["created_at"],
                "score": m.get("score", 0),
            }
            for m in memories
        ]

        return [
            TextContent(
                type="text",
                text=json.dumps({
                    "ok": True,
                    "hits": hits,
                }),
            )
        ]

    except Exception as e:
        return [
            TextContent(
                type="text",
                text=json.dumps({
                    "ok": False,
                    "error": f"Query failed: {str(e)}",
                }),
            )
        ]


async def _retrieve_session(args: Dict[str, Any]) -> List[TextContent]:
    """Retrieve and decrypt session from Cascade."""
    try:
        cascade_uri = args["cascade_uri"]
        mode = args.get("mode", "mock")

        # Check live mode
        if mode == "live":
            return [
                TextContent(
                    type="text",
                    text=json.dumps({
                        "ok": False,
                        "error": "Live Cascade mode not yet implemented. Missing: CASCADE_API_ENDPOINT and CASCADE_API_KEY environment variables. Use mode=mock for now.",
                    }),
                )
            ]

        # Step 1: Fetch encrypted blob from Cascade
        try:
            encrypted_blob = cascade.get(cascade_uri)
        except NotFoundError:
            return [
                TextContent(
                    type="text",
                    text=json.dumps({
                        "ok": False,
                        "error": f"Cascade URI not found: {cascade_uri}",
                    }),
                )
            ]
        except ValidationError as e:
            return [
                TextContent(
                    type="text",
                    text=json.dumps({
                        "ok": False,
                        "error": f"Invalid Cascade URI: {str(e)}",
                    }),
                )
            ]

        # Step 2: Decrypt and verify
        try:
            plaintext = decrypt_blob(encrypted_blob)
            plaintext_sha256 = hashlib.sha256(plaintext).hexdigest()
            ciphertext_sha256 = hashlib.sha256(encrypted_blob).hexdigest()
            session_data = json.loads(plaintext.decode("utf-8"))
        except EncryptionError as e:
            return [
                TextContent(
                    type="text",
                    text=json.dumps({
                        "ok": False,
                        "error": f"Decryption failed: {str(e)}",
                    }),
                )
            ]

        # Step 3: Get memory card from index (if available)
        memory_metadata = index.get_memory_by_pointer(cascade_uri)
        memory_card = None
        if memory_metadata and "memory_card" in memory_metadata.get("metadata", {}):
            memory_card = memory_metadata["metadata"]["memory_card"]

        result = {
            "ok": True,
            "cascade_uri": cascade_uri,
            "session": session_data,
            "crypto": {
                "verified": True,
                "plaintext_sha256": plaintext_sha256,
                "ciphertext_sha256": ciphertext_sha256,
                "key_id": "env:LUMERA_MEMORY_KEY",
            },
        }

        if memory_card:
            result["memory_card"] = memory_card

        return [
            TextContent(
                type="text",
                text=json.dumps(result),
            )
        ]

    except Exception as e:
        return [
            TextContent(
                type="text",
                text=json.dumps({
                    "ok": False,
                    "error": f"Retrieval failed: {str(e)}",
                }),
            )
        ]


async def _estimate_cost(args: Dict[str, Any]) -> List[TextContent]:
    """Estimate storage cost (heuristic, mock pricing)."""
    try:
        bytes_count = args["bytes"]
        redundancy = args.get("redundancy", 3)

        # Mock pricing: $0.03 per GB per month storage + $0.01 per 10k requests
        gb = bytes_count / (1024 * 1024 * 1024)
        monthly_storage_usd = gb * 0.03 * redundancy
        estimated_request_usd = 0.001  # Assume ~100 requests per month

        return [
            TextContent(
                type="text",
                text=json.dumps({
                    "ok": True,
                    "bytes": bytes_count,
                    "gb": round(gb, 6),
                    "monthly_storage_usd": round(monthly_storage_usd, 6),
                    "estimated_request_usd": estimated_request_usd,
                    "total_estimated_usd": round(monthly_storage_usd + estimated_request_usd, 6),
                    "assumptions": {
                        "redundancy": redundancy,
                        "estimated_requests_per_month": 100,
                        "note": "Heuristic estimate. Not based on real Cascade pricing.",
                    },
                }),
            )
        ]

    except Exception as e:
        return [
            TextContent(
                type="text",
                text=json.dumps({
                    "ok": False,
                    "error": f"Estimation failed: {str(e)}",
                }),
            )
        ]


if __name__ == "__main__":
    import asyncio
    from mcp.server.stdio import stdio_server

    async def main():
        async with stdio_server() as (read_stream, write_stream):
            await app.run(read_stream, write_stream, app.create_initialization_options())

    asyncio.run(main())
