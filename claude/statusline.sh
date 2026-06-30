#!/bin/bash
# Claude Code Status Line - Shows context usage and session info
# Claude Code passes JSON via stdin with context_window data

# Read JSON from stdin
input=$(cat)

# Get git branch
branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "no-git")

# Get current model from env
model="${ANTHROPIC_MODEL:-opus}"

# Parse context from JSON stdin
used=$(echo "$input" | jq -r '.context_window.current_usage.input_tokens // 0' 2>/dev/null)
total=$(echo "$input" | jq -r '.context_window.context_window_size // 200000' 2>/dev/null)
pct=$(echo "$input" | jq -r '.context_window.used_percentage // 0' 2>/dev/null | cut -d. -f1)

# Compact token display (e.g. 45K/200K)
if [ -n "$used" ] && [ "$used" != "null" ] && [ "$used" -gt 0 ] 2>/dev/null; then
  used_k=$((used / 1000))
  total_k=$((total / 1000))
  echo "[$branch] $model | ${used_k}K/${total_k}K (${pct}%)"
else
  echo "[$branch] $model"
fi
