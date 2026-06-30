#!/usr/bin/env python3
"""
Claude Code Session Survey Tool
Scans ~/.claude/projects/ for recent sessions, extracts synopses,
and optionally checks tmux process status.

Usage:
    python3 survey_sessions.py                    # Last 7 days, all projects
    python3 survey_sessions.py --days 14          # Last 14 days
    python3 survey_sessions.py --project myapp    # Filter by project name
    python3 survey_sessions.py --today            # Today only
    python3 survey_sessions.py --tmux             # Include tmux window status
    python3 survey_sessions.py --top 5            # Top N sessions per project
    python3 survey_sessions.py --json             # JSON output for piping
"""

import json
import os
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path


PROJECTS_DIR = Path.home() / ".claude" / "projects"

# Map encoded directory names to real paths
def build_dir_map():
    mapping = {}
    if not PROJECTS_DIR.exists():
        return mapping
    for d in PROJECTS_DIR.iterdir():
        if d.is_dir():
            real = d.name.replace("-", "/", 1)  # First dash is root /
            # Reconstruct: -Users-you-foo-bar -> /Users/you/foo/bar
            parts = d.name.split("-")
            # Rebuild path from parts (first element is empty due to leading -)
            if len(parts) > 1:
                real = "/" + "/".join(parts[1:])
            mapping[d.name] = real
    return mapping


def extract_first_user_message(fpath, max_lines=100):
    """Extract the first meaningful user message from a session file."""
    try:
        with open(fpath, "r") as f:
            for i, line in enumerate(f):
                if i > max_lines:
                    break
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line)
                    if entry.get("type") == "user":
                        msg = entry.get("message", {})
                        content = msg.get("content", "")
                        text = ""
                        if isinstance(content, str):
                            text = content
                        elif isinstance(content, list):
                            for item in content:
                                if isinstance(item, dict) and item.get("type") == "text":
                                    text = item["text"]
                                    break
                        text = text.strip()
                        # Skip empty, slash commands, and system messages
                        if (
                            text
                            and len(text) > 10
                            and not text.startswith("/resume")
                            and not text.startswith("<local-command")
                            and not text.startswith("<command-")
                        ):
                            return text.replace("\n", " ")[:150]
                except (json.JSONDecodeError, KeyError):
                    pass
    except (OSError, IOError):
        pass
    return None


def count_user_messages(fpath, max_lines=5000):
    """Count user messages in a session file (samples first N lines)."""
    count = 0
    try:
        with open(fpath, "r") as f:
            for i, line in enumerate(f):
                if i > max_lines:
                    break
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line)
                    if entry.get("type") == "user":
                        count += 1
                except (json.JSONDecodeError, KeyError):
                    pass
    except (OSError, IOError):
        pass
    return count


