# Output Formatting

ALWAYS use a markdown table when presenting structured data: files
modified, comparisons, options, status grids, anything with parallel
rows. NEVER substitute a `-` bulleted list. NEVER substitute labeled
prose blocks (`Field: value` lines). The table is non-negotiable.

## Effective width

If you know your terminal renders narrower than it reports (zoomed
iTerm/tmux panes, a CI log viewer, a notification width limit), set
an effective width and stick to it. Long paragraphs that "the
terminal will reflow" do NOT reflow into a narrower visible viewport
than the renderer assumes. Write short sentences. Break paragraphs
into multiple short lines.

A reasonable default if you haven't measured your own setup: 72
chars. Adjust to match your actual terminal.

## Table width rule

- Total rendered table width ≤ your effective width (count pipes,
  spaces, everything).
- Per-column caps summing ≤ that width. Suggested split for a 72-char
  budget: identifier/file ≤ 18, status ≤ 10, prose ≤ 32. Adjust per
  table.

## Never use `<br>` inside cells

Many terminal markdown renderers print `<br>` literally as the
characters `<br>` instead of a line break. Avoid it; use a new row
instead.

## When a cell would exceed its column cap

In strict priority order — exhaust each before moving to the next:

1. **Shorten the cell.** Strip articles, use leaf paths, drop
   parentheticals, summarize harder. "Tiered pricing library; agents
   get 402 + negotiation" beats the full sentence.
2. **Split one row into multiple rows.** If an item has 3 facts that
   won't fit one row, give it 3 rows (repeat the name or use `↳`
   continuation).
3. **Drop a column.** Merge two short columns, or move one column's
   data into the row label.
4. **Lift ONE cell's detail out as a follow-up line below the
   table.** Last resort, for a single outlier. Format as `**name —**
   terse fact.` on its own line. NOT a wholesale fallback — the table
   must still carry every row.

NEVER drop the table and use labeled prose blocks like `Repo: foo /
Lang: Python / Tests: 60 / What it does: ...`. That is the failure
mode.

## Prose under or beside tables

If you write prose at all (intro, lift-out detail, summary line),
keep each sentence within your effective width on its own line.
Don't write multi-line paragraphs that depend on reflow.

## Full paths

When the user needs to copy a path, show the full absolute path. If
it won't fit in a cell after shortening, put it on its own fenced
code line BELOW the table (not inside the cell). The table cell
holds the leaf; the code block below holds the full path.

## Hygiene

- 1-word column headers (`File`, `Change`, `Status` — not `File
  Path`)
- Strip path prefixes to the leaf (`pool.py`, not
  `server/api/core/pool.py`)
- If leaf is ambiguous, use shortest unique suffix (`core/pool.py`)
- Cells: no trailing punctuation, no parentheticals unless
  load-bearing
- Drop articles (`Added TokenCache` not `Added a TokenCache`)

## Example — short cells, no overflow

| File | Change |
|------|--------|
| `pool.py` | Added TokenCache, wired into pool |
| `client.py` | Cache-first auth strategy |

## Example — rows with long descriptions, handled correctly

| Service | Lang | Tests | Deployed |
|---------|------|-------|----------|
| billing | Python | 60 | No |
| orchestrator | Python | 68 | 1 prod run |
| ingest | Go | 26 | 2 prod runs |

**billing —** Tiered pricing library, usage metering hooks.
**orchestrator —** Job scheduler with retry + backoff policies.
**ingest —** Streaming pipeline, dedupes on event id.

Table is the scannable scaffold. One short line per item below it —
each within your effective width. No `<br>`, no labeled-prose
blocks, no overflow.

<!-- CUSTOMISE: this rule originally hardcoded a specific user's
     terminal width quirk and project names as examples. Replace the
     examples above and the "effective width" default with your own
     setup if different. -->
