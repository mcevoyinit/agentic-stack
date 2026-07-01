#!/usr/bin/env python3
"""
Iterate through recent X bookmarks by opening each one in its own
new Claude Code session in an iTerm2 tab.

Pulls inputs from your X bookmarks and opens each in a fresh Claude
session (--write-script). Each spawned tab also gets the FULL
conversation thread (replies, sub-tweets) — not just the bookmarked
tweet.

Configuration (env vars):
  X_BOOKMARK_FETCHER  Path to a Node script that exports your bookmarks
                      to a bookmarks-*.json file. See /x-bookmark-export-cdp
                      for the CDP-based fetcher pattern. If unset, run with
                      --cached or --from-json against an existing export.
  X_BOOKMARK_DIR      Dir holding bookmarks-*.json exports (default
                      ~/x-bookmarks).

Pipeline:
  1. Either fetch fresh bookmarks via $X_BOOKMARK_FETCHER OR reuse the
     most recent bookmarks-*.json in $X_BOOKMARK_DIR.
  2. Take the top N (X returns newest-bookmarked first).
  3. Fetch each bookmark's full conversation thread via fetch_threads.mjs
     (TweetDetail GraphQL, same CDP credential-discovery technique).
  4. Flatten each thread into a readable transcript.
  5. Generate an AppleScript that opens N iTerm tabs, each starting
     a fresh `claude` session prefilled with the bookmark URL +
     author + flattened thread + path to raw thread JSON.

Usage:
    python3 iterate_bookmarks.py                   # 10 newest, fresh fetch
    python3 iterate_bookmarks.py 5                 # 5 newest
    python3 iterate_bookmarks.py 10 --cached       # reuse last JSON, no Chrome launch
    python3 iterate_bookmarks.py 10 --no-threads   # skip thread fetch (faster)
    python3 iterate_bookmarks.py 10 --dry-run      # print what would open, don't write script
    python3 iterate_bookmarks.py --cwd ~/x-bookmarks
"""

import argparse
import glob
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent
BOOKMARK_DIR = Path(os.environ.get("X_BOOKMARK_DIR", str(Path.home() / "x-bookmarks")))
_fetcher = os.environ.get("X_BOOKMARK_FETCHER")
FETCH_BOOKMARKS_SCRIPT = Path(_fetcher).expanduser() if _fetcher else None
FETCH_THREADS_SCRIPT = SKILL_DIR / "fetch_threads.mjs"
# per-user temp dir (private on macOS), not world-writable /tmp
THREAD_CACHE_DIR = Path(tempfile.gettempdir()) / "bookmark-threads"


# ---------- bookmark JSON sourcing ----------

def latest_bookmarks_json():
    files = sorted(glob.glob(str(BOOKMARK_DIR / "bookmarks-*.json")), reverse=True)
    return files[0] if files else None


def fetch_fresh_bookmarks():
    if not FETCH_BOOKMARKS_SCRIPT or not FETCH_BOOKMARKS_SCRIPT.exists():
        sys.exit("No bookmark fetcher configured. Set $X_BOOKMARK_FETCHER to a "
                 "Node script that exports bookmarks-*.json (see "
                 "/x-bookmark-export-cdp), or run with --cached / --from-json.")
    print(f"Fetching fresh X bookmarks via CDP ({FETCH_BOOKMARKS_SCRIPT})...", flush=True)
    r = subprocess.run(
        ["node", str(FETCH_BOOKMARKS_SCRIPT), "--export-only"],
        cwd=str(FETCH_BOOKMARKS_SCRIPT.parent),
    )
    if r.returncode != 0:
        sys.exit(f"Bookmark fetch failed (exit {r.returncode}).")
    path = latest_bookmarks_json()
    if not path:
        sys.exit("Fetch reported success but no bookmarks-*.json was written.")
    return path


# ---------- bookmark extraction ----------

def extract_bookmark(item):
    """Pull (id, screen_name, url, text, conversation_id) from one tweet result."""
    rest_id = item.get("rest_id")
    user = (
        item.get("core", {})
        .get("user_results", {})
        .get("result", {})
    )
    screen = (
        user.get("core", {}).get("screen_name")
        or user.get("legacy", {}).get("screen_name")
        or ""
    )
    legacy = item.get("legacy", {}) or {}
    text = legacy.get("full_text", "")
    note = (
        item.get("note_tweet", {})
        .get("note_tweet_results", {})
        .get("result", {})
        .get("text")
    )
    if note:
        text = note
    url = f"https://x.com/{screen}/status/{rest_id}" if (screen and rest_id) else ""
    text = (text or "").replace("\n", " ").strip()
    return {
        "id": rest_id,
        "screen_name": screen,
        "url": url,
        "text": text,
        "conversation_id": legacy.get("conversation_id_str"),
    }


