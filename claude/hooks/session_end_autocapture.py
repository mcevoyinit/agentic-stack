#!/usr/bin/env python3
"""
session_end_autocapture.py — heuristic session-end auto-capture, fired by
a SessionEnd hook.

Reads a JSONL transcript, detects mode + stats, auto-writes safe outputs
(a snapshot markdown file, todo-list appends), and queues anything that
looks medium/high stakes to $CLAUDE_PENDING_DIR/{ts}.json for human
review at the start of the next session (pair this with a review skill
of your own, e.g. a "/wrap pending" style command).

Design rules:
- No LLM calls. Heuristic only. Smart analysis belongs in your review
  skill, not here.
- Degrades silently. Never raises past main(). Always exits 0.
- Skips subagent transcripts and trivial sessions (<3 user turns or <2
  min).
- Never writes to your memory/notes system directly — queue it for
  human review instead.

CLI:
    session_end_autocapture.py <transcript_path>

Configure via env vars (all optional, sane defaults shown):
    CLAUDE_SNAPSHOT_DIR   default ~/.claude-snapshots
    CLAUDE_TODO_FILE      default ~/todo.md
    CLAUDE_PENDING_DIR    default ~/.claude-snapshots/.pending
    CLAUDE_HOOK_LOG       default ~/.claude/hooks/session_end_autocapture.log
"""
from __future__ import annotations

import json
import os
import re
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

HOME = Path.home()
SNAPSHOT_DIR = Path(os.environ.get("CLAUDE_SNAPSHOT_DIR", HOME / ".claude-snapshots"))
TODO_FILE = Path(os.environ.get("CLAUDE_TODO_FILE", HOME / "todo.md"))
PENDING_DIR = Path(os.environ.get("CLAUDE_PENDING_DIR", SNAPSHOT_DIR / ".pending"))
LOG_FILE = Path(os.environ.get("CLAUDE_HOOK_LOG", HOME / ".claude" / "hooks" / "session_end_autocapture.log"))

MIN_USER_TURNS = 3
MIN_DURATION_SEC = 120

FILE_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}

MODE_KEYWORDS = {
    "DONE": [
        "ship it", "perfect", "looks good", "all done", "we're done",
        "great work", "excellent", "let's go", "let's do it", "approved",
        "sounds good", "lgtm", "ready to ship", "merge it",
    ],
    "PAUSE": [
        "wrap this", "wrap it", "wrap up", "let's wrap",
        "pick up tomorrow", "continue tomorrow", "later", "leave it for now",
        "pause here", "park this", "come back to",
    ],
    "BLOCKED": [
        "stuck", "don't know how", "can't get this", "not working",
        "blocked on", "waiting on", "need help with", "hit a wall",
    ],
    "ABANDONED": [
        "drop it", "forget it", "scratch that", "different approach",
        "let's try something else", "abandon", "give up on this",
    ],
}

REMINDER_TRIGGERS = [
    r"remind me to (.+?)(?:[.!?\n]|$)",
    r"remind me about (.+?)(?:[.!?\n]|$)",
    r"put (.+?) on my (?:list|todo)",
    r"add (.+?) to my (?:list|todo)",
    r"don't let me forget (?:to )?(.+?)(?:[.!?\n]|$)",
    r"i need to (.+?) (?:tomorrow|today|on \w+|by \w+)",
]

INSIGHT_PATTERNS = [
    (r"\bremember that\s+(.+?)(?:[.!?\n]|$)", "feedback", "explicit"),
    (r"\bnote that\s+(.+?)(?:[.!?\n]|$)", "feedback", "explicit"),
    (r"\bthe reason (?:is|we|i|that)\s+(.+?)(?:[.!?\n]|$)", "project", "rationale"),
    (r"\bbecause we (?:need|want|have)\s+(.+?)(?:[.!?\n]|$)", "project", "rationale"),
    (r"\bnever (?:do |use |touch |publish )(.+?)(?:[.!?\n]|$)", "feedback", "prohibition"),
]

