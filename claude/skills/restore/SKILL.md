---
name: restore
description: |
  Restore recent Claude Code sessions into new iTerm2 tabs with dangerous mode.
  Generates AppleScript, executes it, opens tabs. Fully automated.
  Trigger: "/restore", "restore sessions", "restore <project>", "open my sessions".
args: "<project> [count]"
---

# Restore Sessions

Bulk-resume recent Claude Code sessions into new iTerm2 tabs.

## Usage

```
/restore <project> [count]
```

- `project` — fuzzy project name filter. Pass any directory name that
  appears under `~/.claude/projects/` (e.g. the leaf of a repo path you
  work in). There is no hardcoded project list — whatever exists on disk
  is matched.
- `count` — number of most recent sessions to restore (default: 10)

## Examples

```
/restore myapp 20        # Last 20 sessions for the "myapp" project
/restore myapp           # Last 10 myapp sessions (default)
/restore backend 5       # Last 5 sessions for the "backend" project
```

## Implementation — FOLLOW EXACTLY

### Step 1: Generate the AppleScript

```bash
python3 ~/.claude/skills/session-survey/survey_sessions.py \
  --project <PROJECT> \
  --top <COUNT> \
  --write-script /tmp/open_sessions.scpt
```

### Step 2: Execute it (background, no wait)

```bash
osascript /tmp/open_sessions.scpt &
```

Run this with `run_in_background: true` in the Bash tool. Do NOT wait for output.
Do NOT use TaskOutput to check on it. It just fires and opens the tabs.

### Step 3: Confirm to user

Tell the user how many tabs were opened. Done.

## Rules

- ALWAYS dangerous mode (no `--safe` flag)
- ALWAYS `cd <project-dir>` in each tab command (baked into `--write-script`)
- Execute the script — do NOT tell the user to run it manually
- Use `run_in_background: true` for the osascript call to avoid timeout
- If osascript genuinely fails (permission denied), THEN fall back to telling user to run manually
