---
name: x-bookmarks-iterate
description: |
  Iterate through your most recent X bookmarks by spawning one new Claude Code
  session per bookmark in its own iTerm2 tab. Each tab is prefilled with the
  bookmark URL, author, and the FULL conversation thread (replies + sub-tweets,
  not just the bookmarked post) so you can immediately discuss it.
  Trigger: "/x-bookmarks-iterate", "go through my bookmarks", "iterate bookmarks",
  "open recent x bookmarks".
args: "[count] [--cached] [--no-threads] [--cwd <dir>] [--dry-run]"
---

# Iterate Recent X Bookmarks

Bulk-open your N newest X bookmarks, one per Claude Code tab. Companion to
`/x-bookmark-export-cdp` (which fetches bookmarks) and any session-restore
skill (which opens iTerm tabs from session history).

> Setup note: this skill drives YOUR OWN logged-in X session via Chrome
> DevTools Protocol — it reads whatever account is signed into your local
> Chrome profile. No account handle or credentials are baked in. Point it at
> a bookmark-fetcher with the `X_BOOKMARK_FETCHER` env var (see below).

## Usage

```
/x-bookmarks-iterate                # 10 newest, fetch fresh + threads
/x-bookmarks-iterate 5              # 5 newest
/x-bookmarks-iterate 10 --cached    # reuse last bookmarks JSON
/x-bookmarks-iterate 10 --no-threads # skip thread fetch (faster, less context)
/x-bookmarks-iterate --dry-run      # print what would open
```

## What each spawned tab gets

Each new Claude session starts with a prompt containing:
- Bookmark URL (`https://x.com/<author>/status/<id>`)
- Author (`@screen_name`)
- The bookmarked tweet text
- **Flattened conversation thread**: every tweet in the reply tree, marked with
  ★ for the focal (bookmarked) tweet
- Path to the raw `TweetDetail` JSON (for deeper inspection)

## Implementation — FOLLOW EXACTLY

### Step 1: Generate the AppleScript

```bash
python3 ~/.claude/skills/x-bookmarks-iterate/iterate_bookmarks.py \
  <COUNT> \
  --write-script /tmp/open_bookmarks.scpt
```

Add `--cached` if the user already ran a fetch recently (skips ~30s Chrome
launch). Add `--no-threads` if the user wants speed over context. Default
behaviour: fetch fresh bookmarks AND fresh threads.

### Step 2: Execute it (background, no wait)

```bash
osascript /tmp/open_bookmarks.scpt &
```

Run with `run_in_background: true`. Do NOT wait, do NOT TaskOutput-check it.

### Step 3: Confirm to user

Tell the user how many tabs were opened. Done.

## Pipeline (under the hood)

```
bookmark fetcher (CDP) ──► bookmarks-<ts>.json ──► top N
   ($X_BOOKMARK_FETCHER)                              │
                                                      ▼
                                fetch_threads.mjs ──► /tmp/bookmark-threads/<id>.json
                                (TweetDetail GraphQL,
                                 same CDP technique,
                                 port 9235)
                                                      │
                                                      ▼
                                flatten_thread() ──► transcript per bookmark
                                                      │
                                                      ▼
                                write_script() ──► /tmp/open_bookmarks.scpt
                                                      │
                                                      ▼
                                osascript ──► N iTerm tabs running
                                              `claude --dangerously-skip-permissions '<prompt>'`
```

## Files

| File | Purpose |
|------|---------|
| `iterate_bookmarks.py` | Orchestrator: bookmarks → threads → prompts → AppleScript |
| `fetch_threads.mjs`    | Node CDP fetcher for X TweetDetail (full conversations) |
| `SKILL.md`             | This file |

## Configuration

| Env var | Default | Purpose |
|---------|---------|---------|
| `X_BOOKMARK_FETCHER` | (unset) | Path to a Node script that exports your bookmarks to `bookmarks-*.json`. See `/x-bookmark-export-cdp` for the CDP-based fetcher pattern. |
| `X_BOOKMARK_DIR` | `~/x-bookmarks` | Dir holding `bookmarks-*.json` exports |
| `--cwd` | `~` | Working directory baked into each spawned tab |

## Rules

- ALWAYS dangerous mode (no `--safe` flag) unless the user asks otherwise
- ALWAYS `cd <work-dir>` baked into each tab command (default: home dir)
- Execute the script — do NOT tell the user to run it manually
- Use `run_in_background: true` for the osascript call to avoid timeout
- Thread cache at `/tmp/bookmark-threads/` is reused across runs (idempotent);
  use `--refresh-threads` to force re-fetch

## Gotchas

- Both Node scripts launch a temp Chrome with the user's cookies. They use
  different debug ports (9234 for bookmarks, 9235 for threads) so they CAN
  run back-to-back, but not in parallel.
- TweetDetail credentials (QID + bearer + features) rotate just like Bookmarks
  — that's why we re-discover via CDP network interception each run rather than
  hardcoding.
- Long threads are truncated at 4000 chars in the prompt (raise via
  `--max-thread-chars`); the raw JSON path is always passed for full access.
