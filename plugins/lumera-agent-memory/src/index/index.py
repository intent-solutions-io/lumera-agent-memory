"""Local SQLite index for fast memory search.

CRITICAL: This index stores POINTERS only (never blob content).
Queries return pointers for retrieval from Cascade.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional


class MemoryIndex:
    """SQLite-based local memory index."""

    def __init__(self, db_path: Path = None):
        """Initialize index.

        Args:
            db_path: Path to SQLite database (default: .cache/memory_index.db)
        """
        if db_path is None:
            db_path = Path(".cache/memory_index.db")

        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row  # Enable dict-like access
        self._initialize_schema()

    def _initialize_schema(self):
        """Create tables and indexes if not exist."""
        schema_path = Path(__file__).parent / "schema.sql"
        schema = schema_path.read_text()
        self.conn.executescript(schema)
        self.conn.commit()

    def add_memory(
        self,
        pointer: str,
        content_hash: str,
        tags: List[str] = None,
        source_session_id: str = None,
        source_tool: str = None,
    ) -> int:
        """Add memory pointer to index.

        Args:
            pointer: Cascade pointer (cascade://...)
            content_hash: SHA-256 hash of encrypted blob
            tags: List of tags for categorization
            source_session_id: Original session ID (from CASS)
            source_tool: Tool that generated this memory

        Returns:
            Memory ID (primary key)

        Raises:
            sqlite3.IntegrityError: If pointer already exists
        """
        tags_json = json.dumps(tags or [])
        created_at = datetime.utcnow().isoformat()

        cursor = self.conn.execute(
            """
            INSERT INTO memories (pointer, content_hash, tags_json, created_at,
                                  source_session_id, source_tool)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (pointer, content_hash, tags_json, created_at, source_session_id, source_tool),
        )
        self.conn.commit()
        return cursor.lastrowid

    def query_memories(
        self,
        tags: List[str] = None,
        session_id: str = None,
        limit: int = 10,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Query index for memory pointers.

        Args:
            tags: Filter by tags (substring match on any tag)
            session_id: Filter by source session ID
            limit: Max results to return
            offset: Number of results to skip

        Returns:
            List of memory dicts with keys: pointer, tags, created_at, etc.
        """
        query = "SELECT * FROM memories WHERE 1=1"
        params = []

        if tags:
            # Substring match on tags_json (simple search)
            tag_conditions = []
            for tag in tags:
                tag_conditions.append("tags_json LIKE ?")
                params.append(f"%{tag}%")
            query += " AND (" + " OR ".join(tag_conditions) + ")"

        if session_id:
            query += " AND source_session_id = ?"
            params.append(session_id)

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor = self.conn.execute(query, params)
        rows = cursor.fetchall()

        # Convert to dicts and parse tags_json
        results = []
        for row in rows:
            memory = dict(row)
            memory["tags"] = json.loads(memory["tags_json"])
            del memory["tags_json"]  # Remove raw JSON field
            results.append(memory)

        return results

    def get_memory_by_pointer(self, pointer: str) -> Optional[Dict[str, Any]]:
        """Get memory metadata by pointer.

        Args:
            pointer: Cascade pointer

        Returns:
            Memory dict or None if not found
        """
        cursor = self.conn.execute("SELECT * FROM memories WHERE pointer = ?", (pointer,))
        row = cursor.fetchone()

        if row is None:
            return None

        memory = dict(row)
        memory["tags"] = json.loads(memory["tags_json"])
        del memory["tags_json"]
        return memory

    def delete_memory(self, pointer: str) -> bool:
        """Remove memory from index (blob remains in Cascade).

        Args:
            pointer: Cascade pointer

        Returns:
            True if deleted, False if not found
        """
        cursor = self.conn.execute("DELETE FROM memories WHERE pointer = ?", (pointer,))
        self.conn.commit()
        return cursor.rowcount > 0

    def count_memories(self, tags: List[str] = None) -> int:
        """Count memories matching filters.

        Args:
            tags: Filter by tags

        Returns:
            Count of matching memories
        """
        query = "SELECT COUNT(*) FROM memories WHERE 1=1"
        params = []

        if tags:
            tag_conditions = []
            for tag in tags:
                tag_conditions.append("tags_json LIKE ?")
                params.append(f"%{tag}%")
            query += " AND (" + " OR ".join(tag_conditions) + ")"

        cursor = self.conn.execute(query, params)
        return cursor.fetchone()[0]

    def close(self):
        """Close database connection."""
        self.conn.close()
