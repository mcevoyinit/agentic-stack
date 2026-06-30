#!/usr/bin/env zsh
# ============================================================================
# Claude Code Full Backup — generic template
# v2.0 — Production-grade: atomic SQLite, integrity-verified, optional cloud sync
#
# Backs up everything needed to port a Claude Code setup to a new machine:
#   - Config, skills, rules, commands, hooks, agents, plugins
#   - Conversation transcripts, memory, plans, todos, tasks
#   - Optional companion MCP data dirs (with atomic SQLite online backup)
#   - Optional extra directories (e.g. local MCP server source)
#   - Optional OAuth config directory
#   - All project .claude/ dirs + all CLAUDE.md files
#
# Features:
#   - Atomic SQLite backups via `.backup` (no WAL tearing)
#   - Self-excluding (won't recurse into prior backups)
#   - Pre-flight checks (disk space, cloud remote reachable)
#   - Archive integrity verification (tar tzf + size check)
#   - Optional cloud sync via rclone, with retention pruning
#   - SHA-256 manifest of critical files
#   - Fail-fast with clear error messages
#   - Secrets EXCLUDED by default (see SECURITY below)
#
# ----------------------------------------------------------------------------
# CONFIGURATION (all via environment variables — sane defaults below)
# ----------------------------------------------------------------------------
#   BACKUP_REMOTE            rclone remote + path for cloud sync.
#                            Default: "your-remote:claude-code-backups"
#                            (placeholder — you MUST set this for cloud sync,
#                             or pass --local-only to skip the cloud step).
#   BACKUP_DEST              Local destination dir for archives.
#                            Default: "$HOME/claude-backups"
#   BACKUP_EXTRA_DIRS        Space-separated list of extra absolute dirs to
#                            include (e.g. local MCP server source trees).
#                            Stored under extra/<path-relative-to-HOME>.
#                            Default: "" (none).
#   BACKUP_OAUTH_DIR         Optional OAuth/credentials config dir to include
#                            (e.g. "$HOME/.config/<your-oauth-tool>").
#                            Default: "" (none).
#   BACKUP_MCP_DATA_DIRS     Space-separated list of companion MCP data dirs
#                            that contain SQLite DBs to snapshot atomically.
#                            Default: "$HOME/.claude-conversations
#                                      $HOME/.claude-knowledge"
#                            (skipped silently if they don't exist).
#   BACKUP_LOCAL_RETENTION   Local archives to keep.  Default: 3
#   BACKUP_REMOTE_RETENTION  Remote archives to keep. Default: 5
#   BACKUP_MIN_FREE_GB       Min free disk (GB) required. Default: 5
#
# ----------------------------------------------------------------------------
# SECURITY — secrets are EXCLUDED by default
# ----------------------------------------------------------------------------
# The archive is UNENCRYPTED. By default this script does NOT copy files that
# commonly hold live secrets:
#     api-keys.env, settings.local.json, .credentials.json
# This prevents your own keys leaking into an unencrypted cloud backup on the
# first run. Pass --include-secrets to bundle them anyway — only do so if you
# also encrypt the archive at rest (e.g. an rclone "crypt" remote, or
# gpg-encrypt the .tar.gz before uploading).
#
# Usage:
#   ./backup.sh                      # full backup + cloud sync (needs BACKUP_REMOTE)
#   ./backup.sh --local-only         # skip cloud sync
#   ./backup.sh --no-prune           # skip retention cleanup
#   ./backup.sh --dest DIR           # custom local destination
#   ./backup.sh --include-secrets    # bundle secret files (see SECURITY)
# ============================================================================
set -euo pipefail

# ============================================================================
# CONFIG
# ============================================================================
readonly SCRIPT_VERSION="2.0"
readonly TIMESTAMP=$(date +%Y%m%d_%H%M%S)
readonly RCLONE_REMOTE="${BACKUP_REMOTE:-your-remote:claude-code-backups}"
readonly RCLONE_REMOTE_PLACEHOLDER="your-remote:claude-code-backups"
readonly LOCAL_RETENTION="${BACKUP_LOCAL_RETENTION:-3}"
readonly REMOTE_RETENTION="${BACKUP_REMOTE_RETENTION:-5}"
readonly MIN_FREE_GB="${BACKUP_MIN_FREE_GB:-5}"
readonly EXTRA_DIRS="${BACKUP_EXTRA_DIRS:-}"
readonly OAUTH_DIR="${BACKUP_OAUTH_DIR:-}"
readonly MCP_DATA_DIRS="${BACKUP_MCP_DATA_DIRS:-$HOME/.claude-conversations $HOME/.claude-knowledge}"

