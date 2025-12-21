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
                },
                "required": ["session_id"],
            },
        ),
        Tool(
            name="query_cascade_memories",
            description="Query local index for memory pointers. "
            "CRITICAL: Does NOT query Cascade (local index only). "
            "Returns pointers for use with retrieve_session_from_cascade.",
            inputSchema={
                "type": "object",
                "properties": {
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Filter by tags (substring match)",
                    },
                    "session_id": {
                        "type": "string",
                        "description": "Filter by source session ID (optional)",
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
                    "pointer": {
                        "type": "string",
                        "description": "Cascade pointer (cascade://...)",
                    },
                },
                "required": ["pointer"],
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
    elif name == "query_cascade_memories":
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

        # Step 1: Export session from CASS (or fixture)
        session_data = cass.export_session(session_id)
        if session_data is None:
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "success": False,
                            "error": f"Session not found: {session_id}",
                        }
                    ),
                )
            ]

        # Step 2: Redact (fail-closed)
        try:
            redacted = redact_session(session_data)
        except RedactionError as e:
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "success": False,
                            "error": f"Redaction failed: {str(e)}",
                        }
                    ),
                )
            ]

        # Step 3: Serialize and encrypt
        plaintext = json.dumps(redacted).encode("utf-8")
        encrypted_blob = encrypt_blob(plaintext)

        # Step 4: Store in Cascade
        pointer = cascade.put(encrypted_blob)

        # Step 5: Compute content hash for index
        content_hash = hashlib.sha256(encrypted_blob).hexdigest()

        # Step 6: Add to local index
        index.add_memory(
            pointer=pointer,
            content_hash=content_hash,
            tags=tags,
            source_session_id=session_id,
            source_tool=session_data.get("tool_name", "unknown"),
        )

        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "success": True,
                        "pointer": pointer,
                        "content_hash": content_hash,
                        "indexed": True,
                    }
                ),
            )
        ]

    except EncryptionError as e:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "success": False,
                        "error": f"Encryption failed: {str(e)}",
                    }
                ),
            )
        ]
    except Exception as e:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "success": False,
                        "error": f"Storage failed: {str(e)}",
                    }
                ),
            )
        ]


async def _query_memories(args: Dict[str, Any]) -> List[TextContent]:
    """Query local index for memory pointers."""
    try:
        tags = args.get("tags")
        session_id = args.get("session_id")
        limit = args.get("limit", 10)

        memories = index.query_memories(tags=tags, session_id=session_id, limit=limit)

        # Return only pointer + metadata (no blob content)
        results = [
            {
                "pointer": m["pointer"],
                "tags": m["tags"],
                "created_at": m["created_at"],
                "source_session_id": m.get("source_session_id"),
                "source_tool": m.get("source_tool"),
            }
            for m in memories
        ]

        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "success": True,
                        "memories": results,
                        "count": len(results),
                    }
                ),
            )
        ]

    except Exception as e:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "success": False,
                        "error": f"Query failed: {str(e)}",
                    }
                ),
            )
        ]


async def _retrieve_session(args: Dict[str, Any]) -> List[TextContent]:
    """Retrieve and decrypt session from Cascade."""
    try:
        pointer = args["pointer"]

        # Step 1: Fetch encrypted blob from Cascade
        try:
            encrypted_blob = cascade.get(pointer)
        except NotFoundError:
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "success": False,
                            "error": f"Pointer not found: {pointer}",
                        }
                    ),
                )
            ]
        except ValidationError as e:
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "success": False,
                            "error": f"Invalid pointer: {str(e)}",
                        }
                    ),
                )
            ]

        # Step 2: Decrypt blob
        try:
            plaintext = decrypt_blob(encrypted_blob)
            session_data = json.loads(plaintext.decode("utf-8"))
        except EncryptionError as e:
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "success": False,
                            "error": f"Decryption failed: {str(e)}",
                        }
                    ),
                )
            ]

        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "success": True,
                        "session_data": session_data,
                    }
                ),
            )
        ]

    except Exception as e:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "success": False,
                        "error": f"Retrieval failed: {str(e)}",
                    }
                ),
            )
        ]


async def _estimate_cost(args: Dict[str, Any]) -> List[TextContent]:
    """Estimate storage cost (heuristic, Week 1 mock)."""
    try:
        bytes_count = args["bytes"]
        redundancy = args.get("redundancy", 3)

        # Mock pricing: $0.00003 per KB per month with redundancy
        kb = bytes_count / 1024
        monthly_cost = kb * 0.00003 * redundancy

        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "success": True,
                        "estimated_cost": round(monthly_cost, 6),
                        "currency": "USD",
                        "period": "monthly",
                        "disclaimer": "Week 1 heuristic estimate, not based on real Cascade pricing",
                    }
                ),
            )
        ]

    except Exception as e:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "success": False,
                        "error": f"Estimation failed: {str(e)}",
                    }
                ),
            )
        ]


if __name__ == "__main__":
    import asyncio
    from mcp.server.stdio import stdio_server

    async def main():
        async with stdio_server() as (read_stream, write_stream):
            await app.run(read_stream, write_stream, app.create_initialization_options())

    asyncio.run(main())
