---
name: recall
description: |
  Search and recall past Claude Code conversations with verbatim accuracy.
  Queries a SQLite database of indexed messages across all projects.
  Supports keyword search, date browsing, and full session retrieval.
  Trigger: "recall", "remember", "what did we discuss", "find conversation",
  "search history", "past conversation", "what did we work on".
---

# Conversation Recall

You have access to a conversation search database via the
`conversation-search` MCP server. Use these tools to find and display past
conversations.

> Setup note: the conversation index ships EMPTY. The install script creates
> the SQLite DB and registers the MCP server; an indexer backfills your own
> Claude Code transcripts on first run and keeps them current after that. All
> examples below use generic placeholder projects and previews.

## Available MCP Tools

Use ToolSearch to load these tools before calling them:
- `mcp__conversation-search__search_conversations` — Full-text search across all messages
- `mcp__conversation-search__get_session` — Retrieve a full verbatim conversation
- `mcp__conversation-search__list_sessions` — Browse sessions chronologically
- `mcp__conversation-search__search_by_date` — Find sessions by date

## Workflow

1. **Parse the user's query** to determine intent:
   - Keywords/topic → use `search_conversations`
   - Date reference ("yesterday", "last week", "Feb 3") → use `search_by_date`
   - "List sessions" or project browsing → use `list_sessions`
   - Specific session ID → use `get_session`

2. **Search first**, then offer to retrieve full sessions:
   - Show a summary table of matching results
   - Ask if they want the full conversation from any session

3. **Format results clearly**:
   - Use markdown tables for session lists
   - Quote relevant message excerpts
   - Always show timestamps and project context

## Query Parsing Rules

| User Says | Action |
|-----------|--------|
| `/recall fundraising` | `search_conversations(query="fundraising")` |
| `/recall yesterday` | `search_by_date(date="yesterday")` |
| `/recall last tuesday` | `search_by_date(date="last tuesday")` |
| `/recall docker myproject` | `search_conversations(query="docker", project="myproject")` |
| `/recall Jan 15 myproject` | `list_sessions(date="2026-01-15", project="myproject")` |
| `/recall this week` | `search_by_date(date="this week")` |

## Response Format

After searching, present results as:

```
### Found N results for "query"

| # | Project | Time | Preview |
|---|---------|------|---------|
| 1 | project-a | Jan 15, 2:30 PM | "discussed the authentication flow..." |
| 2 | project-b | Jan 14, 10:15 AM | "reviewed the API client..." |

Want me to pull up the full conversation from any of these?
```

## Important Notes

- The database contains your own indexed Claude Code messages across all projects
- FTS5 supports: AND, OR, NOT, "exact phrases", prefix*
- Older entries may be user prompts only if they predate full-transcript
  logging; newer entries have full verbatim transcripts (user + assistant)
- Sessions with a `history-` prefix ID come from a legacy history file
