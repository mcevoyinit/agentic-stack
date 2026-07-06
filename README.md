# agentic-stack

**Site:** https://mcevoyinit.github.io/agentic-stack/

## The short version

Most "prompt packs" are a folder of clever prompts. This is not that.
It is a **unified agentic system**: four layers that compose into one
self-maintaining loop, not a menu you pick from.

- **Skills**: 66 task modes the agent invokes on its own. Research,
  code review, planning, writing, multi-model deliberation across
  GPT, Gemini and Grok. The *what it can do*.
- **Rules**: always-on operating instructions that shape *how* it
  behaves on every single turn. Output format, verification
  discipline, tone, guardrails. Not invoked, always live.
- **Hooks**: lifecycle automation that fires without being asked.
  Injects the right context at session start, captures what was
  learned at session end, checks links, syncs indexes. The nervous
  system.
- **Memory + context**: persistent state across sessions. A
  source-of-truth registry, a conversation-recall index, a structured
  knowledge base. So it never re-learns what it already knew, and
  never quotes a stale fact.

The point is not any single skill. It is that **quality is enforced by
the system, not remembered by the human**. Context arrives
automatically. Insights are captured automatically. High-stakes facts
are derived live from a canonical source instead of hardcoded, so they
cannot silently go stale. The loop closes itself, so the agent gets
sharper every session instead of starting cold.

This is a **real, daily-driven stack**, sanitised and packaged so you
can install the whole thing in one command and run the same loop.

## What's underneath

A privacy-sanitised, installable export of a real, daily-driven Claude
Code agentic stack: 66 skills, a rules pattern, a hooks framework, an
MCP server reference list, and three runnable empty-schema infra
templates (canonical-facts registry, conversation recall index,
structured knowledge base).

Everything here is either generic (ships verbatim, useful as-is) or a
template (ships with personal data stripped, marked `<CUSTOMISE>`
where you need to plug in your own paths/accounts/data). Nothing in
this bundle contains real credentials, real personal data, or
populated databases. (A full sanitisation audit trail,
`SANITISATION-REPORT.md`, is kept alongside the bundle's source —
ask whoever gave you this bundle if you want it.)

## What's in here

```
agentic-stack-starter/
  README.md                  this file
  install.sh                 copies/symlinks everything into ~/.claude
  verify-install.sh          post-install doctor — run after install.sh
  claude/
    CLAUDE.md.template         global instructions skeleton
    settings.json.template     env/permissions/hooks/mcp, placeholders only
    statusline.sh               context-usage status line
    rules/                      5 composable instruction-pattern files
    skills/                     66 skills (see docs/SKILL-INDEX.md)
    hooks/                      Stop/SessionEnd/SessionStart hook scripts
    commands/                   slash commands (design review, spike VM, etc)
  mcp/
    mcp-servers.example.json   every MCP server this stack uses, by name,
                                 with placeholder creds and setup notes
  infra-templates/
    canonical/                  source-of-truth registry (empty schema)
    recall-db/                  cross-session conversation index (empty schema)
    knowledge-base/             topic dossier store (empty schema)
  docs/
    ARCHITECTURE.md             how the pieces fit together
    CUSTOMISE.md                everywhere you need to plug in your own data
    SKILL-INDEX.md               one-line description of every skill shipped
```

## Quick start

```bash
git clone https://github.com/mcevoyinit/agentic-stack
cd agentic-stack
./install.sh
./verify-install.sh   # doctor: checks the install, reports what's missing
```

Or the no-terminal route — paste this into Claude Code:

> Clone https://github.com/mcevoyinit/agentic-stack, run its
> install.sh, then verify-install.sh, then open docs/CUSTOMISE.md
> and walk me through the setup step by step, starting with the
> bits that need no accounts or keys.

`install.sh` copies `claude/` into `~/.claude/` (backing up anything
that would be overwritten), renders the two `.template` files by
stripping the `.template` suffix (it does NOT auto-fill placeholders —
that's deliberate, read `docs/CUSTOMISE.md` and fill them yourself),
and prints a checklist of what to configure next.

It does **not** install any MCP server, does **not** create any
credential file, and does **not** populate any database. Those are all
your own setup, by design — see `docs/CUSTOMISE.md`.

## Read these in order

1. **`docs/ARCHITECTURE.md`** — what a "stack" even means here: how
   skills, rules, hooks, and MCP servers compose, and why the design
   leans heavily on flat files + SQLite over anything fancier.
2. **`docs/CUSTOMISE.md`** — the concrete checklist of every
   `<CUSTOMISE>` marker in the bundle and what to do about it.
3. **`docs/SKILL-INDEX.md`** — what each shipped skill does, so you
   know what you're turning on.
4. **`claude/skills/morning-brief/INTEGRATION.md`** — the deepest
   single integration guide in the bundle, if you want the flagship
   daily-briefing skill running end to end.

## A note on what isn't here

Some categories were deliberately excluded, not just lightly redacted:
full MCP server implementations (whatsapp, hermes, slack, github,
gws, nimble, x — you bring your own or use community servers), the
indexer/embedder that would populate `recall-db`, the ingestion
pipeline for `knowledge-base`, and every skill that was inherently
about one person's specific life (finance tracking, health, a named
business deal, a named relationship). The `SANITISATION-REPORT.md`
kept with the bundle's source lists every exclusion and why.

