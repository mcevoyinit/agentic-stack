#!/usr/bin/env python3
"""
canonical.py — source-of-truth registry for high-stakes facts across sessions.

Backed by an additive, append-only `canonical_sources` table inside the
existing conversations.db (WAL, concurrency-safe). Every `set` INSERTs a new
row; the CURRENT truth for a concept is the latest row. Full history is kept
for audit (who/which session/when). Nothing is ever updated or deleted.

Governed by ~/.claude/rules/personal-facts-derive.md. Skills and memory carry
a POINTER to a concept here; the named canonical_file is the truth and its
latest dated entry wins over any copy found elsewhere.

Usage:
  canonical set --concept tax-2025-irs --file <path> --value "..." \
                [--stale-days 14] [--source manual] [--session <id>] [--note ...]
  canonical get --concept tax-2025-irs [--json]
  canonical list [--json]
  canonical history --concept tax-2025-irs
  canonical stale [--days N]          # concepts older than their threshold (or N)
  canonical stamp --concept X [--session <id>]   # re-verify (bump freshness)
  canonical render [--out <path>]     # regenerate CANONICAL.md projection (M2)

DB path: $CANONICAL_DB or ~/.claude-conversations/conversations.db
"""
import argparse
import os
import re
import sqlite3
import sys
from datetime import datetime, timezone

DB_PATH = os.environ.get(
    "CANONICAL_DB",
    os.path.expanduser("~/.claude-canonical/canonical.db"),
)
DEFAULT_OUT = os.path.expanduser("~/.claude/CANONICAL.md")
DEFAULT_STALE_DAYS = 30


# ---------- db helpers ----------

def connect(busy_ms=5000):
    # busy_ms caps how long we wait on a lock. The SessionStart inject path
    # passes a short cap so a pathological DB lock can never approach the
    # hook's 5s timeout; reads on WAL effectively never contend anyway.
    conn = sqlite3.connect(DB_PATH, timeout=max(1, busy_ms / 1000.0))
    conn.execute(f"PRAGMA busy_timeout = {int(busy_ms)}")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.row_factory = sqlite3.Row
    return conn


