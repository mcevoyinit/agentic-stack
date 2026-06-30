#!/usr/bin/env python3
"""
Sync session .jsonl files to sessions-index.json so /resume can find them.

Called from the Stop hook with --transcript <path> for targeted sync,
or with --scan <project-dir> for a full orphan scan.

The problem: Claude Code writes .jsonl transcripts but sometimes fails to
add them to sessions-index.json. /resume only searches the index, so
sessions silently disappear from /resume despite existing on disk.
"""
import json
import os
import sys
import glob
from datetime import datetime, timezone
from pathlib import Path


def read_session_metadata(jsonl_path: str) -> dict:
    """Extract metadata from a .jsonl transcript file."""
    first_prompt = ""
    msg_count = 0
    created = None
    git_branch = ""
    project_path = ""

    try:
        with open(jsonl_path) as f:
            for line in f:
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    continue
                msg_count += 1

                # First message is usually file-history-snapshot with timestamp
                if msg.get("type") == "file-history-snapshot" and not created:
                    snap = msg.get("snapshot", {})
                    ts = snap.get("timestamp")
                    if ts:
                        created = ts

                # Extract first user prompt
                if msg.get("type") == "user" and not first_prompt:
                    content = msg.get("message", {})
                    if isinstance(content, dict):
                        parts = content.get("content", [])
                        if isinstance(parts, list):
                            for p in parts:
                                if isinstance(p, dict) and p.get("type") == "text":
                                    first_prompt = p.get("text", "")[:200]
                                    break
                    elif isinstance(content, str):
                        first_prompt = content[:200]
    except Exception:
        pass

    stat = os.stat(jsonl_path)
    if not created:
        created = datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%S.000Z"
        )

    return {
        "firstPrompt": first_prompt,
        "messageCount": msg_count,
        "created": created,
        "modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%S.000Z"
        ),
        "fileMtime": int(stat.st_mtime * 1000),
    }


def ensure_in_index(project_dir: str, session_id: str, jsonl_path: str) -> bool:
    """Ensure a session is in sessions-index.json. Returns True if added."""
    index_path = os.path.join(project_dir, "sessions-index.json")

    # Read or create index
    if os.path.exists(index_path):
        with open(index_path) as f:
            data = json.load(f)
    else:
        data = {"version": 1, "entries": [], "originalPath": ""}

    # Check if already indexed
    indexed_ids = {e["sessionId"] for e in data["entries"]}
    if session_id in indexed_ids:
        return False

    # Read metadata from transcript
    meta = read_session_metadata(jsonl_path)

    entry = {
        "sessionId": session_id,
        "fullPath": jsonl_path,
        "fileMtime": meta["fileMtime"],
        "firstPrompt": meta["firstPrompt"],
        "summary": "",
        "messageCount": meta["messageCount"],
        "created": meta["created"],
        "modified": meta["modified"],
        "gitBranch": "",
        "projectPath": data.get("originalPath", ""),
        "isSidechain": False,
    }

    data["entries"].append(entry)

    with open(index_path, "w") as f:
        json.dump(data, f)

    return True


def sync_transcript(transcript_path: str):
    """Sync a single transcript to its project's index."""
    transcript_path = os.path.abspath(transcript_path)
    project_dir = os.path.dirname(transcript_path)
    basename = os.path.basename(transcript_path)

    if not basename.endswith(".jsonl"):
        return

    session_id = basename.replace(".jsonl", "")

    if ensure_in_index(project_dir, session_id, transcript_path):
        print(f"indexed {session_id[:8]}", file=sys.stderr)


def scan_project(project_dir: str):
    """Scan a project directory for orphaned sessions and index them."""
    project_dir = os.path.abspath(project_dir)
    index_path = os.path.join(project_dir, "sessions-index.json")

    if not os.path.exists(index_path):
        return

    with open(index_path) as f:
        data = json.load(f)

    indexed_ids = {e["sessionId"] for e in data["entries"]}
    jsonl_files = glob.glob(os.path.join(project_dir, "*.jsonl"))
    added = 0

    for fpath in jsonl_files:
        sid = os.path.basename(fpath).replace(".jsonl", "")
        if sid not in indexed_ids:
            if ensure_in_index(project_dir, sid, fpath):
                added += 1

    if added:
        print(f"indexed {added} orphaned sessions in {project_dir}", file=sys.stderr)


def scan_all_projects():
    """Scan all project directories for orphaned sessions."""
    claude_dir = Path.home() / ".claude" / "projects"
    if not claude_dir.exists():
        return

    for project_dir in claude_dir.iterdir():
        if project_dir.is_dir():
            index_path = project_dir / "sessions-index.json"
            if index_path.exists():
                scan_project(str(project_dir))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        scan_all_projects()
    elif sys.argv[1] == "--transcript" and len(sys.argv) > 2:
        sync_transcript(sys.argv[2])
    elif sys.argv[1] == "--scan" and len(sys.argv) > 2:
        scan_project(sys.argv[2])
    elif sys.argv[1] == "--all":
        scan_all_projects()
    else:
        print(f"Usage: {sys.argv[0]} [--transcript <path> | --scan <dir> | --all]")
        sys.exit(1)
