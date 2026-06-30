#!/bin/bash
# session-end-autocapture.sh — SessionEnd hook wrapper.
#
# Runs heuristic extraction in the background, exits 0 immediately.
# Never blocks session shutdown. Errors logged, never raised.
#
# Pipes stdin JSON (with transcript_path) to the Python extractor.
set -uo pipefail

INPUT=$(cat)

TRANSCRIPT_PATH=$(python3 -c "
import json, sys
try:
    data = json.loads(sys.argv[1])
    print(data.get('transcript_path', ''))
except Exception:
    pass
" "$INPUT" 2>/dev/null || true)

if [ -z "$TRANSCRIPT_PATH" ] || [ ! -f "$TRANSCRIPT_PATH" ]; then
    exit 0
fi

# Run in background, survives shell exit, errors swallowed
(
    python3 ~/.claude/hooks/session_end_autocapture.py "$TRANSCRIPT_PATH" \
        >> "${CLAUDE_HOOK_LOG:-$HOME/.claude/hooks/session_end_autocapture.log}" 2>&1 || true
) &

exit 0
