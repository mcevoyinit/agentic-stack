# knowledge-base

A SQLite-backed topic dossier system. Companies, people, technologies,
projects, concepts — each gets a `topics` row with aliases, freeform
`insights`, sourced `documents`, a `timeline`, and `relationships` to
other topics. `claude/rules/kb-triggers.md` wires Claude to consult it
before answering any "what do you know about X" question, and
`claude/skills/kb` is the query-side skill.

This template ships the **schema only** — no data, no server. Write a
thin MCP server (or even a CLI Claude can shell out to) exposing these
four operations against the schema below:

- `get_topic(name)` — resolve aliases, return topic + insights +
  documents + timeline + relationships + linked sessions
- `add_insight(topic, content, source)` — append a new insight row
  (creates the topic if it doesn't exist)
- `list_topics(category=None)` — browse by category
- `search_knowledge(query)` — full-text search over `knowledge_fts`

## Install

```bash
python3 infra-templates/knowledge-base/setup.py
```

Creates `~/.claude-knowledge/knowledge.db` (or `$KNOWLEDGE_DB`) with
the full schema: `topics`, `aliases`, `insights`, `documents`,
`timeline`, `relationships`, `topic_sessions`, `metadata`,
`knowledge_fts`. See `schema.sql` for exact DDL.

## Example get_topic query

```sql
SELECT t.*, GROUP_CONCAT(a.alias) AS aliases
FROM topics t
LEFT JOIN aliases a ON a.topic_id = t.id
WHERE t.name = ? OR a.alias = ?
GROUP BY t.id;

SELECT content, source, confidence, created_at
FROM insights
WHERE topic_id = ? AND superseded_by IS NULL
ORDER BY created_at DESC;
```

## Populating it

Two realistic paths:
1. **Manual** — `add_insight` calls as you work, the same way the
   `kb-triggers.md` rule expects Claude to call them when you say
   "remember that...".
2. **Batch ingest** — write your own ingestion script that reads
   source documents (notes, call transcripts, research) and populates
   `topics`/`insights`/`documents` in bulk. Not included here — the
   ingestion logic is highly specific to what you're tracking.

<!-- CUSTOMISE: nothing to strip, ships empty. Bring your own server
     and ingestion pipeline. -->
