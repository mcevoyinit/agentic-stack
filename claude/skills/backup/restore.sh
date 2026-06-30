#!/usr/bin/env zsh
# ============================================================================
# Claude Code Full Restore — generic template (companion to backup.sh v2.0)
#
# Run this from the root of an extracted backup archive
# (the directory that contains claude/, MANIFEST.md, CHECKSUMS.sha256).
#
# Usage:
#   ./restore.sh              # interactive restore
#   ./restore.sh --dry-run    # preview without changes
#   ./restore.sh --force      # skip confirmation
# ============================================================================
set -euo pipefail

DRY_RUN=false
FORCE=false
for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=true ;;
        --force)   FORCE=true ;;
    esac
done

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HOME_DIR="$HOME"

RED=$'\033[0;31m'
GREEN=$'\033[0;32m'
YELLOW=$'\033[1;33m'
BLUE=$'\033[0;34m'
BOLD=$'\033[1m'
NC=$'\033[0m'

info()  { print -P "${BLUE}[INFO]${NC}  $*"; }
ok()    { print -P "${GREEN}[OK]${NC}    $*"; }
warn()  { print -P "${YELLOW}[WARN]${NC}  $*"; }
fail()  { print -P "${RED}[FAIL]${NC}  $*"; }

do_restore() {
    local src="$1" dst="$2" label="$3"
    if [[ -d "$src" ]] || [[ -f "$src" ]]; then
        if $DRY_RUN; then
            info "[DRY RUN] Would restore: $label"
        else
            mkdir -p "$(dirname "$dst")"
            if [[ -d "$src" ]]; then
                rsync -a "$src/" "$dst/"
            else
                cp -p "$src" "$dst"
            fi
            ok "$label"
        fi
    else
        warn "Skip: $label (not in backup)"
    fi
}

# Create a venv + install requirements for any restored dir that has one.
setup_venv() {
    local dir="$1" label="$2"
    $DRY_RUN && return
    [[ -f "$dir/requirements.txt" ]] || return
    info "Setting up venv: $label"
    (
        cd "$dir"
        python3 -m venv .venv 2>/dev/null || { warn "venv creation failed — install Python 3"; return; }
        if [[ -f .venv/bin/pip ]]; then
            .venv/bin/pip install -q -r requirements.txt 2>/dev/null \
                && ok "$label deps installed" \
                || warn "$label pip install failed — run manually"
        fi
    )
}

print ""
print "${BOLD}=============================================="
print "  Claude Code Full Restore"
print "  $(date)"
$DRY_RUN && print "  *** DRY RUN — no changes will be made ***"
print "==============================================${NC}"
print ""

# Pre-flight
[[ -d "$SCRIPT_DIR/claude" ]] || { fail "Backup structure not found. Run from backup root."; exit 1; }

# Verify checksums if present
if [[ -f "$SCRIPT_DIR/CHECKSUMS.sha256" ]]; then
    info "Verifying checksums..."
    (cd "$SCRIPT_DIR" && shasum -c CHECKSUMS.sha256) || { fail "Checksum verification FAILED"; exit 1; }
    ok "All checksums verified"
fi

# Verify any SQLite DBs in the archive are intact
while IFS= read -r db; do
    [[ -z "$db" ]] && continue
    if sqlite3 "$db" "PRAGMA integrity_check;" 2>/dev/null | grep -q "^ok$"; then
        ok "SQLite integrity: $(basename "$db")"
    else
        fail "SQLite integrity CHECK FAILED: $db"
        exit 1
    fi
done < <(find "$SCRIPT_DIR/mcp-data" -name '*.db' 2>/dev/null)

# Confirm
if ! $DRY_RUN && ! $FORCE; then
    print "${YELLOW}This will restore Claude Code configuration to $HOME_DIR${NC}"
    print "Existing files will be OVERWRITTEN. Ctrl+C to abort."
    read -r "confirm?Continue? [y/N] "
    [[ "$confirm" =~ ^[Yy]$ ]] || exit 0
fi

# --- 1. Core config ---
info "=== Restoring Core Configuration ==="
mkdir -p "$HOME_DIR/.claude"

for f in config.json settings.json settings.local.json CLAUDE.md api-keys.env \
         statusline.sh history.jsonl session-cache.jsonl session-index.jsonl; do
    do_restore "$SCRIPT_DIR/claude/$f" "$HOME_DIR/.claude/$f" "$f"
done

$DRY_RUN || chmod +x "$HOME_DIR/.claude/statusline.sh" 2>/dev/null || true

# --- 2. Skills + config dirs ---
info "=== Restoring Skills ==="
do_restore "$SCRIPT_DIR/claude/skills" "$HOME_DIR/.claude/skills" "Skills"

