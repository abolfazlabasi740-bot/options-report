#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ROOT="${OPTIMUSAI_ROOT:-$HOME/OptimusAI_V41_LIVE}"
PORT="${OPTIMUSAI_LLM_PORT:-8080}"
API_BASE="http://127.0.0.1:${PORT}/v1"
MODEL="${OPTIMUSAI_LLM_MODEL:-Qwen/Qwen3-0.6B-GGUF:Q8_0}"
SETUP="$ROOT/scripts/setup_local_llm.sh"

cd "$ROOT"

if ! curl --connect-timeout 2 --max-time 5 -fsS "$API_BASE/models" >/dev/null 2>&1; then
  echo "LOCAL_LLM_NOT_READY"
  echo "Starting local LLM..."
  bash "$SETUP"
fi

if ! curl --connect-timeout 2 --max-time 5 -fsS "$API_BASE/models" >/dev/null 2>&1; then
  echo "FAIL: local LLM API is not reachable at $API_BASE"
  exit 1
fi

export OPTIMUSAI_PROVIDER=local
export OPTIMUSAI_API_BASE="$API_BASE"
export OPTIMUSAI_API_KEY=local
export OPTIMUSAI_LLM_MODEL="$MODEL"

if [ -z "${OPTIMUSAI_TASK:-}" ]; then
  echo "FAIL: OPTIMUSAI_TASK is not set."
  echo "Example:"
  echo "OPTIMUSAI_TASK='Inspect project status and report evidence only.' bash scripts/run_local_agent.sh"
  exit 1
fi

echo "Checking required local Python module..."
python -c 'import requests' || {
  echo "FAIL: Python module requests is unavailable; no network package installation was attempted."
  exit 1
}

echo "Checking Agent syntax..."
python -m py_compile agent/project_manager.py scripts/run_project_manager.py

echo "Starting local Project Manager..."
exec python -u scripts/run_project_manager.py
