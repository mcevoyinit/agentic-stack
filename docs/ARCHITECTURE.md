# Architecture

## The shape of the stack

Claude Code reads four kinds of files from `~/.claude/` at session
start or on demand:

| Layer | Where | What it does |
|-------|-------|---------------|
| Global instructions | `CLAUDE.md` | Always-loaded preferences, every session |
| Rules | `rules/*.md` | Composable instruction patterns, referenced by name |
| Skills | `skills/<name>/SKILL.md` | On-demand capability, invoked by trigger phrase or `/name` |
| Hooks | `settings.json` → `hooks` | Shell/Python scripts fired on session/tool lifecycle events |

Plus MCP servers (`settings.json` → `mcpServers`), which give the
agent tools beyond its built-ins (Read/Write/Bash/etc) — email,
calendar, chat platforms, search, your own infra.

None of these are exotic. The leverage is in composition: a rule like
`reminders.md` defines a todo-file protocol; a hook
(`session-end-autocapture.sh`) auto-extracts action items into that
same file at session end; a skill (`morning-brief`) reads it back the
next morning. Three independent, individually-simple pieces compose
into something that feels like memory.

## Why flat files + SQLite, not a database service

Every piece of state in this stack — the todo file, the canonical
registry, the recall index, the knowledge base — is either a plain
markdown file or a local SQLite database. No server process to keep
running, no schema migration tooling, nothing that breaks when you
move to a new machine except "copy the file." This was a deliberate
choice: agentic workflows already have enough moving parts (the model,
the harness, N MCP servers); the persistence layer should be the most
boring part of the system.

SQLite specifically because it gives you full-text search (FTS5) and
transactional writes without an external process, which matters when
multiple Claude Code sessions might be reading/writing the same recall
index concurrently (WAL mode handles this).

## The "derive, never hardcode" pattern

The single most important pattern in this bundle, and the one most
worth carrying into your own skills: **a number that changes over time
must never be hardcoded into a skill prompt.** Skills get re-read and
re-trusted every session. A stale figure baked into a prompt doesn't
just go stale — it actively misleads, with full confidence, every time
the skill fires.

`infra-templates/canonical/` is the mechanism: an append-only SQLite
table mapping a concept name to (a) the file that holds the current
truth and (b) a dated hint value, with staleness tracking. Skills and
`CLAUDE.md` carry a POINTER to a concept, never a copy of the value.
See that directory's README for the full pattern, and
`claude/skills/morning-brief/INTEGRATION.md` §6 for a worked example
(a price tracker / deadline countdown).

## The verifier-preflight pattern

The second pattern worth stealing, from `morning-brief`: any agent
that re-surfaces a todo list every day will eventually nag you about
things you've already done, and trust erodes fast once that happens a
few times. The fix isn't a smarter prompt — it's a preflight step that
reconciles the todo list against ground-truth signals (sent mail,
payment confirmations, outbound messages, file mtimes) BEFORE the
agent renders anything, writing a `proposals.md` with three buckets:
closed-by-evidence, needs-human-review, still-pending. Downstream
sections read the reconciled output, never the raw todo file.

This generalizes past daily briefs — any agent that tracks open work
against a flat list benefits from a ground-truth reconciliation pass
ahead of the "what's left" render.

## The two-message glance-card pattern

Also from `morning-brief`: when an agent's output gets long, the
single most common failure mode is repeating the same fact (a name, a
task) in three different sections, which makes the whole thing harder
to scan, not easier. The fix: emit two messages — a short, fixed-shape
"glance card" with each fact appearing exactly once, then a "detail"
message that expands on it. Never duplicate a fact across the two.

## Subagent delegation patterns

Several skills (`kamikaze`, `phoenix`, `looper`, the claim-verification
fanout in `morning-brief` §0.4) use the `Agent` tool to fan out
independent work in parallel rather than processing serially. The
recurring shape: build N independent prompts, dispatch all N `Agent`
calls in a single assistant turn (not sequential turns — sequential
calls don't actually run in parallel), require each subagent to return
a strict JSON contract (not prose), then merge mechanically. This
shows up enough times across this bundle that it's worth recognizing
as a reusable shape rather than re-deriving it per skill.

## Privacy-by-construction in the rules layer

`rules/output-format.md`, `rules/drafts.md`, and
`rules/reminders.md` are deliberately decoupled from any specific
person's setup — they reference `$DRAFTS_DIR`, `$TODO_FILE`, an
"effective width" you measure yourself, rather than hardcoded paths.
That's not just sanitisation for this export — it's the right shape
for a rule file in general, since rules get copy-pasted between
projects/machines far more often than skills do.
