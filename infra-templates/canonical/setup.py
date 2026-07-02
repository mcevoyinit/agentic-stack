#!/usr/bin/env python3
"""Set up the canonical registry. Safe to re-run.

Does two things:
  1. Creates an empty canonical.db (schema only, no rows).
  2. Installs canonical.py to $CLAUDE_HOME/infra/canonical.py (default
     ~/.claude/infra/) so the optional SessionStart hook —
     `python3 ~/.claude/infra/canonical.py inject`, snippet in this
     folder's README.md — resolves once you add it to settings.json.

Usage:
    python3 setup.py [--db-path PATH] [--no-install-cli]

Default db path: $CANONICAL_DB or ~/.claude-canonical/canonical.db.
If you pass a custom --db-path, export CANONICAL_DB=<that path> in your
shell profile too, so the CLI and the SessionStart hook read the same db.
"""
import argparse
import os
import shutil
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(__file__))
from canonical import ensure_schema, DB_PATH  # noqa: E402


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--db-path", help="where to create the empty db "
                   "(default: $CANONICAL_DB or ~/.claude-canonical/canonical.db)")
    p.add_argument("--no-install-cli", action="store_true",
                   help="skip copying canonical.py into $CLAUDE_HOME/infra/")
    args = p.parse_args()

    db_path = args.db_path or DB_PATH
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    ensure_schema(conn)
    conn.close()
    print(f"canonical db ready (empty) at {db_path}")
    if args.db_path and os.path.abspath(args.db_path) != os.path.abspath(DB_PATH):
        print(f"  note: export CANONICAL_DB={args.db_path} so the CLI/hook use it")

    if not args.no_install_cli:
        claude_home = os.environ.get(
            "CLAUDE_HOME", os.path.expanduser("~/.claude"))
        infra_dir = os.path.join(claude_home, "infra")
        os.makedirs(infra_dir, exist_ok=True)
        src = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "canonical.py")
        dst = os.path.join(infra_dir, "canonical.py")
        shutil.copyfile(src, dst)
        print(f"canonical CLI installed at {dst}")
        print("  to surface concepts every session, add the SessionStart hook")
        print("  snippet from this folder's README.md to ~/.claude/settings.json")


if __name__ == "__main__":
    main()