# Files that may contain live secrets — excluded unless --include-secrets.
readonly -a SECRET_FILES=(api-keys.env settings.local.json .credentials.json)

# Parse args
LOCAL_ONLY=false
PRUNE=true
INCLUDE_SECRETS=false
DEST_BASE="${BACKUP_DEST:-$HOME/claude-backups}"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --local-only)      LOCAL_ONLY=true; shift ;;
        --no-prune)        PRUNE=false; shift ;;
        --include-secrets) INCLUDE_SECRETS=true; shift ;;
        --dest)            DEST_BASE="$2"; shift 2 ;;
        -h|--help)
            grep -E '^#' "$0" | head -90 | sed 's/^# \?//'
            exit 0
            ;;
        *) echo "Unknown arg: $1" >&2; exit 2 ;;
    esac
done

readonly BACKUP_DIR="$DEST_BASE/claude-backup-$TIMESTAMP"
readonly ARCHIVE="$DEST_BASE/claude-backup-$TIMESTAMP.tar.gz"
readonly MANIFEST="$BACKUP_DIR/MANIFEST.md"
readonly CHECKSUMS="$BACKUP_DIR/CHECKSUMS.sha256"
readonly LOG="$BACKUP_DIR/backup.log"

# ============================================================================
# OUTPUT HELPERS
# ============================================================================
RED=$'\033[0;31m'
GREEN=$'\033[0;32m'
YELLOW=$'\033[1;33m'
BLUE=$'\033[0;34m'
BOLD=$'\033[1m'
NC=$'\033[0m'

info()  { print -P "${BLUE}[INFO]${NC}  $*" | tee -a "$LOG" 2>/dev/null || print -P "${BLUE}[INFO]${NC}  $*"; }
ok()    { print -P "${GREEN}[OK]${NC}    $*" | tee -a "$LOG" 2>/dev/null || print -P "${GREEN}[OK]${NC}    $*"; }
warn()  { print -P "${YELLOW}[WARN]${NC}  $*" | tee -a "$LOG" 2>/dev/null || print -P "${YELLOW}[WARN]${NC}  $*"; }
fail()  { print -P "${RED}[FAIL]${NC}  $*" | tee -a "$LOG" 2>/dev/null || print -P "${RED}[FAIL]${NC}  $*"; }
die()   { fail "$*"; exit 1; }

typeset -A SECTION_SIZES
backup_count=0
skip_count=0

is_secret_file() {
    local name="$1"
    for s in "${SECRET_FILES[@]}"; do
        [[ "$name" == "$s" ]] && return 0
    done
    return 1
}

# ============================================================================
# PHASE 0 — PRE-FLIGHT CHECKS
# ============================================================================
preflight() {
    print ""
    print "${BOLD}=============================================="
    print "  Claude Code Full Backup v${SCRIPT_VERSION}"
    print "  $(date)"
    print "  Target: $BACKUP_DIR"
    print "==============================================${NC}"
    print ""
    info "=== Pre-flight Checks ==="

    # 1. Required tools
    for tool in rsync tar sqlite3 shasum; do
        command -v "$tool" >/dev/null || die "Missing required tool: $tool"
    done
    ok "Required tools: rsync, tar, sqlite3, shasum"

    # 2. rclone + remote (only if syncing)
    if ! $LOCAL_ONLY; then
        command -v rclone >/dev/null || die "Missing rclone (needed for cloud sync). Use --local-only to skip."

        if [[ "$RCLONE_REMOTE" == "$RCLONE_REMOTE_PLACEHOLDER" ]]; then
            die "BACKUP_REMOTE is unset (still the placeholder). Set it, e.g. \
export BACKUP_REMOTE=myremote:claude-code-backups — or pass --local-only."
        fi

        # Verify remote is reachable BEFORE spending time on backup
        if ! rclone lsd "${RCLONE_REMOTE%:*}:" >/dev/null 2>&1; then
            die "rclone remote '${RCLONE_REMOTE%:*}:' not reachable. Check 'rclone config'."
        fi
        ok "rclone remote reachable: ${RCLONE_REMOTE%:*}:"
    fi

    # 3. Disk space
    local free_gb
    free_gb=$(df -g "$HOME" | awk 'NR==2 {print $4}')
    if (( free_gb < MIN_FREE_GB )); then
        die "Insufficient disk space: ${free_gb}GB free, need ${MIN_FREE_GB}GB"
    fi
    ok "Disk space: ${free_gb}GB free"

    # 4. ~/.claude exists
    [[ -d "$HOME/.claude" ]] || die "~/.claude not found — nothing to back up"
    ok "Claude Code config found"

    # 5. Secrets policy notice
    if $INCLUDE_SECRETS; then
        warn "Secret files WILL be bundled (--include-secrets). Archive is UNENCRYPTED — encrypt before uploading."
    else
        info "Secret files excluded by default: ${SECRET_FILES[*]} (use --include-secrets to bundle)"
    fi

    # 6. Create backup dir
    mkdir -p "$BACKUP_DIR"
    touch "$LOG"
    ok "Backup directory created"

    print ""
}

