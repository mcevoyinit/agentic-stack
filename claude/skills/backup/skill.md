---
name: backup
description: |
  Full production-grade backup of a Claude Code setup to a cloud remote (or
  local-only). Atomic SQLite snapshots, integrity-verified archive, optional
  rclone sync, retention pruning. Backs up config, skills, rules, commands,
  hooks, agents, plugins, conversation transcripts, project configs, and
  CLAUDE.md files — everything needed to port to a new machine. Secrets are
  excluded by default.
  Trigger: "backup", "/backup", "back up my setup", "sync backup to drive",
  "save my claude setup", "port to new machine".
---

# Claude Code Full Backup Skill

Production-grade backup system that captures everything needed to replicate a
Claude Code setup on a new machine — in one command. Nobody-specific: every
path and destination is configurable.

## What to do

1. **Run the backup script** (backup + integrity check + optional sync + prune):
   ```bash
   ./backup.sh                 # full backup + cloud sync (needs BACKUP_REMOTE)
   ./backup.sh --local-only    # skip cloud sync
   ```

2. **Report** the results with a summary table. The script prints the archive
   path, size, item count, and (if synced) the remote path. Extract these and
   format them for the user.

The script handles:
- Pre-flight checks (disk space, cloud remote reachable, required tools)
- Atomic SQLite snapshots via `sqlite3 .backup` (safe even with an MCP server running)
- File-level backup of all Claude Code config, skills, history, hooks, etc.
- Self-exclusion (won't recursively back up prior backups)
- SHA-256 checksums of critical files
- Archive creation with `tar tzf` integrity verification
- Optional upload to a cloud remote (rclone) with size verification
- Local + remote retention pruning
- Staging cleanup (removes uncompressed dir after archiving)

## Configuration (environment variables)

| Var | Purpose | Default |
|-----|---------|---------|
| `BACKUP_REMOTE` | rclone remote + path for sync | `your-remote:claude-code-backups` (placeholder — set it) |
| `BACKUP_DEST` | Local archive destination | `$HOME/claude-backups` |
| `BACKUP_EXTRA_DIRS` | Space-separated extra dirs to include | empty |
| `BACKUP_OAUTH_DIR` | Optional OAuth/credentials config dir | empty |
| `BACKUP_MCP_DATA_DIRS` | MCP data dirs with SQLite DBs | `~/.claude-conversations ~/.claude-knowledge` |
| `BACKUP_LOCAL_RETENTION` | Local archives to keep | 3 |
| `BACKUP_REMOTE_RETENTION` | Remote archives to keep | 5 |
| `BACKUP_MIN_FREE_GB` | Min free disk (GB) | 5 |

For cloud sync you MUST set `BACKUP_REMOTE` (e.g.
`export BACKUP_REMOTE=myremote:claude-code-backups`). Otherwise use
`--local-only`.

## Flags

| Flag | Purpose |
|------|---------|
| `--local-only` | Skip cloud sync |
| `--no-prune` | Keep all old backups (no retention) |
| `--dest DIR` | Use a custom local destination |
| `--include-secrets` | Bundle secret files (off by default — see below) |

## Security — secrets excluded by default

The archive is **unencrypted**. By default the script does NOT copy files that
commonly hold live secrets:

- `api-keys.env`
- `settings.local.json`
- `.credentials.json`

This stops your own keys leaking into an unencrypted cloud backup on the first
run. Pass `--include-secrets` to bundle them — and only do so if you encrypt
the archive at rest (an rclone `crypt` remote, or gpg-encrypt the `.tar.gz`
before upload).

Note: `config.json` may still contain MCP server API keys. Review the archive
before sharing it.

## What gets backed up

| Category | Source |
|----------|--------|
| Core config | `~/.claude/{config.json,settings.json,CLAUDE.md,statusline.sh}` |
| History | `~/.claude/{history,session-cache,session-index}.jsonl` |
| Skills | `~/.claude/skills/` |
| Rules/Commands/Agents/Hooks/Scripts/Prompts/Teams | `~/.claude/{rules,commands,agents,hooks,scripts,prompts,teams}/` |
| Plugins | `~/.claude/plugins/` |
| Project transcripts & memory | `~/.claude/projects/` |
| Personal archive | `~/.claude/personal-archive/` |
| Plans/Todos/Tasks | `~/.claude/{plans,todos,tasks}/` |
| MCP data dirs (atomic SQLite) | `$BACKUP_MCP_DATA_DIRS` |
| Extra dirs / OAuth config | `$BACKUP_EXTRA_DIRS`, `$BACKUP_OAUTH_DIR` |
| Project `.claude` dirs | All `.claude/` across projects |
| CLAUDE.md files | All `CLAUDE.md` / `CLAUDE.local.md` under `$HOME` |
| Secrets (opt-in) | `api-keys.env`, `settings.local.json`, `.credentials.json` |

## Atomic SQLite guarantees

Any SQLite DBs in the configured MCP data dirs are captured with
`sqlite3 .backup` — an online backup that produces a consistent snapshot even
while the DB is being written. Each snapshot is verified with
`PRAGMA integrity_check` before being included in the archive.

## Restore on a new machine

```bash
# (optional) pull the latest backup from your remote
LATEST=$(rclone lsf "$BACKUP_REMOTE/" --files-only | sort -r | head -1)
rclone copy "$BACKUP_REMOTE/$LATEST" ~/

# extract and restore
tar xzf claude-backup-*.tar.gz
cd claude-backup-*
./restore.sh --dry-run   # preview
./restore.sh             # full restore (prompts for confirmation)
# or: ./restore.sh --force  # skip confirmation
```

The restore script:
- Verifies SHA-256 checksums before touching anything
- Runs SQLite integrity checks on all DBs
- Auto-creates Python venvs for any restored dir with a `requirements.txt`
- Restores executable permissions on hooks/scripts
- Prompts before overwriting (unless `--force`)
- Reminds you to re-add any secret files that were excluded
