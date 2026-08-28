#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

PROJECT_ROOT="${PROJECT_ROOT:-$HOME/options_report}"
RUN_PIPELINE="${RUN_PIPELINE:-$PROJECT_ROOT/run_pipeline.ps1}"
REPORTS_DIR="${REPORTS_DIR:-$PROJECT_ROOT/reports}"
HASH_FILE="${HASH_FILE:-$PROJECT_ROOT/.last_report_hash}"
LOG_FILE="${LOG_FILE:-$PROJECT_ROOT/termux_bale.log}"
ENV_FILE="${ENV_FILE:-$PROJECT_ROOT/.env}"

now() { date '+%Y-%m-%d %H:%M:%S'; }

log() {
  echo "$(now) | $*" | tee -a "$LOG_FILE"
}

load_env() {
  [[ -f "$ENV_FILE" ]] || return 0
  while IFS='=' read -r k v; do
    [[ -z "${k:-}" ]] && continue
    [[ "${k:0:1}" == "#" ]] && continue
    v="${v%\"}"; v="${v#\"}"
    v="${v%\'}"; v="${v#\'}"
    export "$k=$v"
  done < <(grep -E '^[A-Za-z_][A-Za-z0-9_]*=' "$ENV_FILE" || true)
}

latest_report() {
  find "$REPORTS_DIR" -maxdepth 1 -type f -name '*_options_report.md' -printf '%T@ %p\n' 2>/dev/null \
    | sort -nr | head -n 1 | cut -d' ' -f2-
}

run_pipeline() {
  if [[ -x "$(command -v pwsh)" ]]; then
    pwsh -NoProfile -File "$RUN_PIPELINE" "$@"
  else
    log "pwsh نصب نیست"
    exit 1
  fi
}

send_bale() {
  local token="${BALE_BOT_TOKEN:-}"
  local chat_id="${BALE_CHAT_ID:-}"

  [[ -n "$token" && -n "$chat_id" ]] || {
    log "BALE_BOT_TOKEN یا BALE_CHAT_ID تنظیم نشده"
    exit 1
  }

  local url="https://tapi.bale.ai/bot${token}/sendMessage"
  local text="$1"
  local max=4000
  local start=0
  local len=${#text}
  local part idx=1

  while (( start < len )); do
    part="${text:start:max}"
    python3 - <<PY
import requests
url = ${url@Q}
payload = {
    "chat_id": ${chat_id@Q},
    "text": ${part@Q}
}
r = requests.post(url, json=payload, timeout=30)
print(r.status_code)
print(r.text)
if r.status_code != 200:
    raise SystemExit(1)
PY
    log "تکه $idx ارسال شد"
    start=$((start + max))
    idx=$((idx + 1))
  done
}

main() {
  mkdir -p "$PROJECT_ROOT"
  touch "$LOG_FILE"

  load_env

  log "شروع اجرا"

  [[ -f "$RUN_PIPELINE" ]] || {
    log "run_pipeline.ps1 یافت نشد: $RUN_PIPELINE"
    exit 1
  }

  if [[ "${1:-}" == "--run" ]]; then
    shift
    log "اجرای Pipeline: $RUN_PIPELINE"
    run_pipeline "$@"
  fi

  [[ -d "$REPORTS_DIR" ]] || {
    log "پس از اجرای Pipeline پوشه reports ایجاد نشد: $REPORTS_DIR"
    exit 1
  }

  report="$(latest_report)"
  [[ -n "${report:-}" && -f "$report" ]] || { log "گزارش پیدا نشد"; exit 1; }

  hash="$(sha256sum "$report" | awk '{print $1}')"
  last_hash="$(tr -d '[:space:]' < "$HASH_FILE" 2>/dev/null || true)"

  if [[ -n "$last_hash" && "$last_hash" == "$hash" ]]; then
    log "گزارش تکراری؛ ارسال نشد | hash=$hash"
    exit 0
  fi

  text="$(cat "$report")"
  send_bale "$text"

  printf '%s\n' "$hash" > "$HASH_FILE"
  log "ارسال موفق | $(basename "$report") | hash=$hash"
}

main "$@"
