---
name: kb
description: |
  Query the structured knowledge base for instant topic dossiers.
  Returns summaries, insights, documents, timeline, relationships,
  and linked sessions for any entity (person, company, technology, project).
  Trigger: "kb", "knowledge base", "what do I know about", "dossier on".
---

# Knowledge Base

You have access to a structured knowledge base via the `knowledge-base` MCP
server. Use these tools to query and update topic knowledge.

> Setup note: the knowledge base ships EMPTY. The install script creates an
> empty SQLite DB and registers the MCP server; topics accrue over time as
> you use it (a stop hook populates after each session). All topic names in
> this file are generic placeholders, not real data.

## Available MCP Tools

- `mcp__knowledge-base__get_topic` — Full dossier on a topic (summary, insights, docs, timeline, relationships, sessions)
- `mcp__knowledge-base__list_topics` — Browse topics by category or status
- `mcp__knowledge-base__search_knowledge` — FTS5 search across all insights and summaries (falls back to the conversation index)
- `mcp__knowledge-base__get_topic_history` — Timeline events + session history for a topic
- `mcp__knowledge-base__add_insight` — Persist a new insight about a topic
- `mcp__knowledge-base__update_topic` — Update topic metadata or add aliases
- `mcp__knowledge-base__link_topics` — Create typed relationships between topics
- `mcp__knowledge-base__add_event` — Add a timeline event

## Workflow

1. **Parse the user's query**:
   - Topic name → `get_topic`
   - "list companies" / "list protocols" → `list_topics(category=...)`
   - Search terms → `search_knowledge`
   - "history of X" / "timeline of X" → `get_topic_history`
   - "remember that..." / "note that..." → `add_insight`

2. **Present the dossier clearly**:
   - Lead with summary
   - Show key insights as bullet points
   - List related topics and relationships
   - Show linked sessions if relevant
   - Mention documents/file paths if found

3. **Offer follow-ups**: suggest related topics, deeper session retrieval via `/recall`

## Query Parsing Rules

| User Says | Action |
|-----------|--------|
| `/kb acme-corp` | `get_topic(name="acme-corp")` |
| `/kb` | `list_topics(limit=20)` — show overview |
| `/kb companies` | `list_topics(category="company")` |
| `/kb protocols` | `list_topics(category="protocol")` |
| `/kb search blockchain` | `search_knowledge(query="blockchain")` |
| `/kb history MCP` | `get_topic_history(name="MCP")` |
| `remember that Acme Corp deprecated X` | `add_insight(topic="acme-corp", insight="...")` |

## Response Format

For topic dossiers:

```
### Acme Corp [company]
6 sessions | Last seen: 2026-02-10

**Summary**: Acme Corp is a hypothetical platform...

**Key Insights**:
- Insight 1
- Insight 2

**Related**: Beta Inc (depends_on), Gamma Labs (competes_with)

**Recent Sessions**: (list 3-5 with titles and dates)
```

## Important Notes

- Topics are organized across categories (company, person, technology, project, concept, protocol, tool, place, general)
- Each topic can carry insights, relationships, and aliases
- Topic resolution is case-insensitive and alias-aware
- `search_knowledge` automatically falls back to the conversation index if knowledge base results are sparse
- Knowledge base is updated automatically via a stop hook after each session
- Manual re-population: run the populate script shipped with the MCP server (`populate.py --rebuild`)
