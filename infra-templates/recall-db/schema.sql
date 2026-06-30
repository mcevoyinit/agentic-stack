-- recall-db schema — conversation/session index for cross-session recall.
-- Pure structure, zero data. Created empty by setup.py.
--
-- Designed to be filled by a background indexer that walks your Claude
-- Code transcript .jsonl files (~/.claude/projects/*/*.jsonl) and a
-- small MCP server (or the `recall` skill in claude/skills/recall) that
-- queries it. Neither the indexer nor the server ships here — write
-- your own against this schema, or point an existing one at it.

CREATE TABLE IF NOT EXISTS processed_files (
    file_path    TEXT PRIMARY KEY,
    file_mtime   REAL NOT NULL,
    file_size    INTEGER NOT NULL,
    processed_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    session_id   TEXT
);

CREATE TABLE IF NOT EXISTS sessions (
    session_id          TEXT PRIMARY KEY,
    project_slug        TEXT NOT NULL,
    project_name        TEXT NOT NULL,
    file_path           TEXT NOT NULL,
    is_subagent         INTEGER NOT NULL DEFAULT 0,
    parent_session_id   TEXT,
    agent_id            TEXT,
    start_time          TEXT,
    end_time            TEXT,
    summary              TEXT,
    custom_title         TEXT,
    model                TEXT,
    total_user_msgs      INTEGER DEFAULT 0,
    total_asst_msgs      INTEGER DEFAULT 0,
    total_input_tokens   INTEGER DEFAULT 0,
    total_output_tokens  INTEGER DEFAULT 0,
    cwd                  TEXT,
    git_branch           TEXT,
    version              TEXT
);
CREATE INDEX IF NOT EXISTS idx_sessions_project ON sessions(project_name);
CREATE INDEX IF NOT EXISTS idx_sessions_start   ON sessions(start_time);
CREATE INDEX IF NOT EXISTS idx_sessions_end     ON sessions(end_time);
CREATE INDEX IF NOT EXISTS idx_sessions_parent  ON sessions(parent_session_id);

CREATE TABLE IF NOT EXISTS messages (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id    TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    uuid          TEXT,
    parent_uuid   TEXT,
    role          TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
    content_text  TEXT NOT NULL,
    tool_names    TEXT,
    message_order INTEGER NOT NULL,
    timestamp     TEXT,
    model         TEXT,
    input_tokens  INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
CREATE INDEX IF NOT EXISTS idx_messages_ts      ON messages(timestamp);

CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
    content_text,
    content='messages',
    content_rowid='id',
    tokenize='porter unicode61'
);

CREATE TABLE IF NOT EXISTS session_topics (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    topic      TEXT NOT NULL,
    source     TEXT NOT NULL DEFAULT 'summary'
);
CREATE INDEX IF NOT EXISTS idx_topics_session ON session_topics(session_id);
CREATE INDEX IF NOT EXISTS idx_topics_topic   ON session_topics(topic);

-- Open threads / running questions surfaced across sessions
CREATE TABLE IF NOT EXISTS threads (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    title           TEXT NOT NULL,
    description     TEXT,
    topic_name      TEXT,
    project_slug    TEXT,
    status          TEXT NOT NULL DEFAULT 'open'
                    CHECK(status IN ('open','blocked','resolved','cancelled','superseded')),
    blocked_on      TEXT,
    first_session   TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    last_session    TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    superseded_by   INTEGER REFERENCES threads(id),
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    updated_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    expires_at      TEXT
);
CREATE INDEX IF NOT EXISTS idx_threads_status  ON threads(status);
CREATE INDEX IF NOT EXISTS idx_threads_topic   ON threads(topic_name);
CREATE INDEX IF NOT EXISTS idx_threads_project ON threads(project_slug);
CREATE INDEX IF NOT EXISTS idx_threads_updated ON threads(updated_at);

CREATE VIRTUAL TABLE IF NOT EXISTS threads_fts USING fts5(
    title, description, blocked_on,
    content='threads', content_rowid='id',
    tokenize='porter unicode61'
);

-- Durable decisions extracted from sessions, with reversibility tagging
CREATE TABLE IF NOT EXISTS decisions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    statement       TEXT NOT NULL,
    rationale       TEXT,
    reversibility   TEXT NOT NULL DEFAULT 'medium'
                    CHECK(reversibility IN ('easy','medium','hard','irreversible')),
    topic_name      TEXT,
    thread_id       INTEGER REFERENCES threads(id) ON DELETE SET NULL,
    source_session  TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    superseded_by   INTEGER REFERENCES decisions(id),
    promoted_to_kb  INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_decisions_topic   ON decisions(topic_name);
CREATE INDEX IF NOT EXISTS idx_decisions_thread  ON decisions(thread_id);
CREATE INDEX IF NOT EXISTS idx_decisions_session ON decisions(source_session);

CREATE VIRTUAL TABLE IF NOT EXISTS decisions_fts USING fts5(
    statement, rationale,
    content='decisions', content_rowid='id',
    tokenize='porter unicode61'
);

-- Two sessions touching the same cwd/file/topic at overlapping times
CREATE TABLE IF NOT EXISTS collisions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    kind            TEXT NOT NULL CHECK(kind IN ('cwd','file','topic')),
    overlap_value   TEXT NOT NULL,
    session_a       TEXT NOT NULL,
    session_b       TEXT NOT NULL,
    detected_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    cleared_at      TEXT,
    UNIQUE(kind, overlap_value, session_a, session_b)
);
CREATE INDEX IF NOT EXISTS idx_collisions_open ON collisions(cleared_at) WHERE cleared_at IS NULL;

CREATE TABLE IF NOT EXISTS metadata (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- NOTE: the source system this schema is derived from also supports an
-- optional semantic/vector search layer (sqlite-vec extension +
-- embeddings). That requires a native extension binary and an embedding
-- model and is intentionally NOT included here — FTS5 full-text search
-- (messages_fts / threads_fts / decisions_fts above) covers the same
-- use case without extra dependencies. Add vector search later if you
-- need it; see https://github.com/asg017/sqlite-vec.
