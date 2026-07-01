---
name: session-survey
description: |
  Survey, summarize, and recover recent Claude Code sessions across all projects.
  Scans ~/.claude/projects/ for active sessions, extracts synopses, checks tmux
  status, and offers multiple recovery modes (iTerm tabs, tmux windows, or tmux
  sessions per project).
  Trigger: "sessions", "survey sessions", "what sessions", "recover sessions",
  "reopen sessions", "my sessions", "session recovery", "what was I working on".
---

# Session Survey & Recovery

Survey recent Claude Code sessions and reopen them using the user's preferred layout.

## Crash recovery — optional live-snapshot pattern

Reconstructing open tabs purely from disk under-counts: file mtime means
"last wrote", not "was open", so idle tabs look closed, and hyphenated
project dirs can be mis-decoded. If you want exact crash recovery, run a
small background heartbeat (e.g. a launchd/cron job every ~2 min) that
records the currently-open tabs — real cwd via `lsof`, resume id from
process args — to a JSON file you control (e.g. `~/.claude/open-tabs.json`)
plus a timestamped history dir. Then a replay script can bake
`mkdir -p <cwd> &&` before each `cd` so a deleted scratch dir can't break
recovery, and read the REAL cwd so it never mis-decodes a dir name.

This heartbeat infra is NOT bundled with this template — it's an optional
add-on you can build for your own setup. Out of the box, use the disk
survey below, which works without any background daemon.

## Core Script

```bash
python3 ~/.claude/skills/session-survey/survey_sessions.py
```

### CLI Flags

| Flag | Example | Effect |
|------|---------|--------|
| `--days N` | `--days 14` | Look back N days (default: 7) |
| `--today` | `--today` | Today's sessions only |
| `--project X` | `--project myapp` | Filter by project name (fuzzy) |
| `--top N` | `--top 5` | Top N sessions per project |
| `--tmux` | `--tmux` | Include tmux process status check |
| `--json` | `--json` | JSON output (for piping) |
| `--resume-cmds` | `--resume-cmds` | Output copy-paste resume commands |
| `--restore` | `--restore` | Open ALL sessions in new iTerm tabs (dangerous mode) |
| `--restore X` | `--restore myapp:1,3 backend:2-5` | Open specific sessions by project:number |
| `--safe` | `--restore --safe` | Omit `--dangerously-skip-permissions` |
| `--dry-run` | `--restore --dry-run` | Print commands without executing |
| `--write-script` | `--write-script /tmp/open_sessions.scpt` | Write AppleScript to file (sandbox-safe) |

### Restore Mode (iTerm Tabs)

Opens each session in a new iTerm2 tab with `cd <project-dir> && claude --resume <id> --dangerously-skip-permissions`.

```bash
# Restore all sessions found
python3 ~/.claude/skills/session-survey/survey_sessions.py --restore

# Restore myapp sessions #2 and #3 only
python3 ~/.claude/skills/session-survey/survey_sessions.py --top 10 --restore myapp:2,3

# Restore myapp sessions #1-5 and backend session #1
python3 ~/.claude/skills/session-survey/survey_sessions.py --top 10 --restore myapp:1-5 backend:1

# Restore all sessions for one project without dangerous mode
python3 ~/.claude/skills/session-survey/survey_sessions.py --project myapp --restore --safe

# Preview what would be opened
python3 ~/.claude/skills/session-survey/survey_sessions.py --top 5 --restore --dry-run
```

Pick selectors use `project:N` format where N can be:
- Single: `myapp:3`
- List: `myapp:1,3,5`
- Range: `myapp:1-5`
- All: `myapp` (bare name = all sessions)

Numbers correspond to the `#` column in the survey table output.

## Recovery Modes

When the user wants to reopen sessions, ask which mode they prefer:

### Mode 1: tmux windows (default — what we use)

All sessions as named windows inside one tmux session per project.
Best for: organized switching with `Ctrl-b w`, survives terminal crashes.

```bash
# Create tmux session with named windows
tmux new-session -d -s "myapp" -n "feature-a" -c "$HOME/projects/myapp"
tmux send-keys -t "myapp:feature-a" "claude --resume <session-id>" Enter

tmux new-window -t "myapp" -n "feature-b" -c "$HOME/projects/myapp"
tmux send-keys -t "myapp:feature-b" "claude --resume <session-id>" Enter
```

Navigation: `tmuxx <window-name>`, `Ctrl-b w` (picker), `Ctrl-b n/p` (next/prev)

### Mode 2: Separate iTerm tabs

