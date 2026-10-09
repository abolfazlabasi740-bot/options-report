#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

ROOT="${OPTIMUSAI_ROOT:-$HOME/OptimusAI_V41_LIVE}"
BRIDGE="$ROOT/scripts/termux_command_bridge_agent.py"
WORK="$HOME/.termux_command_bridge"
BOOT_DIR="$HOME/.termux/boot"
BOOT_SCRIPT="$BOOT_DIR/optimusai_bridge_watchdog.sh"
LOG="$WORK/boot_watchdog.log"

mkdir -p "$WORK" "$BOOT_DIR"
[ -f "$BRIDGE" ] || { echo "FAIL: bridge script missing: $BRIDGE"; exit 2; }

cat > "$BOOT_SCRIPT" <<'BOOT'
#!/data/data/com.termux/files/usr/bin/bash
set -u
ROOT="$HOME/OptimusAI_V41_LIVE"
WORK="$HOME/.termux_command_bridge"
LOCK="$WORK/bridge_agent.lock"
LOG="$WORK/boot_watchdog.log"
mkdir -p "$WORK"
if command -v termux-wake-lock >/dev/null 2>&1; then
  termux-wake-lock >>"$LOG" 2>&1 || true
fi
echo "[$(date -Iseconds)] watchdog started" >>"$LOG"
while true; do
  PID=""
  [ -f "$LOCK" ] && PID="$(cat "$LOCK" 2>/dev/null || true)"
  if [ -z "$PID" ] || ! kill -0 "$PID" 2>/dev/null; then
    echo "[$(date -Iseconds)] bridge absent; starting" >>"$LOG"
    cd "$ROOT" || { echo "project directory missing" >>"$LOG"; sleep 30; continue; }
    python "$ROOT/scripts/termux_command_bridge_agent.py" >>"$LOG" 2>&1 || true
  fi
  sleep 30
done
BOOT
chmod 700 "$BOOT_SCRIPT"

if command -v termux-wake-lock >/dev/null 2>&1; then
  termux-wake-lock || true
fi

echo "BOOT_WATCHDOG_INSTALLED=$BOOT_SCRIPT"
echo "TERMUX_BOOT_APP_NOTE=The Termux:Boot Android add-on must be installed and allowed to run at device startup."
echo "WAKE_LOCK_AVAILABLE=$(command -v termux-wake-lock >/dev/null 2>&1 && echo yes || echo no)"
