-- knowledge-base schema — structured topic dossiers (companies, people,
-- technologies, projects, concepts) built up across sessions.
-- Pure structure, zero data. Created empty by setup.py.
--
-- This is the backing store for the get_topic / add_insight /
-- list_topics / search_knowledge tools referenced by
-- claude/rules/kb-triggers.md and the claude/skills/kb skill. The
-- actual MCP server exposing those tools is not included — write a
-- thin server against this schema (any language; it's plain SQLite).

CREATE TABLE IF NOT EXISTS topics (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    category     TEXT NOT NULL DEFAULT 'general'
                 CHECK(category IN ('company','person','technology','project',
                                    'concept','protocol','tool','place','general')),
    status       TEXT NOT NULL DEFAULT 'active'
                 CHECK(status IN ('active','archived','superseded')),
    summary      TEXT,
    session_count INTEGER NOT NULL DEFAULT 0,
    last_seen    TEXT,
    created_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS aliases (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    alias    TEXT NOT NULL UNIQUE,
    topic_id INTEGER NOT NULL REFERENCES topics(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_aliases_topic ON aliases(topic_id);

CREATE TABLE IF NOT EXISTS insights (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id       INTEGER NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
    content        TEXT NOT NULL,
    source         TEXT NOT NULL DEFAULT 'manual'
                   CHECK(source IN ('manual','auto','ai_enrichment','heuristic')),
    source_session TEXT,
    confidence     REAL NOT NULL DEFAULT 1.0,
    superseded_by  INTEGER REFERENCES insights(id),
    created_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_insights_topic ON insights(topic_id);

CREATE TABLE IF NOT EXISTS documents (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id    INTEGER NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
    title       TEXT NOT NULL,
    doc_type    TEXT NOT NULL DEFAULT 'file',
    path_or_url TEXT NOT NULL,
    description TEXT,
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_documents_topic ON documents(topic_id);

CREATE TABLE IF NOT EXISTS timeline (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id    INTEGER NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
    event_date  TEXT NOT NULL,
    description TEXT NOT NULL,
    source      TEXT,
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);
CREATE INDEX IF NOT EXISTS idx_timeline_topic ON timeline(topic_id);
CREATE INDEX IF NOT EXISTS idx_timeline_date  ON timeline(event_date);

CREATE TABLE IF NOT EXISTS relationships (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    from_topic_id INTEGER NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
    to_topic_id   INTEGER NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
    relation_type TEXT NOT NULL DEFAULT 'related'
                  CHECK(relation_type IN ('related','part_of','competes_with',
                                          'depends_on','successor_of')),
    description   TEXT,
    created_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    UNIQUE(from_topic_id, to_topic_id, relation_type)
);
CREATE INDEX IF NOT EXISTS idx_rel_from ON relationships(from_topic_id);
CREATE INDEX IF NOT EXISTS idx_rel_to   ON relationships(to_topic_id);

CREATE TABLE IF NOT EXISTS topic_sessions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id   INTEGER NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
    session_id TEXT NOT NULL,
    relevance  REAL NOT NULL DEFAULT 1.0,
    UNIQUE(topic_id, session_id)
);
CREATE INDEX IF NOT EXISTS idx_ts_topic   ON topic_sessions(topic_id);
CREATE INDEX IF NOT EXISTS idx_ts_session ON topic_sessions(session_id);

CREATE TABLE IF NOT EXISTS metadata (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts USING fts5(
    content,
    topic_name,
    tokenize='porter unicode61'
);