info "=== Restoring Rules, Commands, Agents, Hooks, Scripts, Prompts, Teams ==="
for d in rules commands agents hooks scripts prompts teams; do
    do_restore "$SCRIPT_DIR/claude/$d" "$HOME_DIR/.claude/$d" "$d"
done

if ! $DRY_RUN; then
    find "$HOME_DIR/.claude/hooks" -name "*.sh" -exec chmod +x {} \; 2>/dev/null || true
    find "$HOME_DIR/.claude/scripts" -name "*.sh" -exec chmod +x {} \; 2>/dev/null || true
fi

# --- 3. Plugins ---
info "=== Restoring Plugins ==="
do_restore "$SCRIPT_DIR/claude/plugins" "$HOME_DIR/.claude/plugins" "Plugins"

# --- 4. Project data ---
info "=== Restoring Project Data ==="
do_restore "$SCRIPT_DIR/claude/projects" "$HOME_DIR/.claude/projects" "Project transcripts & memory"
do_restore "$SCRIPT_DIR/claude/personal-archive" "$HOME_DIR/.claude/personal-archive" "Personal archive"
do_restore "$SCRIPT_DIR/claude/plans" "$HOME_DIR/.claude/plans" "Plans"
do_restore "$SCRIPT_DIR/claude/todos" "$HOME_DIR/.claude/todos" "Todos"
do_restore "$SCRIPT_DIR/claude/tasks" "$HOME_DIR/.claude/tasks" "Tasks"

# --- 5. Companion MCP data dirs (restored to ~/<basename>) ---
info "=== Restoring Companion MCP Data Directories ==="
if [[ -d "$SCRIPT_DIR/mcp-data" ]]; then
    for d in "$SCRIPT_DIR/mcp-data"/*(N/); do
        name="$(basename "$d")"
        dest="$HOME_DIR/.$name"   # dirs were named after ~/.<name>
        # If basename already starts with a dot it was stored without it; restore
        # to a dotted dir for the common ~/.claude-* convention.
        [[ "$name" == .* ]] && dest="$HOME_DIR/$name"
        do_restore "$d" "$dest" "MCP data: $name"
        if ! $DRY_RUN; then
            find "$dest" -name "*.sh" -exec chmod +x {} \; 2>/dev/null || true
            setup_venv "$dest" "$name"
        fi
    done
fi

# --- 6. Extra directories (restored to their HOME-relative paths) ---
info "=== Restoring Extra Directories ==="
if [[ -d "$SCRIPT_DIR/extra" ]]; then
    # Each top-level entry under extra/ is a HOME-relative path tree.
    while IFS= read -r d; do
        [[ -z "$d" ]] && continue
        rel="${d#$SCRIPT_DIR/extra/}"
        do_restore "$d" "$HOME_DIR/$rel" "Extra: $rel"
    done < <(find "$SCRIPT_DIR/extra" -mindepth 1 -maxdepth 1 2>/dev/null)
fi

# --- 7. Project-level .claude dirs ---
info "=== Restoring Project-Level Configs ==="
if [[ -d "$SCRIPT_DIR/project-claudes" ]]; then
    while IFS= read -r d; do
        rel="${d#$SCRIPT_DIR/project-claudes/}"
        rel="${rel%/}"
        do_restore "$d" "$HOME_DIR/$rel" "Project: $rel"
    done < <(find "$SCRIPT_DIR/project-claudes" -name ".claude" -type d 2>/dev/null)
fi

# --- 8. CLAUDE.md files ---
info "=== Restoring CLAUDE.md Files ==="
if [[ -d "$SCRIPT_DIR/claude-md-files" ]]; then
    while IFS= read -r f; do
        rel="${f#$SCRIPT_DIR/claude-md-files/}"
        do_restore "$f" "$HOME_DIR/$rel" "CLAUDE.md: $rel"
    done < <(find "$SCRIPT_DIR/claude-md-files" \( -name "CLAUDE.md" -o -name "CLAUDE.local.md" \) 2>/dev/null)
fi

# --- 9. Home CLAUDE.md ---
do_restore "$SCRIPT_DIR/home-CLAUDE.md" "$HOME_DIR/CLAUDE.md" "~/CLAUDE.md"

# ============================================================================
print ""
print "${BOLD}${GREEN}=============================================="
print "  Restore Complete!"
print "==============================================${NC}"
print ""
info "Post-restore checklist:"
print "  1. Install Claude Code: npm install -g @anthropic-ai/claude-code"
print "  2. Auth: claude login"
print "  3. Verify MCP: claude mcp list"
print "  4. Test a skill in Claude Code: /help"
print "  5. Re-add any excluded secret files (api-keys.env, etc.)"
print "  6. If you use cloud sync: rclone config"
print ""
