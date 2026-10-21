#!/data/data/com.termux/files/usr/bin/sh
PID_FILE="$HOME/OptimusAI_V41_LIVE/output/server.pid"
PORT=8080
TARGET_DIR="$HOME/OptimusAI_V41_LIVE/android_app/www"

# آزاد کردن پورت در صورت اشغال بودن
fuser -k ${PORT}/tcp >/dev/null 2>&1
if [ -f "$PID_FILE" ]; then
  kill -9 $(cat "$PID_FILE") >/dev/null 2>&1
  rm -f "$PID_FILE"
fi

cd "$TARGET_DIR" || exit 1
nohup python -m http.server $PORT --bind 127.0.0.1 >/dev/null 2>&1 &
echo $! > "$PID_FILE"
echo "✅ Server started on http://127.0.0.1:$PORT (PID: $(cat "$PID_FILE"))"