# ---------- thread fetching + flattening ----------

def fetch_threads(ids, force=False):
    """Run fetch_threads.mjs for the given tweet IDs. Returns the cache dir."""
    THREAD_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    args = ["node", str(FETCH_THREADS_SCRIPT),
            "--ids", ",".join(ids),
            "--out", str(THREAD_CACHE_DIR)]
    if force:
        args.append("--force")
    r = subprocess.run(args)
    if r.returncode != 0:
        print("⚠ Thread fetch failed; continuing without threads.", file=sys.stderr)
    return THREAD_CACHE_DIR


def _walk_tweet_results(node, out):
    """Depth-first walk of a TweetDetail response, collecting tweet_results."""
    if isinstance(node, dict):
        # tweet_results -> { result: {...} } pattern
        if "tweet_results" in node and isinstance(node["tweet_results"], dict):
            r = node["tweet_results"].get("result")
            if isinstance(r, dict) and r.get("rest_id"):
                out.append(r)
        for v in node.values():
            _walk_tweet_results(v, out)
    elif isinstance(node, list):
        for v in node:
            _walk_tweet_results(v, out)


def flatten_thread(thread_json_path, focal_id, max_chars=4000):
    """Read a TweetDetail JSON and return a compact readable transcript.

    Returns (transcript_str, tweet_count). Limited to max_chars so we
    don't overflow the shell command line.
    """
    try:
        with open(thread_json_path) as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return ("", 0)

    tweets = []
    _walk_tweet_results(data, tweets)

    # Dedupe by rest_id, preserve discovery order
    seen = set()
    uniq = []
    for t in tweets:
        rid = t.get("rest_id")
        if rid and rid not in seen:
            seen.add(rid)
            uniq.append(t)

    # Bring focal tweet to top, then sort the rest by created_at if available
    def created_at(t):
        return (t.get("legacy") or {}).get("created_at", "")

    focal = [t for t in uniq if t.get("rest_id") == focal_id]
    others = [t for t in uniq if t.get("rest_id") != focal_id]
    others.sort(key=created_at)
    ordered = focal + others

    lines = []
    for t in ordered:
        rid = t.get("rest_id", "")
        legacy = t.get("legacy") or {}
        user = ((t.get("core") or {}).get("user_results") or {}).get("result") or {}
        screen = (user.get("core") or {}).get("screen_name") or (user.get("legacy") or {}).get("screen_name") or "?"
        text = legacy.get("full_text") or ""
        note = ((t.get("note_tweet") or {}).get("note_tweet_results") or {}).get("result", {}).get("text")
        if note:
            text = note
        text = text.replace("\n", " ").strip()
        marker = "★" if rid == focal_id else " "
        lines.append(f"{marker} @{screen} ({rid}): {text}")

    transcript = "\n".join(lines)
    if len(transcript) > max_chars:
        transcript = transcript[:max_chars] + " …[truncated]"
    return (transcript, len(ordered))


# ---------- prompt + script generation ----------

def build_initial_prompt(b, transcript, thread_path, max_text=400):
    snippet = b["text"][:max_text]
    parts = [
        "I bookmarked this on X. Help me think about it / decide if there's a follow-up.",
    ]
    if b["url"]:
        parts.append(f"URL: {b['url']}")
    if b["screen_name"]:
        parts.append(f"Author: @{b['screen_name']}")
    if snippet:
        parts.append(f"Tweet: {snippet}")
    if transcript:
        parts.append(
            "Full thread (★ = bookmarked tweet, others are replies / context):\n"
            + transcript
        )
    if thread_path and os.path.exists(thread_path):
        parts.append(f"Raw TweetDetail JSON for deeper inspection: {thread_path}")
    return "\n\n".join(parts)


def shell_single_quote(s):
    """Wrap a string in single quotes safely for /bin/sh."""
    return "'" + s.replace("'", "'\\''") + "'"


def applescript_string_escape(s):
    """Escape backslash and double-quote for an AppleScript string literal."""
    return s.replace("\\", "\\\\").replace('"', '\\"')


