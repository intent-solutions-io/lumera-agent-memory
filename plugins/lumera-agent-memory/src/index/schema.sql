-- Lumera Agent Memory: Local SQLite Index Schema with FTS5
-- Version: 0.2.0
--
-- CRITICAL: This index stores POINTERS ONLY (never blob content).
-- Query this index to find what to retrieve, then fetch from Cascade.

CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pointer TEXT UNIQUE NOT NULL,
    content_hash TEXT NOT NULL,
    tags_json TEXT,
    created_at TEXT NOT NULL,
    schema_version TEXT DEFAULT '0.2.0',
    source_session_id TEXT,
    source_tool TEXT,
    title TEXT,
    snippet TEXT,
    metadata_json TEXT
);

-- Indexes for fast queries
CREATE INDEX IF NOT EXISTS idx_tags ON memories(tags_json);
CREATE INDEX IF NOT EXISTS idx_created ON memories(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_session ON memories(source_session_id);
CREATE INDEX IF NOT EXISTS idx_content_hash ON memories(content_hash);

-- FTS5 virtual table for full-text search
CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
    title,
    snippet,
    source_tool,
    tags_json,
    content='memories',
    content_rowid='id',
    tokenize='porter unicode61'
);

-- Triggers to keep FTS5 in sync
CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
  INSERT INTO memories_fts(rowid, title, snippet, source_tool, tags_json)
  VALUES (new.id, new.title, new.snippet, new.source_tool, new.tags_json);
END;

CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
  INSERT INTO memories_fts(memories_fts, rowid, title, snippet, source_tool, tags_json)
  VALUES('delete', old.id, old.title, old.snippet, old.source_tool, old.tags_json);
END;

CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
  INSERT INTO memories_fts(memories_fts, rowid, title, snippet, source_tool, tags_json)
  VALUES('delete', old.id, old.title, old.snippet, old.source_tool, old.tags_json);
  INSERT INTO memories_fts(rowid, title, snippet, source_tool, tags_json)
  VALUES (new.id, new.title, new.snippet, new.source_tool, new.tags_json);
END;

-- Metadata table for schema migrations
CREATE TABLE IF NOT EXISTS schema_metadata (
    version TEXT PRIMARY KEY,
    applied_at TEXT NOT NULL
);

-- Insert schema version
INSERT OR IGNORE INTO schema_metadata (version, applied_at)
VALUES ('0.2.0', datetime('now'));
