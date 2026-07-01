#!/bin/bash
# verify-install.sh — post-install doctor for agentic-stack-starter.
#
# Run AFTER ./install.sh. Read-only: checks a completed install and
# reports what's missing or misconfigured. Exits non-zero only on hard
# failures (missing core structure); warnings are informational.
set -uo pipefail

TARGET="${CLAUDE_HOME:-$HOME/.claude}"
FAIL=0
WARN=0

pass() { echo "  ok    $1"; }
warn() { echo "  WARN  $1"; WARN=$((WARN + 1)); }
fail() { echo "  FAIL  $1"; FAIL=$((FAIL + 1)); }

echo "agentic-stack-starter doctor — checking $TARGET"
echo
echo "[1/6] Core structure"
[ -d "$TARGET" ] || { fail "$TARGET does not exist — run ./install.sh first"; echo; echo "1 hard failure."; exit 1; }
for d in skills rules hooks commands; do
  if [ -d "$TARGET/$d" ]; then
    pass "$d/ present ($(ls "$TARGET/$d" | grep -cv '\.bak-') items)"
  else
    fail "$d/ missing — re-run ./install.sh"
  fi
done
for f in CLAUDE.md settings.json statusline.sh; do
  if [ -f "$TARGET/$f" ]; then pass "$f present"; else fail "$f missing — re-run ./install.sh"; fi
done

echo
echo "[2/6] Skill frontmatter (a malformed header silently disables that skill)"
if command -v python3 >/dev/null 2>&1; then
  python3 - "$TARGET" <<'EOF'
import os, re, sys
target = sys.argv[1]
skills = os.path.join(target, 'skills')
bad = 0
if os.path.isdir(skills):
    for d in sorted(os.listdir(skills)):
        if '.bak-' in d or not os.path.isdir(os.path.join(skills, d)):
            continue
        p = None
        for cand in ('SKILL.md', 'skill.md'):
            c = os.path.join(skills, d, cand)
            if os.path.exists(c):
                p = c
                break
        if not p:
            continue  # utility dirs (e.g. *-loop) ship without SKILL.md by design
        txt = open(p, encoding='utf-8', errors='replace').read()
        m = re.match(r'^---\n(.*?)\n---\n', txt, re.S)
        if not m or not re.search(r'^name:\s*\S', m.group(1), re.M):
            print(f"  FAIL  {d}: SKILL.md frontmatter missing or has no name:")
            bad += 1
print(f"  ok    frontmatter valid across skills" if bad == 0 else f"  ({bad} broken)")
sys.exit(1 if bad else 0)
EOF
  [ $? -eq 0 ] || FAIL=$((FAIL + 1))
else
  fail "python3 not found — required by several skills and hooks"
fi

echo
echo "[3/6] settings.json"
if python3 -c "import json,sys; json.load(open(sys.argv[1]))" "$TARGET/settings.json" 2>/dev/null; then
  pass "valid JSON"
else
  fail "settings.json is not valid JSON — fix before launching Claude Code"
fi

echo
echo "[4/6] Hook wiring (commands referenced in settings.json must exist)"
for hook in check-links.py session-end-autocapture.sh session_end_autocapture.py sync-session-index.py; do
  if [ -f "$TARGET/hooks/$hook" ]; then pass "hooks/$hook present"; else warn "hooks/$hook missing"; fi
done
[ -x "$TARGET/hooks/session-end-autocapture.sh" ] || warn "session-end-autocapture.sh not executable (chmod +x it)"
if grep -q 'infra/canonical.py' "$TARGET/settings.json" 2>/dev/null; then
  if [ -f "$TARGET/infra/canonical.py" ]; then
    pass "canonical SessionStart hook resolves ($TARGET/infra/canonical.py)"
  else
    warn "settings.json wires the canonical hook but $TARGET/infra/canonical.py is missing — run infra-templates/canonical/setup.py once, or delete that hook entry"
  fi
fi

echo
echo "[5/6] Binaries the stack leans on"
for bin in jq sqlite3 git; do
  if command -v "$bin" >/dev/null 2>&1; then pass "$bin found"; else warn "$bin not found ($([ "$bin" = jq ] && echo 'statusline.sh needs it' || echo 'several skills/infra templates need it'))"; fi
done
command -v node >/dev/null 2>&1 && pass "node found" || warn "node not found (only needed for x-bookmarks-iterate)"

echo
echo "[6/6] Optional infra (absent is fine — these are opt-in)"
for db in "${CANONICAL_DB:-$HOME/.claude-canonical/canonical.db}" "${RECALL_DB:-$HOME/.claude-recall/conversations.db}" "${KNOWLEDGE_DB:-$HOME/.claude-knowledge/knowledge.db}"; do
  if [ -f "$db" ]; then pass "$(basename "$db") exists"; else echo "  --    $(basename "$db") not set up (optional — see infra-templates/)"; fi
done

echo
if [ "$FAIL" -gt 0 ]; then
  echo "$FAIL hard failure(s), $WARN warning(s). Fix FAILs, re-run."
  exit 1
fi
echo "No hard failures ($WARN warning(s)). You're good — see docs/CUSTOMISE.md for what to personalise."