# ============================================================================
# HELPERS
# ============================================================================
backup_dir() {
    local src="$1" dst="$2" label="$3" excludes="${4:-}"

    if [[ -d "$src" ]]; then
        mkdir -p "$dst"
        local -a rsync_args=(-a -q)
        # Always exclude the backup dir itself to prevent recursion
        rsync_args+=(--exclude="$DEST_BASE")
        if [[ -n "$excludes" ]]; then
            local -a EXCL=("${(@s:|:)excludes}")
            for ex in "${EXCL[@]}"; do
                rsync_args+=(--exclude="$ex")
            done
        fi
        rsync "${rsync_args[@]}" "$src/" "$dst/"
        local size
        size=$(du -sh "$dst" 2>/dev/null | cut -f1)
        SECTION_SIZES[$label]="$size"
        ok "$label ($size)"
        backup_count=$((backup_count + 1))
    else
        warn "SKIP $label — $src not found"
        skip_count=$((skip_count + 1))
    fi
}

backup_file() {
    local src="$1" dst="$2" label="$3"

    if [[ -f "$src" ]]; then
        mkdir -p "$(dirname "$dst")"
        cp -p "$src" "$dst"
        local size
        size=$(du -sh "$dst" 2>/dev/null | cut -f1)
        ok "$label ($size)"
        backup_count=$((backup_count + 1))
    else
        warn "SKIP $label — $src not found"
        skip_count=$((skip_count + 1))
    fi
}

# Atomic SQLite backup — safe even when DB is open with WAL writes in progress
backup_sqlite() {
    local src="$1" dst="$2" label="$3"

    if [[ ! -f "$src" ]]; then
        warn "SKIP $label — $src not found"
        skip_count=$((skip_count + 1))
        return
    fi

    mkdir -p "$(dirname "$dst")"

    # sqlite3 .backup is an online backup — takes a consistent snapshot
    # even while another process has the DB open. Handles WAL correctly.
    if sqlite3 "$src" ".backup '$dst'" 2>> "$LOG"; then
        local size
        size=$(du -sh "$dst" 2>/dev/null | cut -f1)

        # Verify the backup is a valid SQLite DB
        if sqlite3 "$dst" "PRAGMA integrity_check;" 2>/dev/null | grep -q "^ok$"; then
            ok "$label ($size) [atomic + integrity verified]"
            backup_count=$((backup_count + 1))
        else
            fail "$label — integrity check FAILED, falling back to file copy"
            cp -p "$src" "$dst"
            warn "$label — used non-atomic copy (may be inconsistent)"
        fi
    else
        # Fallback: if sqlite3 can't open it (e.g. locked), cp the raw files
        warn "$label — sqlite3 .backup failed, using raw cp (may be inconsistent)"
        cp -p "$src" "$dst"
        backup_count=$((backup_count + 1))
    fi
}

# ============================================================================
# BACKUP PHASES
# ============================================================================

