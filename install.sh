#!/bin/bash
# install.sh — copy this bundle's claude/ tree into ~/.claude, with backups.
#
# Does NOT auto-fill any placeholder, does NOT create credentials, does NOT
# populate any database. See docs/CUSTOMISE.md for what to do after this runs.
set -euo pipefail

BUNDLE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="${CLAUDE_HOME:-$HOME/.claude}"
TS="$(date +%Y%m%d-%H%M%S)"

echo "agentic-stack-starter installer"
echo "  bundle:  $BUNDLE_DIR"
echo "  target:  $TARGET"
echo

mkdir -p "$TARGET"

backup_if_exists() {
  local path="$1"
  if [ -e "$path" ]; then
    local bak="${path}.bak-${TS}"
    echo "  backing up existing $(basename "$path") -> $(basename "$bak")"
    mv "$path" "$bak"
  fi
}

copy_dir() {
  local name="$1"
  local src="$BUNDLE_DIR/claude/$name"
  local dst="$TARGET/$name"
  if [ ! -d "$src" ]; then
    return
  fi
  echo "→ $name/"
  if [ -d "$dst" ]; then
    # merge: copy each item, backing up only on collision
    mkdir -p "$dst"
    for item in "$src"/*; do
      local base
      base="$(basename "$item")"
      if [ -e "$dst/$base" ]; then
        backup_if_exists "$dst/$base"
      fi
      cp -R "$item" "$dst/$base"
    done
  else
    cp -R "$src" "$dst"
  fi
}

echo "Copying skills, rules, hooks, commands..."
copy_dir "skills"
copy_dir "rules"
copy_dir "hooks"
copy_dir "commands"
chmod +x "$TARGET"/hooks/*.sh 2>/dev/null || true

echo
echo "Installing templates (rendered, suffix stripped, NOT auto-filled)..."
for tmpl in "$BUNDLE_DIR"/claude/*.template; do
  [ -e "$tmpl" ] || continue
  base="$(basename "$tmpl" .template)"
  dst="$TARGET/$base"
  backup_if_exists "$dst"
  cp "$tmpl" "$dst"
  echo "  → $base (edit this — see docs/CUSTOMISE.md)"
done

if [ -f "$BUNDLE_DIR/claude/statusline.sh" ]; then
  backup_if_exists "$TARGET/statusline.sh"
  cp "$BUNDLE_DIR/claude/statusline.sh" "$TARGET/statusline.sh"
  chmod +x "$TARGET/statusline.sh"
fi

echo
echo "Done. Next steps:"
echo "  1. Read docs/CUSTOMISE.md in the bundle — every <CUSTOMISE> marker"
echo "     across the installed files, grouped by what you're setting up."
echo "  2. Edit ~/.claude/CLAUDE.md and ~/.claude/settings.json — they are"
echo "     plain copies of the .template files, not yet personalised."
echo "  3. Optionally run the setup.py in each infra-templates/ subdir to"
echo "     create empty databases (canonical, recall-db, knowledge-base)."
echo "  4. Add any MCP servers you want from mcp/mcp-servers.example.json."
echo
echo "Nothing was auto-filled. Nothing was overwritten without a .bak-${TS} copy."
