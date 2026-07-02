# Customise checklist

Every file in this bundle that needs your own data instead of a
placeholder is marked `<CUSTOMISE>` inline, or carries an HTML comment
`<!-- CUSTOMISE: ... -->` at the bottom. To find every one of them at
any time:

```bash
grep -rn 'CUSTOMISE' agentic-stack-starter/
```

That command is the live, authoritative list — this file is a guided
tour through the same markers, grouped by what you're trying to do.

## 1. Get a minimal setup running (no MCP servers needed)

- [ ] `claude/CLAUDE.md.template` → copy to `~/.claude/CLAUDE.md`,
      replace the example instructions with your own preferences.
- [ ] `claude/settings.json.template` → copy to
      `~/.claude/settings.json`, review the `hooks` block (two hooks
      are real and work immediately: `check-links.py` and
      `session-end-autocapture.sh`; an optional `canonical inject`
      SessionStart hook can be added later — see step 3 below).
- [ ] `claude/rules/drafts.md` → set `$DRAFTS_DIR` in your shell
      profile, or accept the default.
- [ ] `claude/rules/reminders.md` → set `$TODO_FILE` in your shell
      profile, or accept the default (`~/todo.md`). Create that file
      with at least a `## Open (no date)` heading.
- [ ] `claude/rules/output-format.md` → if your terminal is zoomed or
      otherwise renders narrower than it reports, set your own
      effective-width default; otherwise the 72-char default is fine.
- [ ] `claude/rules/fable-5.md`, `claude/rules/kb-triggers.md` → no
      edits required to function; `kb-triggers.md` just won't have
      anything to call until you do step 3 below.

## 2. Add MCP servers

- [ ] Read `mcp/mcp-servers.example.json` — pick the servers you
      actually want (you do NOT need all of them; `x`/`codex` are
      wired as a minimal example in `settings.json.template`, the rest
      are reference entries to copy in).
- [ ] For each server you add: get your own credentials, export them
      as env vars in your shell profile (never commit them), reference
      as `${VAR_NAME}` in `settings.json`.
- [ ] The multi-model skills (`gemini`, `openai`, `grok`, `looper`,
      `phoenix`, `kamikaze`, `best-models`) read provider keys from
      `~/.claude/api-keys.env` first (falling back to `.env.local` /
      the environment). Create that file as `KEY=value` lines and
      `chmod 600` it — it is never shipped or committed.
- [ ] `claude/commands/spike.md` → set `$SPIKE_GCP_PROJECT` if you use
      the GCP demo-VM command.

## 3. Stand up the infra templates (all optional)

- [ ] `infra-templates/canonical/` → run `setup.py` (creates the empty
      db AND installs the CLI to `~/.claude/infra/canonical.py`), then
      start recording concepts with `canonical set`. To surface your
      concepts at the top of every session, add the SessionStart hook
      snippet from `infra-templates/canonical/README.md` to
      `settings.json` — it's opt-in, not wired by default.
- [ ] `infra-templates/recall-db/` → run `setup.py` to create the
      empty schema, then write your own indexer (walks your
      `~/.claude/projects/*/*.jsonl` transcripts) and your own query
      server/skill. The `recall` skill in `claude/skills/recall`
      expects this to exist.
- [ ] `infra-templates/knowledge-base/` → run `setup.py`, then write
      your own server exposing `get_topic` / `add_insight` /
      `list_topics` / `search_knowledge`. `claude/rules/kb-triggers.md`
      and `claude/skills/kb` expect these four operations.

## 4. The flagship: morning-brief

This is the deepest single piece in the bundle. Don't try to get it
fully working in one sitting — see
`claude/skills/morning-brief/INTEGRATION.md` for a staged setup (an
email + calendar MCP gets you 80% of the value; everything else layers
on incrementally).

## 5. TMPL skills — already parameterised, no hardcoded defaults

A second group of skills was reworked so there's nothing to fill in —
they take a project/path/account as an argument or env var instead of
assuming one, so they work for you immediately with no edits:
`codex-review`, `restore`, `vc-acquirer`, `cheap-flights`, `mac-health`,
`session-survey`, `learn`, `airplane`, `kb`, `recall`,
`x-bookmarks-iterate`, `x-bookmark-export-cdp`, `backup`. Worth
skimming each `SKILL.md` once before first use so you know what
argument/env var it expects (e.g. `restore <project> [count]`,
`MAC_HEALTH_SNAP_DIR`, `BACKUP_REMOTE`) — see each skill's own doc for
specifics.

## 6. Things this bundle deliberately does NOT do for you

- It does not create or fill any credential file.
- It does not install or configure any MCP server binary.
- It does not populate any database — every shipped schema is empty.
- It does not pick a todo-file format for you beyond the minimal
  heading structure `reminders.md` expects.

This is intentional: a starter kit that silently assumed your paths,
your accounts, or your habits would be lying about being a starter kit.
