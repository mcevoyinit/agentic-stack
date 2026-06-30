#!/usr/bin/env bash
# mac-health snapshot — real memory pressure, not `top`'s misleading "used".
# Writes a markdown report to $MAC_HEALTH_SNAP_DIR/YYYY-MM-DD-HHMM.md
# (default ~/.session-snapshots) and echoes the path to stdout.
set -u
# Deliberately NOT using `set -e` or `pipefail`: `sort | head` triggers SIGPIPE (141)
# when head closes early. That's normal here — this is a reporting script, partial
# output is better than no output.

# Configurable: set MAC_HEALTH_SNAP_DIR to change where snapshots are written.
SNAP_DIR="${MAC_HEALTH_SNAP_DIR:-${HOME}/.session-snapshots}"
mkdir -p "$SNAP_DIR"
OUT="${SNAP_DIR}/$(date +%Y-%m-%d-%H%M).md"

{
  echo "# mac-health snapshot — $(date '+%Y-%m-%d %H:%M:%S %Z')"
  echo ""
  echo "## Real memory pressure (trust these, not \`top\`'s \"used\")"
  echo ""

  # Swap — if > 0 and growing, real pressure
  swap_line=$(sysctl -n vm.swapusage 2>/dev/null || echo "total = 0,00M used = 0,00M free = 0,00M")
  swap_used=$(printf '%s' "$swap_line" | awk -F'used = ' '{print $2}' | awk '{print $1}')
  echo "- **swap used: \`${swap_used:-0,00M}\`** — 0 = no pressure; growing = real pressure"

  # vm_stat — the authoritative breakdown
  vm_stat | awk '
    /page size of/ { match($0,/[0-9]+/); ps=substr($0,RSTART,RLENGTH) }
    /^Pages free:/              { sub(/\./,"",$NF); free=$NF }
    /^Pages active:/            { sub(/\./,"",$NF); active=$NF }
    /^Pages inactive:/          { sub(/\./,"",$NF); inactive=$NF }
    /^Pages wired down:/        { sub(/\./,"",$NF); wired=$NF }
    /occupied by compressor:/   { sub(/\./,"",$NF); compressed=$NF }
    /^File-backed pages:/       { sub(/\./,"",$NF); fb=$NF }
    /^Anonymous pages:/         { sub(/\./,"",$NF); anon=$NF }
    END {
      gb = ps/1024/1024/1024
      real = (active + wired) * gb
      printf "- **real usage (active+wired): %.1f GB** ← the honest number\n", real
      printf "- compressed: **%.2f GB** (more than a few GB = memory being squeezed)\n", compressed*gb
      printf "- active: %.1f GB\n", active*gb
      printf "- wired (kernel): %.1f GB\n", wired*gb
      printf "- inactive (reclaimable, NOT really used): %.1f GB\n", inactive*gb
      printf "- file-backed cache (reclaimable): %.1f GB\n", fb*gb
      printf "- free (immediately available): %.1f GB\n", free*gb
    }'

  echo ""
  echo "## \`top\` view (for comparison — counts inactive as \"used\")"
  echo ""
  echo '```'
  top -l 1 | awk '/PhysMem|Load Avg|CPU usage/'
  echo '```'

  echo ""
  echo "## Thermal"
  echo ""
  echo '```'
  pmset -g therm 2>/dev/null | sed '/^$/d' || echo "(pmset thermal unavailable)"
  echo '```'

  echo ""
  echo "## Disk"
  echo ""
  echo '```'
  df -h / | tail -1
  echo '```'

  echo ""
  echo "## Top 15 processes by RSS"
  echo ""
  echo "| RSS | PID | uptime | command |"
  echo "|-----|-----|--------|---------|"
  ps -eo pid,rss,etime,command | sort -k2 -nr | head -15 \
    | awk '{mb=$2/1024; printf "| %d MB | %s | %s | %s |\n", mb, $1, $3, substr($0, index($0,$4), 60)}'

  echo ""
  echo "## Memory by category (RSS sum — approximate; shared pages double-counted)"
  echo ""
  ps -eo rss,command | awk '
    NR>1 {
      cmd=$2; for(i=3;i<=NF;i++) cmd=cmd" "$i
      if(cmd ~ /claude --/)                       claude+=$1
      else if(cmd ~ /Google Chrome/)              chrome+=$1
      else if(cmd ~ /com\.docker|Docker\.app/)    docker+=$1
      else if(cmd ~ /iTerm/)                      iterm+=$1
      else if(cmd ~ /WhatsApp/)                   whatsapp+=$1
      else if(cmd ~ /superwhisper/)               sw+=$1
      else if(cmd ~ /NordVPN/)                    nord+=$1
      else if(cmd ~ /PyCharm|JetBrains/)          pycharm+=$1
    }
    END {
      printf "- claude sessions : %5.1f GB\n", claude/1024/1024
      printf "- Chrome (all)    : %5.1f GB\n", chrome/1024/1024
      printf "- Docker          : %5.1f GB\n", docker/1024/1024
      printf "- iTerm2          : %5.1f GB\n", iterm/1024/1024
      printf "- WhatsApp        : %5.1f GB\n", whatsapp/1024/1024
      printf "- superwhisper    : %5.1f GB\n", sw/1024/1024
      printf "- NordVPN         : %5.1f GB\n", nord/1024/1024
      printf "- PyCharm         : %5.1f GB\n", pycharm/1024/1024
    }'

  echo ""
  echo "## Active claude sessions with IDs"
  echo ""
  ps -eo pid,etime,stat,command | grep 'claude --' | grep -v grep | awk '{
    pid=$1; etime=$2; stat=$3
    resume=""; for(i=4;i<=NF;i++) if($i=="--resume") { resume=$(i+1); break }
    printf "- PID=%-6s STAT=%-3s up=%-12s %s\n", pid, stat, etime, (resume ? "ID="resume : "(new session, no --resume)")
  }'

  echo ""
  echo "## Suspended claude (T-state) — 100% safe to kill"
  echo ""
  zombies=$(ps -eo pid,tty,etime,stat,command | awk '/claude --/ && $4 ~ /T/')
  if [ -z "$zombies" ]; then
    echo "_(none found)_"
  else
    printf '%s\n' "$zombies" | awk '{
      printf "- PID=%-6s TTY=%-7s up=%s\n", $1, $2, $3
    }'
  fi

  echo ""
  echo "---"
  echo ""
  echo "_Recovery: \`cd <project-dir> && claude --resume <session-id>\` — JSONLs at \`~/.claude/projects/\`._"
} > "$OUT"

echo "$OUT"
