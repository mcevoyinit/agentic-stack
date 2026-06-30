---
name: mac-health
description: |
  macOS system health and resource triage. Reports REAL memory pressure
  (swap + compressed + active/wired — not the misleading `top` "used"),
  ranks top consumers, detects zombie processes (suspended claude sessions,
  orphaned helpers, runaway daemons like Docker krun), and produces a
  confirmation-gated kill list ordered by safety × payoff. Read-only by
  default; never kills without explicit user approval.
  Trigger: "mac health", "system check", "what's eating my mac",
  "why is it hot", "reclaim ram", "free up memory", "check resources",
  "zombie processes", "my mac is slow", "machine resources",
  "what can we kill", "/mac-health".
  DO NOT activate for: general performance tuning of user code (use profiler),
  debugging application behavior (use forensic), or kernel-level investigation.
---

# mac-health: macOS Resource Triage

Inspect the local machine, surface real resource pressure, propose safe kill candidates. Never kill anything automatically.

## The macOS "used" myth — read this first

`top` reports `PhysMem: X used / Y unused` where `X` **includes inactive memory that macOS reclaims instantly**. Activity Monitor's "Memory Used" gauge does the same. On a 128 GB Mac it's routine to see "120G used / 3G unused" while the system is idle and not swapping at all. Don't panic at that number. Don't recommend kills off it.

**Trust these signals instead:**

| Signal | Source | Interpretation |
|--------|--------|----------------|
| swap used | `sysctl vm.swapusage` | 0 = no pressure. Growing = real pressure. **Primary signal.** |
| compressed pages | `vm_stat` | 0 = fine. Multi-GB = being squeezed |
| active + wired | `vm_stat` | Real usage in GB |
| inactive | `vm_stat` | Reclaimable. Not really used. |
| `memory_pressure` | cmd (format varies by macOS) | Normal / Warn / Critical |

If `swap = 0` and `compressed = 0`, the machine is fine regardless of `top`'s number.

## Invariants

- **Read-only by default.** Observe and report. Kills require the user to explicitly name targets ("kill docker", "kill the zombies", "kill PID 12345") or confirm a ranked list.
- **Always report before acting.** Even if the user says "clean it up," produce the kill list first, wait for go-ahead.
- **Never kill foreground claude processes** (STAT contains `+`) unless named by PID or session ID.
- **Never kill the current session.** The claude process whose TTY matches yours is off-limits.
- **Never touch system processes**: `WindowServer`, `launchd` (PID 1), `kernel_task`, `loginwindow`, `Finder`, `coreaudiod`, `WindowManager`, anything in `/System/` or root-owned in `/usr/libexec/`.
- **Snapshot before any destructive action.** Crash insurance for resuming sessions.

## Run order

### 1. Snapshot — always first

```bash
bash ~/.claude/skills/mac-health/snapshot.sh
```

Captures: swap, vm_stat real breakdown, thermal, disk, top 15 by RSS, memory-by-category, active claude sessions with IDs, suspended (T-state) claude procs. Writes to `$MAC_HEALTH_SNAP_DIR/YYYY-MM-DD-HHMM.md` (default `~/.session-snapshots`; set `MAC_HEALTH_SNAP_DIR` to relocate) and echoes the path.

Read the snapshot file, don't re-run `ps`/`top`/`vm_stat` yourself. The script is the source of truth.

### 2. Interpret

- **"real usage (active+wired)" line** in the snapshot → the honest headline
- **swap > 0** → system genuinely pressured, act soon
- **compressed > a few GB** → system genuinely pressured
- **None of the above** → `top`'s scary "used" number is noise; report calmly and don't push kills

### 3. Zombie detection

