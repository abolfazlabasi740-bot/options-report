#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ROOT="$HOME/OptimusAI_V41_LIVE"
WWW="$ROOT/android_app/www"
LOGDIR="$ROOT/android_app/service/logs"
PIDFILE="$ROOT/android_app/service/http8080.pid"

mkdir -p "$LOGDIR"
mkdir -p "$WWW"

# 1) Sync bundle (Fail-Closed: اگر نبود، از همان run_android_build_pipeline.py استفاده می‌کنیم که سیاست را اعمال می‌کند)
python "$ROOT/run_android_build_pipeline.py" >> "$LOGDIR/pipeline.log" 2>&1

# 2) اگر سرویس قبلاً بالا است، خروج تمیز
if [[ -f "$PIDFILE" ]]; then
  PID="$(cat "$PIDFILE" || true)"
  if [[ -n "${PID:-}" ]] && kill -0 "$PID" >/dev/null 2>&1; then
    echo "Already running: PID=$PID" >> "$LOGDIR/server.log"
    exit 0
  fi
fi

# 3) اگر پورت اشغال است، پروسه قبلی خودمان را kill می‌کنیم، غیرخودی را Fail-Closed می‌کنیم
if command -v lsof >/dev/null 2>&1; then
  PIDS="$(lsof -t -iTCP:8080 -sTCP:LISTEN 2>/dev/null || true)"
  if [[ -n "${PIDS:-}" ]]; then
    # فقط اگر از خودمان است (python http.server) می‌بندیم
    if ps -o args= -p "${PIDS%%$'\n'*}" 2>/dev/null | grep -q "http.server 8080"; then
      kill $PIDS || true
      sleep 0.2
    else
      echo "FAIL-CLOSED: Port 8080 in use by non-owned process: $PIDS" >> "$LOGDIR/server.log"
      exit 10
    fi
  fi
fi

# 4) اجرای سرور
nohup python -m http.server 8080 --directory "$WWW" >> "$LOGDIR/server.log" 2>&1 &
echo $! > "$PIDFILE"
echo "Started: PID=$(cat "$PIDFILE")" >> "$LOGDIR/server.log"