def get_tmux_status():
    """Get tmux window status for all sessions."""
    status = {}
    try:
        result = subprocess.run(
            [
                "tmux",
                "list-panes",
                "-a",
                "-F",
                "#{session_name}|#{window_index}|#{window_name}|#{pane_pid}",
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            for line in result.stdout.strip().split("\n"):
                parts = line.split("|")
                if len(parts) >= 4:
                    session, idx, name, pid = parts[0], parts[1], parts[2], parts[3]
                    # Check if claude is running as child
                    ps = subprocess.run(
                        ["pgrep", "-P", pid], capture_output=True, text=True
                    )
                    has_claude = bool(ps.stdout.strip())
                    status[f"{session}:{name}"] = {
                        "session": session,
                        "window": idx,
                        "name": name,
                        "pid": pid,
                        "claude_running": has_claude,
                    }
    except FileNotFoundError:
        pass  # tmux not installed
    return status


def scan_sessions(days=7, project_filter=None, today_only=False, top_n=None):
    """Scan all project directories for recent sessions."""
    dir_map = build_dir_map()

    if today_only:
        cutoff = datetime.now().replace(hour=0, minute=0, second=0).timestamp()
    else:
        cutoff = time.time() - (days * 86400)

    results = defaultdict(list)

    for proj_dir in PROJECTS_DIR.iterdir():
        if not proj_dir.is_dir():
            continue

        real_path = dir_map.get(proj_dir.name, proj_dir.name)
        short_path = real_path.replace(str(Path.home()) + "/", "~/")

        # Apply project filter
        if project_filter and project_filter.lower() not in short_path.lower():
            continue

        for fname in proj_dir.iterdir():
            if not fname.suffix == ".jsonl" or fname.is_dir():
                continue

            try:
                mtime = fname.stat().st_mtime
            except OSError:
                continue

            if mtime < cutoff:
                continue

            session_id = fname.stem
            size_mb = fname.stat().st_size / (1024 * 1024)

            # Skip tiny sessions (likely empty/abandoned)
            if size_mb < 0.001:
                continue

            synopsis = extract_first_user_message(str(fname))
            user_msg_count = count_user_messages(str(fname))

            # Skip sessions with no real user interaction
            if user_msg_count < 1:
                continue

            results[short_path].append(
                {
                    "session_id": session_id,
                    "real_path": real_path,
                    "mtime": mtime,
                    "time": datetime.fromtimestamp(mtime).strftime("%b %d %H:%M"),
                    "date": datetime.fromtimestamp(mtime).strftime("%Y-%m-%d"),
                    "size_mb": size_mb,
                    "user_msgs": user_msg_count,
                    "synopsis": synopsis or "(no synopsis)",
                }
            )

    # Sort each project's sessions by mtime desc
    for proj in results:
        results[proj].sort(key=lambda x: x["mtime"], reverse=True)
        if top_n:
            results[proj] = results[proj][:top_n]

    return dict(results)


def format_table(results, include_tmux=False):
    """Format results as readable tables."""
    tmux_status = get_tmux_status() if include_tmux else {}

    # Sort projects by most recent session
    sorted_projects = sorted(
        results.keys(), key=lambda p: results[p][0]["mtime"], reverse=True
    )

    total_sessions = sum(len(v) for v in results.values())
    total_mb = sum(s["size_mb"] for v in results.values() for s in v)

    lines = []
    lines.append(f"## Claude Code Session Survey")
    lines.append(
        f"**{total_sessions} sessions** across **{len(results)} projects** | {total_mb:.0f} MB total"
    )
    lines.append("")

    for proj in sorted_projects:
        sessions = results[proj]
        proj_mb = sum(s["size_mb"] for s in sessions)
        lines.append(f"### {proj} ({len(sessions)} sessions, {proj_mb:.1f} MB)")
        lines.append("")
        lines.append("| Time | Size | Msgs | Synopsis |")
        lines.append("|------|------|------|----------|")

        for s in sessions:
            size_str = f"{s['size_mb']:.1f}MB"
            synopsis = s["synopsis"][:75]

            # Add tmux indicator if requested
            tmux_indicator = ""
            if include_tmux:
                for key, ts in tmux_status.items():
                    if ts["claude_running"]:
                        tmux_indicator = " [LIVE]"
                        break

            lines.append(
                f"| {s['time']} | {size_str} | {s['user_msgs']} | {synopsis}{tmux_indicator} |"
            )

        lines.append("")
        # Resume command
        real = sessions[0]["real_path"]
        lines.append(f"```bash")
        lines.append(f"cd {real} && claude --resume")
        lines.append(f"```")
        lines.append("")

    return "\n".join(lines)


def format_resume_commands(results):
    """Generate copy-pasteable resume commands for all sessions."""
    lines = ["## Resume Commands\n"]

    sorted_projects = sorted(
        results.keys(), key=lambda p: results[p][0]["mtime"], reverse=True
    )

    for proj in sorted_projects:
        sessions = results[proj]
        lines.append(f"### {proj}\n")
        for s in sessions:
            synopsis_short = s["synopsis"][:60]
            lines.append(f"# {s['time']} | {synopsis_short}")
            lines.append(
                f"cd {s['real_path']} && claude --resume {s['session_id']}\n"
            )

    return "\n".join(lines)


def _parse_pick_selectors(pick):
    """Parse pick selectors into {project_keyword: set_of_indices or None}."""
    pick_map = {}
    if pick:
        for selector in pick:
            if ":" in selector:
                proj_key, nums = selector.split(":", 1)
                indices = set()
                for part in nums.split(","):
                    part = part.strip()
                    if "-" in part:
                        lo, hi = part.split("-", 1)
                        indices.update(range(int(lo), int(hi) + 1))
                    elif part.isdigit():
                        indices.add(int(part))
                pick_map[proj_key.lower()] = indices
            else:
                pick_map[selector.lower()] = None
    return pick_map


def _collect_restore_sessions(results, pick=None):
    """Collect sessions to restore, applying pick filter. Returns list of (proj, i, session, real_path)."""
    pick_map = _parse_pick_selectors(pick)
    sorted_projects = sorted(
        results.keys(), key=lambda p: results[p][0]["mtime"], reverse=True
    )
    selected = []
    skipped = 0
    for proj in sorted_projects:
        sessions = results[proj]
        real_path = sessions[0]["real_path"]
        for i, s in enumerate(sessions, 1):
            if pick_map:
                matched = False
                for key, indices in pick_map.items():
                    if key in proj.lower():
                        if indices is None or i in indices:
                            matched = True
                        break
                if not matched:
                    skipped += 1
                    continue
            selected.append((proj, i, s, real_path))
    return selected, skipped


def write_restore_script(results, safe_mode=False, pick=None, output_path="/tmp/open_sessions.scpt"):
    """Write an AppleScript file that opens sessions in iTerm2 tabs.

    This avoids the sandbox timeout issue when Claude Code tries to run
    osascript inline — the user runs the .scpt file from their own terminal.
    """
    flags = "" if safe_mode else " --dangerously-skip-permissions"
    selected, skipped = _collect_restore_sessions(results, pick)

    if not selected:
        print("No sessions matched the filter.")
        return None

    lines = ['tell application "iTerm2"', '    tell current window']
    for proj, i, s, real_path in selected:
        cmd = f"cd {real_path} && claude --resume {s['session_id']}{flags}"
        lines.append('        create tab with default profile')
        lines.append('        tell current session of current tab')
        lines.append(f'            write text "{cmd}"')
        lines.append('        end tell')
    lines.append('    end tell')
    lines.append('end tell')

    script_content = "\n".join(lines) + "\n"
    with open(output_path, "w") as f:
        f.write(script_content)

    print(f"Wrote {len(selected)} session restore commands to {output_path}")
    if skipped:
        print(f"  ({skipped} sessions skipped by filter)")
    print(f"\nRun from your terminal (outside Claude Code):")
    print(f"  osascript {output_path}")
    return output_path


def restore_iterm_tabs(results, safe_mode=False, dry_run=False, pick=None):
    """Open each session in a new iTerm2 tab with correct cd and claude --resume.

    NOTE: When run from within Claude Code, osascript may timeout due to sandbox
    restrictions on iTerm2 automation. In that case, use --write-script instead
    to generate a .scpt file the user can run from their own terminal.
    """
    flags = "" if safe_mode else " --dangerously-skip-permissions"
    selected, skipped = _collect_restore_sessions(results, pick)

    opened = []

    for proj, i, s, real_path in selected:
        cmd = f"cd {real_path} && claude --resume {s['session_id']}{flags}"

        if dry_run:
            synopsis_short = s["synopsis"][:50]
            print(f"# {proj} #{i}: {synopsis_short}")
            print(f"{cmd}\n")
            opened.append((proj, i, s))
            continue

        # Build osascript — shell variable ensures cd + resume in one string
        osa_result = subprocess.run(
            ["bash", "-c", f'''
FULL="cd {real_path} && claude --resume {s['session_id']}{flags}"
osascript <<APPLESCRIPT
tell application "iTerm2"
    tell current window
        create tab with default profile
        tell current session of current tab
            write text "$FULL"
        end tell
    end tell
end tell
APPLESCRIPT
'''],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if osa_result.returncode == 0:
            opened.append((proj, i, s))
        else:
            err = osa_result.stderr.strip()
            print(f"ERROR opening {proj} #{i}: {err}")
            # If first tab fails, likely sandbox issue — fall back to write-script
            if not opened and ("not allowed" in err.lower() or "timeout" in err.lower()):
                print("\nSandbox detected. Falling back to --write-script mode...")
                return write_restore_script(results, safe_mode=safe_mode, pick=pick)

        # Small delay between tabs to avoid iTerm race conditions
        time.sleep(0.3)

    # Summary
    if not dry_run and opened:
        print(f"\nOpened {len(opened)} iTerm tab(s):")
        for proj, i, s in opened:
            synopsis_short = s["synopsis"][:50]
            print(f"  {proj} #{i}: {synopsis_short}")
    if skipped and not dry_run:
        print(f"  ({skipped} sessions skipped by filter)")

    return opened


def format_tmux_launcher(results, session_name="recovery"):
    """Generate a tmux launcher script."""
    lines = [
        "#!/bin/bash",
        f"# Auto-generated tmux recovery script",
        f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
    ]

    sorted_projects = sorted(
        results.keys(), key=lambda p: results[p][0]["mtime"], reverse=True
    )

    for proj in sorted_projects:
        sessions = results[proj]
        tmux_session = proj.replace("~/", "").replace("/", "-") or "home"

        for i, s in enumerate(sessions):
            # Create short window name from synopsis
            words = s["synopsis"].split()[:3]
            window_name = "-".join(w.lower()[:8] for w in words if w.isalnum())[:20]
            if not window_name:
                window_name = f"session-{i}"

            if i == 0:
                lines.append(
                    f'tmux new-session -d -s "{tmux_session}" -n "{window_name}" -c "{s["real_path"]}"'
                )
            else:
                lines.append(
                    f'tmux new-window -t "{tmux_session}" -n "{window_name}" -c "{s["real_path"]}"'
                )
            lines.append(
                f'tmux send-keys -t "{tmux_session}:{window_name}" "claude --resume {s["session_id"]}" Enter'
            )
            lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Survey Claude Code sessions")
    parser.add_argument("--days", type=int, default=7, help="Look back N days")
    parser.add_argument("--today", action="store_true", help="Today only")
    parser.add_argument("--project", type=str, help="Filter by project name")
    parser.add_argument(
        "--top", type=int, help="Show top N sessions per project"
    )
    parser.add_argument(
        "--tmux", action="store_true", help="Include tmux process status"
    )
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument(
        "--resume-cmds", action="store_true", help="Output resume commands"
    )
    parser.add_argument(
        "--tmux-script",
        type=str,
        metavar="NAME",
        help="Generate tmux launcher script",
    )
    parser.add_argument(
        "--restore",
        nargs="*",
        metavar="PICK",
        help="Open sessions in new iTerm tabs. Optional: project:N selectors (e.g. myapp:1,2,3 backend:1-5). Default: all sessions, dangerous mode.",
    )
    parser.add_argument(
        "--safe",
        action="store_true",
        help="With --restore: omit --dangerously-skip-permissions",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="With --restore: print commands without executing",
    )
    parser.add_argument(
        "--write-script",
        type=str,
        nargs="?",
        const="/tmp/open_sessions.scpt",
        metavar="PATH",
        help="Write AppleScript to file instead of executing (default: /tmp/open_sessions.scpt). Use when osascript is blocked by sandbox.",
    )

    args = parser.parse_args()

    results = scan_sessions(
        days=args.days,
        project_filter=args.project,
        today_only=args.today,
        top_n=args.top,
    )

    if not results:
        print("No sessions found matching criteria.")
        sys.exit(0)

    if args.write_script is not None:
        pick = args.restore if (args.restore is not None and args.restore) else None
        write_restore_script(
            results,
            safe_mode=args.safe,
            pick=pick,
            output_path=args.write_script,
        )
    elif args.restore is not None:
        pick = args.restore if args.restore else None
        restore_iterm_tabs(
            results,
            safe_mode=args.safe,
            dry_run=args.dry_run,
            pick=pick,
        )
    elif args.json:
        # Make JSON serializable
        for proj in results:
            for s in results[proj]:
                s.pop("mtime", None)
        print(json.dumps(results, indent=2))
    elif args.resume_cmds:
        print(format_resume_commands(results))
    elif args.tmux_script:
        print(format_tmux_launcher(results, args.tmux_script))
    else:
        print(format_table(results, include_tmux=args.tmux))