- **Suspended claude** (`STAT` contains `T`): ctrl+Z'd behind a newer claude in same tab. Invisible in terminal but holding full RAM. Always safe to kill — JSONL on disk is source of truth. Typically show up as the oldest PIDs (multi-day uptime).
- **Duplicate claude per TTY**: same PPID, two PIDs → one is suspended.
- **Orphans** (`PPID=1`): parent shell died, child reparented to launchd. Rare on modern macOS.
- **Runaway daemons**: compare current RSS vs a previous snapshot in `$MAC_HEALTH_SNAP_DIR`. Docker krun grows 17 → 29 GB over hours when idle — the classic case.

### 4. Idle bloat candidates

- **Docker Desktop** — 15-30 GB when idle with no active containers. Top kill candidate.
- **PyCharm / IntelliJ** — ~3 GB even with no project open.
- **Slack / WhatsApp** — ~2 GB each when not actively chatting.
- **superwhisper** — ~2 GB with voice model loaded. Relaunch takes seconds.
- **Stale dev servers** (vite / next / webpack / jest --watch) — **ask first**; may be active dev loop.

### 5. Kill list — ranked by safety × payoff

Produce a narrow markdown table:

| # | Target | Size | Safety | Action |
|---|--------|------|--------|--------|
| 1 | Docker krun (PID) | N GB | safe if no live containers | AppleScript quit + `pkill -9 -f com.docker` |
| 2 | Suspended claude × N | N GB | 100% safe — JSONL persists | `kill -9 <pids>` |
| 3 | Chrome helper PIDs for forgotten tabs | N GB | list tabs first, user picks | AppleScript tab list |
| 4 | PyCharm if open | ~3 GB | loses unsaved buffers — ask | graceful quit → force |

Each row has a one-line safety note: why it's safe, what's lost, reversal path.

## Safe-kill playbook

### Docker Desktop
```bash
osascript -e 'tell application "Docker" to quit'
sleep 3
pkill -9 -f 'com.docker'
pkill -9 -f 'Docker.app'
```
Reversal: open Docker.app. Containers/images/volumes on disk persist — only the VM's RAM allocation is freed.

### Suspended claude (T-state)
```bash
kill -9 <pid1> <pid2> ...
```
Reversal: `cd <project-dir> && claude --resume <session-id>`. Session IDs are in the snapshot file.

### PyCharm when a save dialog blocks `osascript` quit
```bash
osascript -e 'tell application "PyCharm" to quit'   # try graceful first
pkill -9 -f 'PyCharm.app'                           # if blocked by dialog
pkill -9 -f 'JetBrains'                             # helpers + indexer
```
**Warning**: force-kill loses unsaved editor buffers. Always ask first.

### Chrome helpers
Never kill by PID blind — they map to tabs. Ask the user which tabs matter:
```bash
osascript -e 'tell application "Google Chrome" to get title of every tab of every window'
```
Let them close from the UI or quit Chrome entirely.

### Stale dev servers
Always ask. Name the command line so the user recognizes it.

## What NOT to kill (refuse even if asked)

- `WindowServer` — desktop freezes, hard-reboot required
- `launchd` (PID 1) — kernel panic
- `kernel_task` — synthetic; high usage = thermal throttling, not a killable process
- `coreaudiod`, `WindowManager`, `loginwindow`, `Finder` — system UI
- Anything root-owned in `/System/` or `/usr/libexec/`

If the user insists, explain: killing these requires a restart. Offer to help restart cleanly instead.

## Output style

Narrow markdown tables. Before/after real-usage comparison (active+wired, swap, compressed) after any kill. The user reads these while watching fans — keep it tight.

## Common patterns

- Running many parallel claude sessions across project dirs is normal. Each active session ~1-2 GB RSS. High count is not a problem in itself.
- Docker krun has been observed to grow 17 → 29 GB in 3 hours when idle. Recommend quitting Docker unless actively used.
- Session snapshots live at `$MAC_HEALTH_SNAP_DIR` (default `~/.session-snapshots/`). Reference by filename after crashes — feed session IDs to the `restore` skill.
- VPN clients with deep-packet "threat protection" features have been known to cause kernel instability. If you see a VPN client consuming abnormally, consider disabling its threat-protection mode.