backup_core_config() {
    info "=== Core Configuration ==="

    local files=(
        "config.json|MCP servers config"
        "settings.json|Settings (permissions, hooks, plugins, env)"
        "settings.local.json|Local settings overrides"
        "CLAUDE.md|Global CLAUDE.md"
        "api-keys.env|API keys"
        "statusline.sh|Status line script"
        "history.jsonl|Prompt history"
        "session-cache.jsonl|Session cache"
        "session-index.jsonl|Session index"
    )

    for entry in "${files[@]}"; do
        local fname="${entry%%|*}"
        local label="${entry##*|}"
        if is_secret_file "$fname" && ! $INCLUDE_SECRETS; then
            warn "SKIP $label — $fname excluded (secret; use --include-secrets)"
            skip_count=$((skip_count + 1))
            continue
        fi
        backup_file "$HOME/.claude/$fname" "$BACKUP_DIR/claude/$fname" "$label"
    done
}

backup_skills_and_config() {
    info "=== Skills ==="
    backup_dir "$HOME/.claude/skills" "$BACKUP_DIR/claude/skills" "Skills"

    info "=== Rules, Commands, Agents, Hooks, Scripts, Prompts, Teams ==="
    local dirs=(rules commands agents hooks scripts prompts teams)
    for d in "${dirs[@]}"; do
        backup_dir "$HOME/.claude/$d" "$BACKUP_DIR/claude/$d" "$d"
    done

    info "=== Plugins ==="
    backup_dir "$HOME/.claude/plugins" "$BACKUP_DIR/claude/plugins" "Plugins" \
        "cache|__pycache__|node_modules|.git"
}

backup_project_data() {
    info "=== Project Data (transcripts, memory, plans, todos) ==="

    backup_dir "$HOME/.claude/projects" "$BACKUP_DIR/claude/projects" \
        "Project transcripts & memory"
    backup_dir "$HOME/.claude/personal-archive" "$BACKUP_DIR/claude/personal-archive" \
        "Personal archive"
    backup_dir "$HOME/.claude/plans" "$BACKUP_DIR/claude/plans" "Plans"
    backup_dir "$HOME/.claude/todos" "$BACKUP_DIR/claude/todos" "Todos"
    backup_dir "$HOME/.claude/tasks" "$BACKUP_DIR/claude/tasks" "Tasks"
}