def write_script(prompts, output_path, work_dir, safe_mode=False):
    """prompts: list of (bookmark, prompt_text). Writes the .scpt file."""
    flags = "" if safe_mode else " --dangerously-skip-permissions"
    work_dir_expanded = os.path.expanduser(work_dir)

    lines = ['tell application "iTerm2"', '    tell current window']
    for _, prompt in prompts:
        prompt_q = shell_single_quote(prompt)            # safe for shell
        cmd = f"cd {work_dir_expanded} && claude{flags} {prompt_q}"
        cmd_as = applescript_string_escape(cmd)          # safe for AppleScript string
        lines += [
            "        create tab with default profile",
            "        tell current session of current tab",
            f'            write text "{cmd_as}"',
            "        end tell",
        ]
    lines += ["    end tell", "end tell"]

    Path(output_path).write_text("\n".join(lines) + "\n")
    return output_path


# ---------- main ----------

def main():
    p = argparse.ArgumentParser(description="Open recent X bookmarks (with full threads) in new iTerm Claude tabs")
    p.add_argument("count", type=int, nargs="?", default=10,
                   help="Number of newest bookmarks to open (default: 10)")
    p.add_argument("--cached", action="store_true",
                   help="Reuse most recent bookmarks-*.json instead of fetching fresh")
    p.add_argument("--cwd", default=str(Path.home()),
                   help="Working directory for each spawned claude session")
    p.add_argument("--write-script",
                   default=str(Path(tempfile.gettempdir()) / "open_bookmarks.scpt"),
                   help="Where to write the AppleScript (default: open_bookmarks.scpt in your private temp dir)")
    p.add_argument("--safe", action="store_true",
                   help="Omit --dangerously-skip-permissions on the spawned claude")
    p.add_argument("--dry-run", action="store_true",
                   help="Print the bookmarks that would be opened and exit")
    p.add_argument("--from-json", help="Use a specific bookmarks JSON file (skip fetch)")
    p.add_argument("--no-threads", action="store_true",
                   help="Skip fetching full conversation threads (faster, less context)")
    p.add_argument("--refresh-threads", action="store_true",
                   help="Re-fetch threads even if already cached in the thread cache dir")
    p.add_argument("--max-thread-chars", type=int, default=4000,
                   help="Truncate flattened thread text at N chars (default: 4000)")
    args = p.parse_args()

    # 1. Source bookmarks JSON
    if args.from_json:
        json_path = args.from_json
    elif args.cached:
        json_path = latest_bookmarks_json()
        if not json_path:
            print("No cached bookmarks-*.json found, fetching fresh.", file=sys.stderr)
            json_path = fetch_fresh_bookmarks()
    else:
        json_path = fetch_fresh_bookmarks()

    with open(json_path) as f:
        items = json.load(f)

    # 2. Pick top N
    bookmarks = []
    for it in items:
        b = extract_bookmark(it)
        if b["id"]:
            bookmarks.append(b)
        if len(bookmarks) >= args.count:
            break

    if not bookmarks:
        sys.exit("No bookmarks extracted from JSON.")

    # 3. Fetch threads (unless skipped)
    if not args.no_threads:
        ids = [b["id"] for b in bookmarks]
        fetch_threads(ids, force=args.refresh_threads)

    # 4. Build prompts (with flattened thread transcripts)
    prompts = []
    for b in bookmarks:
        transcript, tweet_count = ("", 0)
        thread_path = str(THREAD_CACHE_DIR / f"{b['id']}.json")
        if not args.no_threads and os.path.exists(thread_path):
            transcript, tweet_count = flatten_thread(
                thread_path, b["id"], max_chars=args.max_thread_chars
            )
        b["_thread_count"] = tweet_count
        prompts.append((b, build_initial_prompt(b, transcript, thread_path)))

    if args.dry_run:
        print(f"Source bookmarks: {json_path}")
        print(f"Thread cache:     {THREAD_CACHE_DIR}")
        print(f"Would open {len(bookmarks)} tab(s):\n")
        for i, (b, prompt) in enumerate(prompts, 1):
            preview = b["text"][:90].replace("\n", " ")
            tc = b.get("_thread_count", 0)
            tc_str = f"[{tc} tweets in thread]" if tc else "[no thread]"
            print(f"  {i:>2}. @{b['screen_name']:<20} {tc_str:<20} {preview}")
            print(f"      {b['url']}")
        return

    # 5. Write iTerm script
    out = write_script(
        prompts,
        output_path=args.write_script,
        work_dir=args.cwd,
        safe_mode=args.safe,
    )
    print(f"Wrote {len(prompts)} bookmark commands to {out}")
    print(f"Source bookmarks: {json_path}")
    if not args.no_threads:
        print(f"Thread cache:     {THREAD_CACHE_DIR}")
    print(f"Run:   osascript {out}")


if __name__ == "__main__":
    main()
