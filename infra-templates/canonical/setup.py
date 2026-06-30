#!/usr/bin/env python3
"""Create an empty canonical.db with schema only. Safe to re-run."""
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(__file__))
from canonical import ensure_schema, DB_PATH  # noqa: E402


def main():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    ensure_schema(conn)
    conn.close()
    print(f"canonical db ready (empty) at {DB_PATH}")


if __name__ == "__main__":
    main()
