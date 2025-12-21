"""Local SQLite index with FTS5 for fast memory search.

CRITICAL: This index stores POINTERS only (never blob content).
Queries return pointers for retrieval from Cascade.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional


class MemoryIndex:
    """SQLite-based local memory index with FTS5 full-text search."""

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
        artifact_type: str = "artifact_only",
        tags: List[str] = None,
        source_session_id: str = None,
        source_tool: str = None,
        title: str = None,
        snippet: str = None,
        metadata: Dict[str, Any] = None,
    ) -> int:
        """Add memory pointer to index.

        Args:
            pointer: Cascade pointer (cascade://...)
            content_hash: SHA-256 hash of encrypted blob
            artifact_type: "artifact_only" or "raw_plus_artifact"
            tags: List of tags for categorization
            source_session_id: Original session ID (from CASS)
            source_tool: Tool that generated this memory
            title: Memory title (for search/display)
            snippet: Short summary/preview (for search/display)
            metadata: Additional metadata dict

        Returns:
            Memory ID (primary key)

        Raises:
            sqlite3.IntegrityError: If pointer already exists
        """
        tags_json = json.dumps(tags or [])
        metadata_json = json.dumps(metadata or {})
        created_at = datetime.now().isoformat()

        cursor = self.conn.execute(
            """
            INSERT INTO memories (pointer, content_hash, artifact_type, tags_json, created_at,
                                  source_session_id, source_tool, title, snippet, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (pointer, content_hash, artifact_type, tags_json, created_at, source_session_id, source_tool, title, snippet, metadata_json),
        )
        self.conn.commit()
        return cursor.lastrowid

    def query_memories(
        self,
        query: str = None,
        tags: List[str] = None,
        time_range: Dict[str, str] = None,
        limit: int = 10,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Query index for memory pointers with FTS5 full-text search.

        Args:
            query: Free-text search query (uses FTS5 with BM25 ranking)
            tags: Filter by tags (substring match on any tag)
            time_range: Filter by time range {"start": ISO8601, "end": ISO8601}
            limit: Max results to return
            offset: Number of results to skip

        Returns:
            List of memory dicts with keys: pointer, tags, created_at, title, snippet, score, etc.
        """
        if query:
            # FTS5 query with BM25 ranking
            sql = """
                SELECT m.*, bm25(memories_fts) AS score
                FROM memories m
                JOIN memories_fts ON memories_fts.rowid = m.id
                WHERE memories_fts MATCH ?
            """
            params = [query]
        else:
            # No FTS query - just filter and sort by recency
            sql = "SELECT *, 0 AS score FROM memories WHERE 1=1"
            params = []

        # Add tag filtering
        if tags:
            tag_conditions = []
            for tag in tags:
                tag_conditions.append("tags_json LIKE ?")
                params.append(f"%{tag}%")
            sql += " AND (" + " OR ".join(tag_conditions) + ")"

        # Add time range filtering
        if time_range:
            if time_range.get("start"):
                sql += " AND created_at >= ?"
                params.append(time_range["start"])
            if time_range.get("end"):
                sql += " AND created_at <= ?"
                params.append(time_range["end"])

        # Order by score (if FTS) or recency
        if query:
            sql += " ORDER BY score ASC, created_at DESC"  # BM25 returns negative scores, lower is better
        else:
            sql += " ORDER BY created_at DESC"

        sql += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor = self.conn.execute(sql, params)
        rows = cursor.fetchall()

        # Convert to dicts and parse JSON fields
        results = []
        for row in rows:
            memory = dict(row)
            memory["tags"] = json.loads(memory["tags_json"])
            memory["metadata"] = json.loads(memory.get("metadata_json", "{}"))
            del memory["tags_json"]
            if "metadata_json" in memory:
                del memory["metadata_json"]
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
        memory["metadata"] = json.loads(memory.get("metadata_json", "{}"))
        del memory["tags_json"]
        if "metadata_json" in memory:
            del memory["metadata_json"]
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
