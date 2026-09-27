#!/data/data/com.termux/files/usr/bin/bash
set -u

ROOT="$HOME/OptimusAI_V41_LIVE"
LOG_DIR="$ROOT/output/history"
LOG_FILE="$LOG_DIR/collector_job.log"

mkdir -p "$LOG_DIR"
cd "$ROOT" || exit 1

# Tehran schedule: Saturday-Wednesday, 09:30 through 12:30,
# exactly on half-hour slots. The job scheduler itself is periodic,
# so align each invocation to the next half-hour slot before collecting.
export TZ="Asia/Tehran"

weekday="$(date '+%u')"   # Mon=1 ... Sun=7
hour="$(date '+%H')"
minute="$(date '+%M')"

# Allowed days: Saturday(6), Sunday(7), Monday(1), Tuesday(2), Wednesday(3).
case "$weekday" in
  1|2|3|6|7) ;;
  *) exit 0 ;;
esac

current_minutes=$((10#$hour * 60 + 10#$minute))
start_minutes=$((9 * 60 + 30))
end_minutes=$((12 * 60 + 30))

if [ "$current_minutes" -gt "$end_minutes" ]; then
  exit 0
fi

if [ "$current_minutes" -lt "$start_minutes" ]; then
  sleep_seconds=$(( (start_minutes - current_minutes) * 60 ))
  sleep "$sleep_seconds"
else
  remainder=$((current_minutes % 30))
  if [ "$remainder" -ne 0 ]; then
    sleep_minutes=$((30 - remainder))
    sleep_seconds=$((sleep_minutes * 60))
    sleep "$sleep_seconds"
  fi
fi

# Re-check the slot after alignment/sleep.
weekday="$(date '+%u')"
hour="$(date '+%H')"
minute="$(date '+%M')"
current_minutes=$((10#$hour * 60 + 10#$minute))

case "$weekday" in
  1|2|3|6|7) ;;
  *) exit 0 ;;
esac

if [ "$minute" != "00" ] && [ "$minute" != "30" ]; then
  exit 0
fi

if [ "$current_minutes" -lt "$start_minutes" ] || [ "$current_minutes" -gt "$end_minutes" ]; then
  exit 0
fi

{
  printf '\n=== %s ===\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  printf 'TEHRAN_SLOT = %s\n' "$(date '+%Y-%m-%d %H:%M:%S %Z')"
  python collect_tsetmc_history.py
} >> "$LOG_FILE" 2>&1

exit $?
