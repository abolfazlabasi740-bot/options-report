#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

PIDFILE="$HOME/OptimusAI_V41_LIVE/android_app/service/http8080.pid"
if [[ -f "$PIDFILE" ]]; then
  PID="$(cat "$PIDFILE" || true)"
  if [[ -n "${PID:-}" ]] && kill -0 "$PID" >/dev/null 2>&1; then
    kill "$PID" || true
    sleep 0.2
  fi
  rm -f "$PIDFILE"
fi
echo "Stopped."