def ensure_schema(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS canonical_sources (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            concept       TEXT NOT NULL,
            canonical_file TEXT NOT NULL,
            value         TEXT,
            stale_days    INTEGER,
            source        TEXT,
            session_id    TEXT,
            note          TEXT,
            recorded_at   TEXT NOT NULL
                          DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_canon_concept "
        "ON canonical_sources(concept)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_canon_recorded "
        "ON canonical_sources(recorded_at)"
    )
    conn.commit()


def slug(s):
    s = (s or "").strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s


def now_iso():
    # millisecond ISO-8601 with Z, matching the DB's strftime('%f') style
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace(
        "+00:00", "Z")


def parse_iso(ts):
    if not ts:
        return None
    t = ts.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(t)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def age_days(ts):
    dt = parse_iso(ts)
    if dt is None:
        return None
    return (datetime.now(timezone.utc) - dt).total_seconds() / 86400.0


def current_rows(conn):
    """Latest row per concept (the current truth), newest first."""
    return conn.execute(
        """
        SELECT c.* FROM canonical_sources c
        JOIN (
            SELECT concept, MAX(id) AS mid
            FROM canonical_sources GROUP BY concept
        ) m ON c.id = m.mid
        ORDER BY c.recorded_at DESC
        """
    ).fetchall()


def current_for(conn, concept):
    return conn.execute(
        "SELECT * FROM canonical_sources WHERE concept = ? "
        "ORDER BY id DESC LIMIT 1",
        (concept,),
    ).fetchone()


def is_stale(row):
    a = age_days(row["recorded_at"])
    if a is None:
        return False
    thr = row["stale_days"] if row["stale_days"] is not None else DEFAULT_STALE_DAYS
    return a > thr


def is_private(row):
    return (row["value"] or "").strip().upper().startswith("PRIVATE")


def leaf(path):
    return os.path.basename(path or "")


# ---------- commands ----------

def cmd_set(args):
    concept = slug(args.concept)
    if not concept:
        sys.exit("error: --concept is required")
    if not args.file:
        sys.exit("error: --file is required")
    conn = connect()
    ensure_schema(conn)
    cur = conn.execute(
        """
        INSERT INTO canonical_sources
          (concept, canonical_file, value, stale_days, source, session_id,
           note, recorded_at)
        VALUES (?,?,?,?,?,?,?,?)
        """,
        (
            concept,
            os.path.expanduser(args.file),
            args.value,
            args.stale_days,
            args.source or "manual",
            args.session,
            args.note,
            now_iso(),
        ),
    )
    conn.commit()
    print(f"set {concept} (row {cur.lastrowid}) -> {args.file}")
    if args.value:
        print(f"  value: {args.value}")


def cmd_stamp(args):
    concept = slug(args.concept)
    conn = connect()
    ensure_schema(conn)
    row = current_for(conn, concept)
    if row is None:
        sys.exit(f"error: no such concept '{concept}'")
    conn.execute(
        """
        INSERT INTO canonical_sources
          (concept, canonical_file, value, stale_days, source, session_id,
           note, recorded_at)
        VALUES (?,?,?,?,?,?,?,?)
        """,
        (
            concept,
            row["canonical_file"],
            row["value"],
            row["stale_days"],
            args.source or "manual",
            args.session,
            "re-verified",
            now_iso(),
        ),
    )
    conn.commit()
    print(f"stamped {concept} re-verified at {now_iso()}")


def cmd_get(args):
    concept = slug(args.concept)
    conn = connect()
    ensure_schema(conn)
    row = current_for(conn, concept)
    if row is None:
        sys.exit(f"(no canonical entry for '{concept}')")
    if args.json:
        import json
        print(json.dumps({k: row[k] for k in row.keys()}, indent=2))
        return
    a = age_days(row["recorded_at"])
    age_s = f"{a:.0f}d ago" if a is not None else "age unknown"
    print(f"concept : {row['concept']}")
    print(f"file    : {row['canonical_file']}")
    print(f"value   : {row['value']}")
    print(f"verified: {row['recorded_at']}  ({age_s})")
    print(f"stale?  : {'YES' if is_stale(row) else 'no'} "
          f"(threshold {row['stale_days'] or DEFAULT_STALE_DAYS}d)")
    print(f"source  : {row['source']}  session={row['session_id']}")


def cmd_list(args):
    conn = connect()
    ensure_schema(conn)
    rows = current_rows(conn)
    if args.json:
        import json
        print(json.dumps([{k: r[k] for k in r.keys()} for r in rows], indent=2))
        return
    if not rows:
        print("(registry empty)")
        return
    for r in rows:
        a = age_days(r["recorded_at"])
        age = f"{a:.0f}d" if a is not None else "?"
        flag = "STALE" if is_stale(r) else "  ok "
        print(f"[{flag}] {r['concept']:<26} {age:>5}  {r['value'] or ''}")


def cmd_history(args):
    concept = slug(args.concept)
    conn = connect()
    ensure_schema(conn)
    rows = conn.execute(
        "SELECT * FROM canonical_sources WHERE concept = ? ORDER BY id DESC",
        (concept,),
    ).fetchall()
    if not rows:
        sys.exit(f"(no history for '{concept}')")
    for r in rows:
        print(f"{r['recorded_at']}  [{r['source']}/{r['session_id']}]  "
              f"{r['note'] or ''}")
        print(f"    {r['value'] or ''}  -> {r['canonical_file']}")


def cmd_stale(args):
    conn = connect()
    ensure_schema(conn)
    rows = current_rows(conn)
    hits = []
    for r in rows:
        a = age_days(r["recorded_at"])
        if a is None:
            continue
        thr = args.days if args.days is not None else (
            r["stale_days"] if r["stale_days"] is not None else DEFAULT_STALE_DAYS)
        if a > thr:
            hits.append((r, a, thr))
    if not hits:
        print("no stale concepts")
        return
    for r, a, thr in hits:
        print(f"STALE {r['concept']:<26} {a:.0f}d (>{thr}d)  {r['canonical_file']}")
    sys.exit(2)  # non-zero so a sweep can detect


def cmd_inject(args):
    """Emit a compact SessionStart additionalContext view. Never raises."""
    if os.environ.get("CANONICAL_INJECT_DISABLED") == "1":
        return
    import json
    try:
        conn = connect(busy_ms=1000)   # tight cap on the session-start path
        ensure_schema(conn)
        rows = current_rows(conn)
    except Exception:
        return  # must never break session start
    if not rows:
        return
    BUDGET = 2500
    stale = [r for r in rows if is_stale(r)]
    lines = [
        "CANONICAL source-of-truth registry (live from DB). Derive "
        "high-stakes facts from the named file, never a frozen copy "
        "(see rules/personal-facts-derive.md):"
    ]
    if stale:
        lines.append(f"⚠ {len(stale)} STALE — re-verify before quoting:")
        for r in stale:
            a = age_days(r["recorded_at"])
            age = f"{a:.0f}d" if a is not None else "?"
            lines.append(f"  ⚠ {r['concept']} ({age}) -> {leaf(r['canonical_file'])}")
    for r in rows:
        if is_stale(r):
            continue
        if is_private(r):
            lines.append(f"  {r['concept']} [PRIVATE] -> {leaf(r['canonical_file'])}")
        else:
            lines.append(f"  {r['concept']} -> {leaf(r['canonical_file'])} : "
                         f"{r['value'] or ''}")
    lines.append("Full: ~/.claude/CANONICAL.md | `canonical get --concept X`")
    text = "\n".join(lines)
    if len(text) > BUDGET:
        text = text[:BUDGET] + "\n…(truncated; run `canonical list`)"
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "SessionStart", "additionalContext": text}}))