DEAD_END_PATTERNS = [
    r"didn'?t work",
    r"doesn'?t work",
    r"that failed",
    r"this approach failed",
    r"not the right approach",
]

SCHEDULE_SIGNALS = [
    "feature flag", "soak window", "in two weeks", "in 2 weeks",
    "in three weeks", "in 3 weeks", "remove once", "weekly sweep",
    "weekly review", "monthly", "bi-weekly", "biweekly",
]


def is_pasted_content(msg: str) -> bool:
    """Detect slash command invocations or pasted skill/spec content (not real user input)."""
    if not msg:
        return True
    markers = (
        "Base directory for this skill:",
        "<command-name>",
        "<command-message>",
        "<system-reminder>",
    )
    if any(m in msg for m in markers):
        return True
    if msg.count("\n## ") >= 3 or msg.count("\n| ") >= 5:
        return True
    return False


def is_clean_claim(claim: str) -> bool:
    if len(claim) < 15:
        return False
    if "|" in claim or "```" in claim or claim.startswith(("-", "*", "#")):
        return False
    if claim.count(" ") < 2:
        return False
    return True


def format_duration(sec: float) -> str:
    if sec < 3600:
        return f"{int(sec/60)} min"
    if sec < 8 * 3600:
        return f"{sec/3600:.1f} h"
    if sec < 24 * 3600:
        return f"{sec/3600:.1f} h (long, possible multi sitting)"
    return f"{sec/(24*3600):.1f} d (multi day session, gap unknown)"


def log(msg: str) -> None:
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with LOG_FILE.open("a") as f:
            f.write(f"[{datetime.now().isoformat()}] {msg}\n")
    except Exception:
        pass