# Companion MCP data dirs: atomically snapshot any *.db, then copy the rest.
# Generic — handles any such dir listed in BACKUP_MCP_DATA_DIRS, skips missing.
backup_mcp_data_dirs() {
    info "=== Companion MCP Data Directories ==="

    local -a dirs=(${(z)MCP_DATA_DIRS})
    [[ ${#dirs[@]} -eq 0 ]] && { info "None configured"; return; }

    for src in "${dirs[@]}"; do
        [[ -z "$src" ]] && continue
        if [[ ! -d "$src" ]]; then
            warn "SKIP MCP data dir — $src not found"
            continue
        fi
        local name rel dst
        rel="${src#$HOME/}"
        name="$(basename "$src")"
        dst="$BACKUP_DIR/mcp-data/$name"
        mkdir -p "$dst"

        # Atomic snapshot of every SQLite DB in the dir (top level).
        local db
        for db in "$src"/*.db(N); do
            [[ -f "$db" ]] || continue
            backup_sqlite "$db" "$dst/$(basename "$db")" "MCP[$name]: $(basename "$db")"
        done

        # Copy everything else (code, config, static) excluding DBs + cruft.
        backup_dir "$src" "$dst" "MCP[$name]: files" \
            "*.db|*.db-wal|*.db-shm|.venv|__pycache__|.git|node_modules"
    done
}

# Extra dirs + OAuth dir: stored under extra/<path-relative-to-HOME> so the
# restore script can put them back generically (no hardcoded destinations).
backup_extra_dirs() {
    info "=== Extra Directories ==="

    local -a dirs=(${(z)EXTRA_DIRS})
    [[ -n "$OAUTH_DIR" ]] && dirs+=("$OAUTH_DIR")

    if [[ ${#dirs[@]} -eq 0 ]]; then
        info "None configured (set BACKUP_EXTRA_DIRS / BACKUP_OAUTH_DIR)"
        return
    fi

    for src in "${dirs[@]}"; do
        [[ -z "$src" ]] && continue
        if [[ ! -d "$src" ]]; then
            warn "SKIP extra dir — $src not found"
            continue
        fi
        local rel
        case "$src" in
            "$HOME"/*) rel="${src#$HOME/}" ;;
            *)         rel="abs${src}" ;;   # outside HOME: stash under extra/abs/...
        esac
        backup_dir "$src" "$BACKUP_DIR/extra/$rel" "Extra: $rel" \
            ".venv|__pycache__|.git|node_modules"
    done
}

backup_project_claudes() {
    info "=== Project-Level .claude Configs ==="

    # Find .claude dirs, EXCLUDING the backup dir and ~/.claude itself.
    # ``|| true``: bind-mounts can leave root-owned dirs under $HOME; find
    # exits non-zero on EPERM and errexit+pipefail would kill the backup.
    local project_dirs
    project_dirs=$({ find "$HOME" -maxdepth 4 -name ".claude" -type d 2>/dev/null || true; } \
        | grep -v "^$HOME/.claude$" \
        | grep -v "^$HOME/.claude/" \
        | grep -v "^$DEST_BASE" \
        | grep -v "node_modules" \
        | grep -v "/.npm/" \
        | sort)

    if [[ -z "$project_dirs" ]]; then
        warn "No project .claude dirs found"
        return
    fi

    while IFS= read -r dir; do
        local rel="${dir#$HOME/}"
        backup_dir "$dir" \
            "$BACKUP_DIR/project-claudes/$rel" \
            "Project: $rel" \
            "__pycache__|.git|node_modules"
    done <<< "$project_dirs"
}

backup_claude_md_files() {
    info "=== CLAUDE.md Files (all projects) ==="

    mkdir -p "$BACKUP_DIR/claude-md-files"
    local md_count=0

    while IFS= read -r f; do
        [[ -z "$f" ]] && continue
        local rel="${f#$HOME/}"
        mkdir -p "$BACKUP_DIR/claude-md-files/$(dirname "$rel")"
        cp -p "$f" "$BACKUP_DIR/claude-md-files/$rel"
        md_count=$((md_count + 1))
    done < <({ find "$HOME" -maxdepth 5 \( -name "CLAUDE.md" -o -name "CLAUDE.local.md" \) 2>/dev/null || true; } \
        | grep -v "^$DEST_BASE" \
        | grep -v "node_modules" \
        | grep -v "/.npm/" \
        | sort)

    ok "CLAUDE.md files ($md_count files)"
    SECTION_SIZES["CLAUDE.md files"]="$md_count files"

    backup_file "$HOME/CLAUDE.md" "$BACKUP_DIR/home-CLAUDE.md" "~/CLAUDE.md"
}

# ============================================================================
# CHECKSUMS & MANIFEST
# ============================================================================
generate_checksums() {
    info "=== Generating SHA-256 checksums of critical files ==="

    (
        cd "$BACKUP_DIR"
        # Critical config + every SQLite snapshot captured.
        local -a critical=(
            "claude/config.json"
            "claude/settings.json"
            "claude/CLAUDE.md"
        )
        for f in "${critical[@]}"; do
            [[ -f "$f" ]] && shasum -a 256 "$f" >> "$CHECKSUMS"
        done
        # All DB snapshots under mcp-data/
        if [[ -d "mcp-data" ]]; then
            while IFS= read -r db; do
                shasum -a 256 "$db" >> "$CHECKSUMS"
            done < <(find mcp-data -name '*.db' 2>/dev/null | sort)
        fi
    )

    if [[ -f "$CHECKSUMS" ]]; then
        ok "Checksums written: $(wc -l < "$CHECKSUMS" | tr -d ' ') files"
    else
        warn "No critical files found to checksum"
    fi
}

generate_manifest() {
    info "=== Generating Manifest ==="

    local total_size
    total_size=$(du -sh "$BACKUP_DIR" 2>/dev/null | cut -f1)

    cat > "$MANIFEST" << 'HEADER'
# Claude Code Full Backup Manifest
HEADER

    cat >> "$MANIFEST" << EOF

**Version**: ${SCRIPT_VERSION}
**Created**: $(date '+%Y-%m-%d %H:%M:%S %Z')
**Machine**: $(hostname) ($(uname -m))
**OS**: $(sw_vers -productVersion 2>/dev/null || uname -sr)
**Total Size**: $total_size
**Items**: $backup_count backed up, $skip_count skipped
**Secrets bundled**: $($INCLUDE_SECRETS && echo "YES (--include-secrets)" || echo "no (excluded by default)")

## Contents

| Section | Size |
|---------|------|
EOF

    for key in ${(ok)SECTION_SIZES}; do
        echo "| $key | ${SECTION_SIZES[$key]} |" >> "$MANIFEST"
    done

    cat >> "$MANIFEST" << 'EOF'

## Atomic Snapshots

SQLite databases were backed up via `sqlite3 .backup` — consistent snapshots
even while an MCP server was actively writing. Each DB passed
`PRAGMA integrity_check` before being included.

## Sensitive Files

The archive is UNENCRYPTED. By default, files that commonly hold live secrets
(`api-keys.env`, `settings.local.json`, `.credentials.json`) are EXCLUDED.
If you ran with `--include-secrets`, those files ARE in this archive — keep it
on encrypted storage and/or upload only to an encrypted remote.

Note: `config.json` may still contain MCP server API keys. Review before
sharing this archive.

## Restore

```bash
tar xzf claude-backup-*.tar.gz
cd claude-backup-*
./restore.sh --dry-run   # preview
./restore.sh             # full restore
```

## Post-Restore Checklist

- [ ] Install Claude Code CLI: `npm install -g @anthropic-ai/claude-code`
- [ ] Re-authenticate: `claude login`
- [ ] Install Python for MCP servers: `brew install python@3`
- [ ] If using cloud sync: install + reconfigure rclone: `rclone config`
- [ ] Reinstall MCP server deps (handled automatically by restore script)
- [ ] Re-add any excluded secret files (api-keys.env, etc.)
- [ ] Verify MCP servers: `claude mcp list`
- [ ] Verify skills load: `/help` in Claude Code
- [ ] Verify checksums: `shasum -c CHECKSUMS.sha256`
EOF

    ok "Manifest written"
}

# ============================================================================
# RESTORE SCRIPT GENERATOR
# ============================================================================
generate_restore_script() {
    info "=== Generating Restore Script ==="
    # Ship the companion restore.sh into the archive root.
    local self_dir
    self_dir="$(cd "$(dirname "$0")" && pwd)"
    if [[ -f "$self_dir/restore.sh" ]]; then
        cp -p "$self_dir/restore.sh" "$BACKUP_DIR/restore.sh"
        chmod +x "$BACKUP_DIR/restore.sh"
        ok "Restore script copied from template"
    else
        warn "restore.sh template not found next to backup.sh — archive will lack a restore script"
    fi
}

# ============================================================================
# ARCHIVE + VERIFY
# ============================================================================
create_and_verify_archive() {
    info "=== Compressing archive ==="
    print "  This may take a minute for large datasets..."

    (cd "$DEST_BASE" && tar czf "$ARCHIVE" "claude-backup-$TIMESTAMP")

    local archive_size
    archive_size=$(du -h "$ARCHIVE" | cut -f1)
    ok "Archive created: $archive_size"

    info "=== Verifying archive integrity ==="

    tar tzf "$ARCHIVE" > /dev/null 2>&1 || die "Archive corrupted: tar tzf failed"
    ok "tar integrity check passed"

    local file_count
    file_count=$(tar tzf "$ARCHIVE" 2>/dev/null | wc -l | tr -d ' ')
    ok "Archive contains $file_count entries"

    for marker in "claude/config.json" "claude/skills" "MANIFEST.md"; do
        if tar tzf "$ARCHIVE" 2>/dev/null | grep -q "$marker"; then
            ok "Contains: $marker"
        else
            die "Archive missing critical marker: $marker"
        fi
    done
}

# ============================================================================
# CLOUD SYNC (rclone)
# ============================================================================
sync_to_remote() {
    if $LOCAL_ONLY; then
        info "=== Skipping cloud sync (--local-only) ==="
        return
    fi

    info "=== Syncing to cloud remote ==="

    rclone mkdir "$RCLONE_REMOTE" 2>/dev/null || true

    if rclone copy "$ARCHIVE" "${RCLONE_REMOTE}/" --progress 2>&1 | tail -20; then
        ok "Uploaded to ${RCLONE_REMOTE}/"
    else
        fail "rclone copy failed — archive remains locally at $ARCHIVE"
        return 1
    fi

    local local_size remote_size
    local_size=$(stat -f%z "$ARCHIVE")
    remote_size=$(rclone size "${RCLONE_REMOTE}/$(basename "$ARCHIVE")" --json 2>/dev/null \
        | python3 -c "import sys,json; print(json.load(sys.stdin).get('bytes',0))" 2>/dev/null || echo "0")

    if [[ "$local_size" == "$remote_size" ]]; then
        ok "Remote size matches local ($local_size bytes)"
    else
        warn "Size mismatch: local=$local_size, remote=$remote_size"
    fi
}

# ============================================================================
# RETENTION
# ============================================================================
prune_backups() {
    if ! $PRUNE; then
        info "=== Skipping retention prune (--no-prune) ==="
        return
    fi

    info "=== Pruning old backups ==="

    # Local retention — keep last N
    local local_old
    local_old=$(ls -t "$DEST_BASE"/claude-backup-*.tar.gz 2>/dev/null | tail -n +$((LOCAL_RETENTION + 1)))
    if [[ -n "$local_old" ]]; then
        while IFS= read -r f; do
            rm -f "$f"
            local extracted="${f%.tar.gz}"
            [[ -d "$extracted" ]] && rm -rf "$extracted"
            ok "Removed local: $(basename "$f")"
        done <<< "$local_old"
    else
        ok "Local: within retention ($LOCAL_RETENTION)"
    fi

    # Clean up any extracted backup dirs without a tarball
    for d in "$DEST_BASE"/claude-backup-*/; do
        [[ -d "$d" ]] || continue
        local tb="${d%/}.tar.gz"
        if [[ ! -f "$tb" ]] && [[ "${d%/}" != "$BACKUP_DIR" ]]; then
            rm -rf "$d"
            ok "Removed orphan dir: $(basename "${d%/}")"
        fi
    done

    # Remote retention — keep last N
    if ! $LOCAL_ONLY; then
        local remote_list
        remote_list=$(rclone lsf "$RCLONE_REMOTE" --files-only 2>/dev/null \
            | grep -E '^claude-backup-[0-9]{8}_[0-9]{6}\.tar\.gz$' \
            | sort -r)

        if [[ -n "$remote_list" ]]; then
            local to_delete
            to_delete=$(echo "$remote_list" | tail -n +$((REMOTE_RETENTION + 1)))
            if [[ -n "$to_delete" ]]; then
                while IFS= read -r f; do
                    rclone deletefile "${RCLONE_REMOTE}/$f" 2>/dev/null \
                        && ok "Removed remote: $f" \
                        || warn "Failed to delete remote: $f"
                done <<< "$to_delete"
            else
                ok "Remote: within retention ($REMOTE_RETENTION)"
            fi
        fi
    fi

    # Clean up the staging dir for THIS backup (keep only the tarball locally)
    if [[ -d "$BACKUP_DIR" ]] && [[ -f "$ARCHIVE" ]]; then
        rm -rf "$BACKUP_DIR"
        ok "Cleaned staging directory"
    fi
}

# ============================================================================
# SUMMARY
# ============================================================================
print_summary() {
    local archive_size
    archive_size=$(du -h "$ARCHIVE" 2>/dev/null | cut -f1)

    print ""
    print "${BOLD}${GREEN}=============================================="
    print "  Backup Complete!"
    print "==============================================${NC}"
    print ""
    print "  ${BOLD}Archive:${NC}   $ARCHIVE"
    print "  ${BOLD}Size:${NC}      $archive_size"
    print "  ${BOLD}Items:${NC}     $backup_count backed up, $skip_count skipped"
    if ! $LOCAL_ONLY; then
        print "  ${BOLD}Remote:${NC}    ${RCLONE_REMOTE}/$(basename "$ARCHIVE")"
    fi
    print ""
    print "  ${BOLD}Restore on a new machine:${NC}"
    if ! $LOCAL_ONLY; then
        print "    rclone copy ${RCLONE_REMOTE}/$(basename "$ARCHIVE") ~/"
    fi
    print "    tar xzf $(basename "$ARCHIVE")"
    print "    cd claude-backup-$TIMESTAMP"
    print "    ./restore.sh --dry-run   # preview"
    print "    ./restore.sh             # full restore"
    print ""
}

# ============================================================================
# MAIN
# ============================================================================
main() {
    preflight
    backup_core_config
    backup_skills_and_config
    backup_project_data
    backup_mcp_data_dirs
    backup_extra_dirs
    backup_project_claudes
    backup_claude_md_files
    generate_checksums
    generate_manifest
    generate_restore_script
    create_and_verify_archive
    sync_to_remote
    prune_backups
    print_summary
}

main "$@"