def cmd_render(args):
    out = os.path.expanduser(args.out or DEFAULT_OUT)
    conn = connect()
    ensure_schema(conn)
    rows = current_rows(conn)
    lines = []
    lines.append("# CANONICAL — source-of-truth registry")
    lines.append("")
    lines.append("GENERATED from conversations.db `canonical_sources` by "
                 "`canonical.py render`. Do NOT hand-edit; edit via "
                 "`canonical set`. Governed by "
                 "`~/.claude/rules/personal-facts-derive.md`: carry a POINTER "
                 "to a concept here, never a copy. The named file is the truth;"
                 " its latest dated entry wins over any copy elsewhere. The"
                 " value column is a DATED HINT — verify in the file.")
    lines.append("")
    lines.append("| Concept | Fresh | Age | Canonical file | Value (hint) |")
    lines.append("|---------|-------|-----|----------------|--------------|")
    for r in rows:
        a = age_days(r["recorded_at"])
        age = f"{a:.0f}d" if a is not None else "?"
        flag = "⚠STALE" if is_stale(r) else "ok"
        val = (r["value"] or "").replace("|", "\\|")
        lines.append(f"| {r['concept']} | {flag} | {age} | "
                     f"`{r['canonical_file']}` | {val} |")
    lines.append("")
    stale = [r for r in rows if is_stale(r)]
    if stale:
        lines.append(f"⚠ **{len(stale)} stale concept(s)** — re-verify against "
                     "the canonical file and `canonical stamp` or `set`:")
        for r in stale:
            lines.append(f"- `{r['concept']}` "
                         f"({age_days(r['recorded_at']):.0f}d old)")
        lines.append("")
    lines.append(f"_Generated {now_iso()} from {len(rows)} concepts._")
    text = "\n".join(lines) + "\n"
    with open(out, "w") as f:
        f.write(text)
    print(f"rendered {len(rows)} concepts -> {out} "
          f"({len(stale)} stale)")


def main():
    p = argparse.ArgumentParser(prog="canonical", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("set")
    s.add_argument("--concept", required=True)
    s.add_argument("--file", required=True)
    s.add_argument("--value")
    s.add_argument("--stale-days", type=int, dest="stale_days")
    s.add_argument("--source")
    s.add_argument("--session")
    s.add_argument("--note")
    s.set_defaults(func=cmd_set)

    s = sub.add_parser("stamp")
    s.add_argument("--concept", required=True)
    s.add_argument("--source")
    s.add_argument("--session")
    s.set_defaults(func=cmd_stamp)

    s = sub.add_parser("get")
    s.add_argument("--concept", required=True)
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_get)

    s = sub.add_parser("list")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_list)

    s = sub.add_parser("history")
    s.add_argument("--concept", required=True)
    s.set_defaults(func=cmd_history)

    s = sub.add_parser("stale")
    s.add_argument("--days", type=int)
    s.set_defaults(func=cmd_stale)

    s = sub.add_parser("render")
    s.add_argument("--out")
    s.set_defaults(func=cmd_render)

    s = sub.add_parser("inject")
    s.set_defaults(func=cmd_inject)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
