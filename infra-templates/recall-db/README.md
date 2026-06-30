# recall-db

A SQLite index over your own Claude Code transcripts, so a `recall`
skill or MCP server can answer "what did we discuss about X" without
re-reading every `.jsonl` file in `~/.claude/projects/`.

This template ships the **schema only** — no data, no indexer, no
server. You write (or point an existing one at) the two missing
pieces:

1. **An indexer** — walks `~/.claude/projects/*/*.jsonl`, parses each
   transcript, and inserts rows into `sessions` / `messages` /
   `session_topics`. Track what's already processed in
   `processed_files` so re-runs are incremental.
2. **A query layer** — the `claude/skills/recall` skill in this bundle
   expects to be able to full-text search messages and list/filter
   sessions. Wire it to either direct SQLite queries or an MCP server
   you stand up in front of this db.

## Install

```bash
python3 infra-templates/recall-db/setup.py
```

Creates `~/.claude-recall/conversations.db` (or `$RECALL_DB`) with the
full schema: `sessions`, `messages` (+ `messages_fts` full-text
index), `session_topics`, `threads`, `decisions`, `collisions`,
`metadata`. See `schema.sql` for the exact DDL and column comments.

## Suggested query patterns

```sql
-- full-text search across all messages
SELECT s.project_name, s.start_time, m.content_text
FROM messages_fts f
JOIN messages m ON m.id = f.rowid
JOIN sessions s ON s.session_id = m.session_id
WHERE messages_fts MATCH 'your search terms'
ORDER BY m.timestamp DESC
LIMIT 20;

-- recent sessions in a project
SELECT session_id, summary, start_time, total_user_msgs
FROM sessions
WHERE project_name = 'my-project'
ORDER BY start_time DESC
LIMIT 10;

-- open threads (running questions) across all projects
SELECT title, status, blocked_on, updated_at
FROM threads
WHERE status IN ('open', 'blocked')
ORDER BY updated_at DESC;
```

## Why FTS5 and not vector search

The schema uses SQLite's built-in FTS5 (full-text search) rather than
embeddings/vector search, so it runs with zero extra dependencies.
If you want semantic search later, add the `sqlite-vec` extension and
an embedding pipeline on top of this — the relational schema doesn't
need to change.

<!-- CUSTOMISE: nothing to strip here, this ships empty. Just point
     your own indexer/server at the db path you chose. -->
