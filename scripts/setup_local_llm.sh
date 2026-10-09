#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ROOT="${OPTIMUSAI_ROOT:-$HOME/OptimusAI_V41_LIVE}"
LLAMA_ROOT="${OPTIMUSAI_LLAMA_ROOT:-$HOME/llama.cpp}"
# Start small to verify local inference and tool-call plumbing on Android.
MODEL_REF="${OPTIMUSAI_LLM_MODEL_REF:-Qwen/Qwen3-0.6B-GGUF:Q4_K_M}"
PORT="${OPTIMUSAI_LLM_PORT:-8080}"
CONTEXT="${OPTIMUSAI_CONTEXT:-2048}"
THREADS="${OPTIMUSAI_THREADS:-4}"
API_BASE="http://127.0.0.1:${PORT}/v1"
LOG_DIR="$ROOT/output/local_llm"
PID_FILE="$LOG_DIR/llama-server.pid"
LOG_FILE="$LOG_DIR/llama-server.log"
MODELS_FILE="$LOG_DIR/models.json"

mkdir -p "$LOG_DIR"
command -v pkg >/dev/null 2>&1 || { echo "FAIL: Termux required"; exit 1; }
command -v curl >/dev/null 2>&1 || { echo "FAIL: curl is required and is not available"; exit 1; }
cd "$ROOT"

echo "[1/5] Checking llama.cpp binary..."
LLAMA_SERVER="$LLAMA_ROOT/build/bin/llama-server"
if [ ! -x "$LLAMA_SERVER" ]; then
  echo "FAIL: llama-server binary missing at $LLAMA_SERVER"
  exit 1
fi

echo "[2/5] Recording memory and stopping stale server..."
awk '/MemTotal|MemAvailable|SwapFree/ {print}' /proc/meminfo || true
if [ -f "$PID_FILE" ]; then
  OLD_PID="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
    kill "$OLD_PID" 2>/dev/null || true
    for _ in $(seq 1 10); do
      kill -0 "$OLD_PID" 2>/dev/null || break
      sleep 1
    done
    kill -9 "$OLD_PID" 2>/dev/null || true
  fi
  rm -f "$PID_FILE"
fi

echo "[3/5] Starting low-memory model configuration..."
: > "$LOG_FILE"
nohup "$LLAMA_SERVER" \
  -hf "$MODEL_REF" \
  --jinja \
  --reasoning off \
  --host 127.0.0.1 \
  --port "$PORT" \
  -c "$CONTEXT" \
  -t "$THREADS" \
  -b 128 \
  -ub 64 \
  --parallel 1 \
  --fit on \
  >"$LOG_FILE" 2>&1 &
SERVER_PID=$!
echo "$SERVER_PID" > "$PID_FILE"
echo "SERVER_PID=$SERVER_PID"
echo "MODEL=$MODEL_REF"
echo "CONTEXT=$CONTEXT THREADS=$THREADS BATCH=128 UBATCH=64"

echo "[4/5] Waiting up to 10 minutes for the API..."
READY=0
rm -f "$MODELS_FILE"
for _ in $(seq 1 300); do
  if ! kill -0 "$SERVER_PID" 2>/dev/null; then
    echo "FAIL: llama-server exited before API became ready."
    break
  fi
  if curl --connect-timeout 2 --max-time 5 -fsS "$API_BASE/models" >"$MODELS_FILE" 2>/dev/null; then
    READY=1
    break
  fi
  sleep 2
done

if [ "$READY" -ne 1 ]; then
  echo "LOCAL_LLM_START_FAILED"
  echo "LOG=$LOG_FILE"
  tail -n 120 "$LOG_FILE" || true
  awk '/MemTotal|MemAvailable|SwapFree/ {print}' /proc/meminfo || true
  exit 1
fi

export OPTIMUSAI_PROVIDER=local
export OPTIMUSAI_API_BASE="$API_BASE"
export OPTIMUSAI_API_KEY=local
export OPTIMUSAI_LLM_MODEL="$MODEL_REF"

echo "[5/5] API is ready."
echo "LOCAL_LLM_READY"
echo "API=$API_BASE"
echo "MODEL=$MODEL_REF"
echo "LOG=$LOG_FILE"
