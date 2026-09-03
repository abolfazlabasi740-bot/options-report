#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env"
  set +a
fi
: "${BALE_BOT_TOKEN:?BALE_BOT_TOKEN is not set}"
exec "${PYTHON_BIN:-python3}" "$ROOT/termux_bale_listener.py"
