#!/data/data/com.termux/files/usr/bin/bash
set -u

ROOT="$HOME/OptimusAI_V41_LIVE"
LOG_DIR="$ROOT/output/history"
LOG_FILE="$LOG_DIR/collector_job.log"

mkdir -p "$LOG_DIR"
cd "$ROOT" || exit 1

{
  printf '\n=== %s ===\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  python collect_tsetmc_history.py
} >> "$LOG_FILE" 2>&1

exit $?
