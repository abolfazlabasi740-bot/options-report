#!/data/data/com.termux/files/usr/bin/bash
set -u

ROOT="$HOME/OptimusAI_V41_LIVE"
LOG_DIR="$ROOT/output/history"
LOG_FILE="$LOG_DIR/market_collector_runner.log"
LOCK_DIR="$LOG_DIR/.market_collector_runner.lock"

mkdir -p "$LOG_DIR"
cd "$ROOT" || exit 1

# One persistent runner owns the market-session schedule.
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  printf '%s RUNNER_ALREADY_RUNNING\n' "$(date '+%Y-%m-%d %H:%M:%S %Z')" >> "$LOG_FILE"
  exit 0
fi
trap 'rmdir "$LOCK_DIR" 2>/dev/null || true' EXIT

export TZ="Asia/Tehran"

while true; do
  weekday="$(date '+%u')"
  hour="$(date '+%H')"
  minute="$(date '+%M')"
  current_minutes=$((10#$hour * 60 + 10#$minute))

  # Saturday-Wednesday only: 6,7,1,2,3
  case "$weekday" in
    1|2|3|6|7) ;;
    *)
      sleep 300
      continue
      ;;
  esac

  start_minutes=$((9 * 60 + 30))
  end_minutes=$((12 * 60 + 30))

  if [ "$current_minutes" -lt "$start_minutes" ]; then
    sleep_seconds=$(( (start_minutes - current_minutes) * 60 ))
    sleep "$sleep_seconds"
    continue
  fi

  if [ "$current_minutes" -gt "$end_minutes" ]; then
    sleep 300
    continue
  fi

  # Collect only on exact half-hour slots.
  if [ "$minute" = "00" ] || [ "$minute" = "30" ]; then
    {
      printf '\n=== %s ===\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
      printf 'TEHRAN_SLOT = %s\n' "$(date '+%Y-%m-%d %H:%M:%S %Z')"
      python collect_tsetmc_history.py
      printf 'COLLECTOR_RC = %s\n' "$?"
    } >> "$LOG_FILE" 2>&1

    # Move away from the slot so the same slot cannot be collected twice.
    sleep 61
  else
    remainder=$((current_minutes % 30))
    sleep_seconds=$(( (30 - remainder) * 60 - 5 ))
    [ "$sleep_seconds" -lt 5 ] && sleep_seconds=5
    sleep "$sleep_seconds"
  fi
done
