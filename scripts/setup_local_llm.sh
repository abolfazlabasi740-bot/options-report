#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ROOT="${OPTIMUSAI_ROOT:-$HOME/OptimusAI_V41_LIVE}"
LLAMA_ROOT="${OPTIMUSAI_LLAMA_ROOT:-$HOME/llama.cpp}"
MODEL_REF="${OPTIMUSAI_LLM_MODEL_REF:-Qwen/Qwen3-4B-GGUF:Q4_K_M}"
PORT="${OPTIMUSAI_LLM_PORT:-8080}"
API_BASE="http://127.0.0.1:${PORT}/v1"
LOG_DIR="$ROOT/output/local_llm"
PID_FILE="$LOG_DIR/llama-server.pid"
LOG_FILE="$LOG_DIR/llama-server.log"

mkdir -p "$LOG_DIR"
command -v pkg >/dev/null 2>&1 || { echo "FAIL: Termux required"; exit 1; }
cd "$ROOT"

# Termux's official documentation lists multiple package mirrors and explicitly notes
# that mirror availability can vary by network/country. Probe several official mirrors
# and select the first reachable one instead of assuming packages.termux.dev is reachable.
MIRRORS=(
  "https://packages-cf.termux.dev/apt/termux-main"
  "https://mirror.rinarin.dev/termux/termux-main"
  "https://linux.domainesia.com/applications/termux/termux-main"
  "https://mirror.twds.com.tw/termux/termux-main"
  "https://mirrors.cbrx.io/apt/termux/termux-main"
  "https://md.mirrors.hacktegic.com/termux/termux-main"
  "https://nl.mirror.flokinet.net/termux/termux-main"
  "https://ro.mirror.flokinet.net/termux/termux-main"
)

echo "[1/6] Selecting reachable Termux package mirror..."
command -v curl >/dev/null 2>&1 || { echo "FAIL: curl is required and is not available"; exit 1; }
SELECTED=""
for mirror in "${MIRRORS[@]}"; do
  if curl -4 -fsSI --connect-timeout 5 --max-time 10 "$mirror/dists/stable/InRelease" >/dev/null 2>&1; then
    SELECTED="$mirror"
    break
  fi
done

if [ -z "$SELECTED" ]; then
  echo "FAIL: no official Termux mirror is reachable."
  echo "The original packages.termux.dev connection is unavailable from this network."
  exit 1
fi

echo "TERMUX_MIRROR=$SELECTED"
MAIN_SOURCE="$PREFIX/etc/apt/sources.list"
printf 'deb %s stable main\n' "$SELECTED" > "$MAIN_SOURCE"

echo "[2/6] Installing build prerequisites..."
apt-get update
apt-get install -y git cmake make clang curl python

echo "[3/6] Preparing llama.cpp..."
if [ ! -d "$LLAMA_ROOT/.git" ]; then
  git clone --depth=1 https://github.com/ggml-org/llama.cpp.git "$LLAMA_ROOT"
else
  git -C "$LLAMA_ROOT" pull --ff-only
fi

if [ ! -x "$LLAMA_ROOT/build/bin/llama-server" ]; then
  echo "[4/6] Building llama-server..."
  cmake -S "$LLAMA_ROOT" -B "$LLAMA_ROOT/build" -DCMAKE_BUILD_TYPE=Release
  cmake --build "$LLAMA_ROOT/build" -j "$(nproc)" --target llama-server
else
  echo "[4/6] llama-server already built."
fi

LLAMA_SERVER="$LLAMA_ROOT/build/bin/llama-server"
[ -x "$LLAMA_SERVER" ] || { echo "FAIL: llama-server build missing"; exit 1; }

echo "[5/6] Checking RAM and starting local server..."
awk '/MemTotal/ {printf "RAM_MB=%d\\n", $2/1024}' /proc/meminfo || true

if [ -f "$PID_FILE" ]; then
  PID="$(cat "$PID_FILE" 2>/dev/null || true)"
  if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
    echo "Existing llama-server is running (PID $PID)."
  else
    rm -f "$PID_FILE"
  fi
fi

if [ ! -f "$PID_FILE" ]; then
  nohup "$LLAMA_SERVER" \
    -hf "$MODEL_REF" \
    --host 127.0.0.1 \
    --port "$PORT" \
    -c 8192 \
    -t "${OPTIMUSAI_THREADS:-6}" \
    --parallel 1 \
    >"$LOG_FILE" 2>&1 &
  echo $! > "$PID_FILE"
fi

echo "[6/6] Waiting for local API..."
READY=0
for i in $(seq 1 120); do
  if curl -fsS "$API_BASE/models" >/tmp/optimusai_llm_models.json 2>/dev/null; then
    READY=1
    break
  fi
  sleep 2
done

if [ "$READY" -ne 1 ]; then
  echo "FAIL: local LLM did not become ready."
  echo "Log: $LOG_FILE"
  tail -n 100 "$LOG_FILE" || true
  exit 1
fi

export OPTIMUSAI_PROVIDER=local
export OPTIMUSAI_API_BASE="$API_BASE"
export OPTIMUSAI_API_KEY=local
export OPTIMUSAI_LLM_MODEL="$MODEL_REF"

python -m py_compile agent/project_manager.py scripts/run_project_manager.py
git status --short

echo "LOCAL_LLM_READY"
echo "API=$API_BASE"
echo "MODEL=$MODEL_REF"
echo "LOG=$LOG_FILE"
echo "NEXT: export OPTIMUSAI_TASK='...' && python scripts/run_project_manager.py"
