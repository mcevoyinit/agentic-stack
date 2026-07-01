# canonical — source-of-truth registry

A tiny CLI + SQLite table that solves one problem: stale facts baked
into prompts/skills/memory outlive the truth, and once a few copies
of a number agree with each other, every cross-check returns a false
green.

`canonical.py` keeps an append-only `canonical_sources` table. Every
`set` inserts a new row; the *current* truth for a concept is the
latest row. Full history stays for audit. Nothing is ever updated or
deleted in place.

The pattern: a skill or your `CLAUDE.md` carries a POINTER to a
concept ("for the Q3 revenue figure, read `finance/q3.md`"), never
the value itself. `canonical get --concept X` tells you which file
to read and how stale the last verification is.

## Install (creates an EMPTY db — no data ships with this template)

```bash
python3 infra-templates/canonical/setup.py
```

This does two things:
1. Creates `~/.claude-canonical/canonical.db` (or `$CANONICAL_DB` /
   `--db-path` if set) with the schema only. No rows.
2. Copies `canonical.py` to `~/.claude/infra/canonical.py` (or
   `$CLAUDE_HOME/infra/`), which is the path the optional SessionStart
   hook in `settings.json` invokes. Skip with `--no-install-cli`.

## Usage

```bash
# record that concept X's truth lives in file Y, with a short hint
canonical set --concept tax-2025 --file ~/finance/tax-2025.md \
  --value "estimate pending" --stale-days 14

# read it back later
canonical get --concept tax-2025

# list every concept and its freshness
canonical list

# full history of a concept
canonical history --concept tax-2025

# concepts past their staleness threshold
canonical stale

# re-verify without changing the value (bumps freshness)
canonical stamp --concept tax-2025

# regenerate a flat markdown projection
canonical render --out ~/.claude/CANONICAL.md

# emit a SessionStart hook payload (wire into settings.json hooks)
canonical inject
```

## Wiring into your own SessionStart hook

Add a `SessionStart` hook in `settings.json` that runs
`python3 ~/.claude/infra/canonical.py inject` — it prints a compact
`additionalContext` JSON blob the harness injects at the top of every
session, so you (and the agent) see which high-stakes facts exist and
which are stale before doing any work.

<!-- CUSTOMISE: this ships as pure mechanism. Populate your own
     concepts with `canonical set` after install — never hardcode a
     personal fact into this file or into canonical.py itself. -->