def parse_transcript(path: Path) -> dict:
    """Parse JSONL transcript, return structured session data."""
    user_messages: list[str] = []
    assistant_messages: list[str] = []
    tool_calls: list[dict] = []
    files_changed: dict[str, set[str]] = {}
    first_ts: float | None = None
    last_ts: float | None = None
    is_subagent = False
    session_id = ""

    with path.open("r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue

            if rec.get("isSidechain") or rec.get("subagent"):
                is_subagent = True

            if not session_id:
                session_id = rec.get("sessionId") or rec.get("session_id") or ""

            ts = rec.get("timestamp")
            if ts:
                try:
                    t = datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
                    if first_ts is None:
                        first_ts = t
                    last_ts = t
                except Exception:
                    pass

            mtype = rec.get("type")
            msg = rec.get("message") or {}
            content = msg.get("content")

            if mtype == "user":
                if isinstance(content, str):
                    user_messages.append(content)
                elif isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            user_messages.append(block.get("text", ""))
            elif mtype == "assistant":
                if isinstance(content, list):
                    for block in content:
                        if not isinstance(block, dict):
                            continue
                        btype = block.get("type")
                        if btype == "text":
                            assistant_messages.append(block.get("text", ""))
                        elif btype == "tool_use":
                            tname = block.get("name", "")
                            tinput = block.get("input", {}) or {}
                            tool_calls.append({"name": tname, "input": tinput})
                            if tname in FILE_TOOLS:
                                fp = tinput.get("file_path") or tinput.get("notebook_path")
                                if fp:
                                    files_changed.setdefault(fp, set()).add(tname)

    return {
        "session_id": session_id,
        "is_subagent": is_subagent,
        "user_messages": user_messages,
        "assistant_messages": assistant_messages,
        "tool_calls": tool_calls,
        "files_changed": {k: sorted(v) for k, v in files_changed.items()},
        "first_ts": first_ts,
        "last_ts": last_ts,
        "duration_sec": (last_ts - first_ts) if first_ts and last_ts else 0,
    }


def detect_mode(user_messages: list[str]) -> tuple[str, str]:
    clean = [m for m in user_messages if not is_pasted_content(m)]
    if not clean:
        return ("PARTIAL", "no clean user messages")

    last_n = " ".join(clean[-8:]).lower()
    scores = {mode: 0 for mode in MODE_KEYWORDS}
    matched: dict[str, list[str]] = {mode: [] for mode in MODE_KEYWORDS}

    for mode, kws in MODE_KEYWORDS.items():
        for kw in kws:
            if kw in last_n:
                scores[mode] += 1
                matched[mode].append(kw)

    top_mode = max(scores, key=scores.get)
    if scores[top_mode] == 0:
        return ("PARTIAL", "no mode keywords matched")

    reason = f"matched: {', '.join(matched[top_mode][:3])}"
    return (top_mode, reason)


def extract_action_items(user_messages: list[str]) -> list[str]:
    items: list[str] = []
    for msg in user_messages:
        if is_pasted_content(msg):
            continue
        for pattern in REMINDER_TRIGGERS:
            for m in re.finditer(pattern, msg, re.IGNORECASE):
                item = m.group(1).strip()
                if 5 <= len(item) <= 200 and " " in item:
                    items.append(item)
    return list(dict.fromkeys(items))


def extract_insights(user_messages: list[str]) -> list[dict]:
    insights: list[dict] = []
    for i, msg in enumerate(user_messages):
        if is_pasted_content(msg):
            continue
        for pattern, mtype, subtype in INSIGHT_PATTERNS:
            for m in re.finditer(pattern, msg, re.IGNORECASE):
                claim = m.group(1).strip()
                if not is_clean_claim(claim):
                    continue
                insights.append({
                    "type": mtype,
                    "subtype": subtype,
                    "claim_hint": claim[:300],
                    "raw": msg[:500],
                    "user_message_index": i,
                })
    seen = set()
    unique: list[dict] = []
    for ins in insights:
        key = (ins["type"], ins["claim_hint"][:80])
        if key not in seen:
            seen.add(key)
            unique.append(ins)
    return unique[:15]


def extract_dead_ends(user_messages: list[str], assistant_messages: list[str]) -> list[dict]:
    dead_ends: list[dict] = []
    pool = [m for m in user_messages if not is_pasted_content(m)]
    pool += [m for m in assistant_messages if not is_pasted_content(m)]
    for msg in pool:
        for pattern in DEAD_END_PATTERNS:
            if re.search(pattern, msg, re.IGNORECASE):
                dead_ends.append({"raw": msg[:400], "matched": pattern})
                break
    return dead_ends[:8]


def extract_schedule_signals(user_messages: list[str], assistant_messages: list[str]) -> list[str]:
    signals: list[str] = []
    pool = [m for m in user_messages + assistant_messages if not is_pasted_content(m)]
    haystack = " ".join(pool).lower()
    for sig in SCHEDULE_SIGNALS:
        if sig in haystack:
            signals.append(sig)
    return list(dict.fromkeys(signals))


def write_snapshot(snapshot_path: Path, data: dict, mode: str, mode_reason: str,
                   action_items: list[str], insights: list[dict],
                   dead_ends: list[dict], schedule_signals: list[str]) -> None:
    files_table = "\n".join(
        f"  | {fp} | {', '.join(tools)} |"
        for fp, tools in data["files_changed"].items()
    ) or "  (none)"

    actions_block = "\n".join(f"  · {item}" for item in action_items) or "  (none extracted)"
    insights_block = "\n".join(
        f"  [{ins['type']}] {ins['claim_hint'][:120]}"
        for ins in insights
    ) or "  (none extracted)"
    dead_ends_block = "\n".join(f"  · {de['raw'][:120]}" for de in dead_ends) or "  (none)"
    schedule_block = ", ".join(schedule_signals) or "(none)"

    duration_str = format_duration(data["duration_sec"])

    body = f"""# Auto session-end snapshot · {datetime.now().strftime('%Y-%m-%d %H:%M')}

Generated by a SessionEnd hook (heuristic only, no LLM).
Review pending items via your own review skill in the next session.

## Detected mode

{mode}  ({mode_reason})

## Stats

| Metric | Value |
|--------|-------|
| Session ID | {data['session_id'][:16]} |
| Duration | {duration_str} |
| User turns | {len(data['user_messages'])} |
| Assistant turns | {len(data['assistant_messages'])} |
| Tool calls | {len(data['tool_calls'])} |
| Files touched | {len(data['files_changed'])} |

## Files changed

  | File | Tools |
  |------|-------|
{files_table}

## Action items extracted (auto written to todo file)

{actions_block}

## Candidate insights (queued for human review)

{insights_block}

## Candidate dead ends (queued)

{dead_ends_block}

## Schedule signals detected

{schedule_block}

## Note

This snapshot is mechanical extraction. Real verdict, curated insights,
and any memory writes belong in your own review skill, not this hook.
"""
    snapshot_path.write_text(body)


def append_todos(items: list[str]) -> int:
    if not items:
        return 0
    if not TODO_FILE.exists():
        return 0
    text = TODO_FILE.read_text()
    if "## Open (no date)" not in text:
        return 0
    new_lines = [f"- [ ] {item}  (auto extracted)" for item in items]
    insertion = "\n".join(new_lines) + "\n"
    text = text.replace("## Open (no date)\n", f"## Open (no date)\n{insertion}", 1)
    TODO_FILE.write_text(text)
    return len(items)


def write_pending(pending_path: Path, payload: dict) -> None:
    pending_path.parent.mkdir(parents=True, exist_ok=True)
    pending_path.write_text(json.dumps(payload, indent=2, default=str))


def main() -> int:
    try:
        if len(sys.argv) < 2:
            log("no transcript path argv")
            return 0

        transcript_path = Path(sys.argv[1])
        if not transcript_path.exists():
            log(f"transcript not found: {transcript_path}")
            return 0

        data = parse_transcript(transcript_path)

        if data["is_subagent"]:
            log(f"skip subagent: {transcript_path.name}")
            return 0

        if len(data["user_messages"]) < MIN_USER_TURNS:
            log(f"skip trivial (turns={len(data['user_messages'])}): {transcript_path.name}")
            return 0

        if data["duration_sec"] < MIN_DURATION_SEC:
            log(f"skip short (sec={int(data['duration_sec'])}): {transcript_path.name}")
            return 0

        mode, mode_reason = detect_mode(data["user_messages"])
        action_items = extract_action_items(data["user_messages"])
        insights = extract_insights(data["user_messages"])
        dead_ends = extract_dead_ends(data["user_messages"], data["assistant_messages"])
        schedule_signals = extract_schedule_signals(data["user_messages"], data["assistant_messages"])

        ts = datetime.now().strftime("%Y-%m-%d-%H%M")
        SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
        snapshot_path = SNAPSHOT_DIR / f"snapshot-{ts}.md"

        write_snapshot(snapshot_path, data, mode, mode_reason,
                       action_items, insights, dead_ends, schedule_signals)

        todos_appended = append_todos(action_items)

        pending_payload = {
            "schema_version": 1,
            "session_id": data["session_id"],
            "ended_at": datetime.now(timezone.utc).isoformat(),
            "transcript_path": str(transcript_path),
            "mode": mode,
            "mode_reason": mode_reason,
            "stats": {
                "duration_sec": int(data["duration_sec"]),
                "user_turns": len(data["user_messages"]),
                "assistant_turns": len(data["assistant_messages"]),
                "tool_calls": len(data["tool_calls"]),
                "files_touched": len(data["files_changed"]),
            },
            "files_changed": data["files_changed"],
            "snapshot_path": str(snapshot_path),
            "auto_writes": [
                f"snapshot: {snapshot_path}",
                f"todo file: {todos_appended} items appended",
            ],
            "candidate_insights": insights,
            "candidate_dead_ends": dead_ends,
            "schedule_signals": schedule_signals,
            "action_items_written": action_items,
        }

        pending_path = PENDING_DIR / f"{ts}.json"
        write_pending(pending_path, pending_payload)

        log(f"ok: mode={mode}, snapshot={snapshot_path.name}, "
            f"insights={len(insights)}, todos={todos_appended}")
        return 0

    except Exception:
        log("FAILED:\n" + traceback.format_exc())
        return 0


if __name__ == "__main__":
    sys.exit(main())