Each session in its own iTerm2 tab. Best for: visual tab bar, mouse clicking.

```bash
osascript -e '
tell application "iTerm2"
    tell current window
        create tab with default profile
        tell current session of current tab
            write text "cd $HOME/projects/myapp && claude --resume <session-id>"
        end tell
    end tell
end tell'
```

### Mode 3: tmux session per topic (hybrid)

Each topic gets its own tmux session (not just a window). Best for: full isolation,
separate `tmuxx <topic>` attach points.

```bash
tmux new-session -d -s "feature-a" -c "$HOME/projects/myapp"
tmux send-keys -t "feature-a" "claude --resume <session-id>" Enter

tmux new-session -d -s "feature-b" -c "$HOME/projects/myapp"
tmux send-keys -t "feature-b" "claude --resume <session-id>" Enter
```

Navigation: `tmuxx feature-a`, `tmuxx feature-b` (each attaches to separate session)

## Workflow

1. **Survey** — Run the script to see what's there:
   ```bash
   python3 ~/.claude/skills/session-survey/survey_sessions.py --today
   ```

2. **Ask the user** which recovery mode they want:
   - tmux windows (grouped by project)
   - iTerm tabs (one per session)
   - tmux sessions (one per topic)

3. **Launch** — Generate and run the appropriate commands

4. **Verify** — Check what's actually running:
   ```bash
   tmux ls                           # List tmux sessions
   tmux list-windows -t myapp        # List windows in a session
   ```

5. **Health check** — Verify Claude is running in each pane:
   ```bash
   # Check all panes for running claude processes
   tmux list-panes -a -F "#{session_name}:#{window_name} pid=#{pane_pid}" | while read line; do
       pid=$(echo "$line" | grep -o 'pid=[0-9]*' | cut -d= -f2)
       children=$(pgrep -P "$pid" 2>/dev/null)
       if [ -n "$children" ]; then
           echo "✅ $line"
       else
           echo "❌ $line (no claude process)"
       fi
   done
   ```

## Shell Aliases (in ~/.zshrc)

Optional convenience helpers — set `DEFAULT_TMUX_SESSION` to your most-used
project name, or pass a name explicitly:

```bash
tmuxx() {       # Attach to session or find window by name
  local target="${1:-${DEFAULT_TMUX_SESSION:-main}}"
  if tmux has-session -t "$target" 2>/dev/null; then
    tmux attach -t "$target"
  else
    local match=$(tmux list-windows -a -F "#{session_name}:#{window_name}" 2>/dev/null | grep -i "$target" | head -1)
    if [ -n "$match" ]; then
      tmux select-window -t "$match" && tmux attach -t "${match%%:*}"
    else
      echo "No match for '$target'"
      tmux ls 2>/dev/null
    fi
  fi
}

tmuxkk() { tmux kill-window -t "${DEFAULT_TMUX_SESSION:-main}:$1"; }
```

## Key tmux Commands

| Command | Action |
|---------|--------|
| `tmuxx` | Attach to default session |
| `tmuxx feature-a` | Find and attach to the feature-a window |
| `tmuxkk 7` | Kill window 7 |
| `tmux ls` | List all sessions |
| `Ctrl-b w` | Visual window picker |
| `Ctrl-b n/p` | Next/prev window |
| `Ctrl-b d` | Detach (keeps running) |
| `Ctrl-b &` | Kill current window |

## Session File Locations

| What | Where |
|------|-------|
| History index | `~/.claude/history.jsonl` |
| Session files | `~/.claude/projects/<encoded-dir>/<session-id>.jsonl` |
| Subagent data | `~/.claude/projects/<encoded-dir>/<session-id>/subagents/` |

## Important Notes

- **`claude --resume` from shell** gives full scrollable list (not the truncated 8-10 from `/resume` inside a session)
- **`-p` flag sessions exit immediately** — use interactive mode for persistent sessions
- **`--dangerously-skip-permissions`** skips all permission prompts (use for trusted work)
- **Mouse scroll in tmux** requires `set -g mouse on` in `~/.tmux.conf`
- **50K line scrollback** configured in `~/.tmux.conf` (`history-limit 50000`)
- Session `.jsonl` files survive everything — always recoverable from disk even if tmux dies
- **Sandbox gotcha**: `osascript` from within Claude Code times out because the sandbox blocks iTerm2 automation. Use `--write-script` to generate a `.scpt` file, then tell the user to run `osascript /tmp/open_sessions.scpt` from their own terminal
- **Use `/restore` skill** for quick bulk restore: `/restore myapp 20` generates the script and tells user to run it
