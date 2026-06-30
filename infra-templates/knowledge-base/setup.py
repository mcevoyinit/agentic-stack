#!/usr/bin/env python3
"""Create an empty knowledge-base db with schema only. Safe to re-run.

Usage:
    python3 setup.py [--db-path PATH]

Default path: $KNOWLEDGE_DB or ~/.claude-knowledge/knowledge.db
"""
import argparse
import os
import sqlite3


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--db-path")
    args = p.parse_args()

    db_path = args.db_path or os.environ.get(
        "KNOWLEDGE_DB", os.path.expanduser("~/.claude-knowledge/knowledge.db")
    )
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    with open(schema_path) as f:
        schema = f.read()

    conn = sqlite3.connect(db_path)
    conn.executescript(schema)
    conn.commit()
    conn.close()
    print(f"knowledge-base ready (empty) at {db_path}")


if __name__ == "__main__":
    main()
