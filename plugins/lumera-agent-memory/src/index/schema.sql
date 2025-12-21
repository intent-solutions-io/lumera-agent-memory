-- Lumera Agent Memory: Local SQLite Index Schema
-- Version: 0.1.0
--
-- CRITICAL: This index stores POINTERS ONLY (never blob content).
-- Query this index to find what to retrieve, then fetch from Cascade.

CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pointer TEXT UNIQUE NOT NULL,
    content_hash TEXT NOT NULL,
    tags_json TEXT,
    created_at TEXT NOT NULL,
    schema_version TEXT DEFAULT '0.1.0',
    source_session_id TEXT,
    source_tool TEXT
);

-- Indexes for fast queries
CREATE INDEX IF NOT EXISTS idx_tags ON memories(tags_json);
CREATE INDEX IF NOT EXISTS idx_created ON memories(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_session ON memories(source_session_id);
CREATE INDEX IF NOT EXISTS idx_content_hash ON memories(content_hash);

-- Metadata table for schema migrations
CREATE TABLE IF NOT EXISTS schema_metadata (
    version TEXT PRIMARY KEY,
    applied_at TEXT NOT NULL
);

-- Insert initial schema version
INSERT OR IGNORE INTO schema_metadata (version, applied_at)
VALUES ('0.1.0', datetime('now'));
