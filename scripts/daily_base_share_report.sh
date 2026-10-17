#!/data/data/com.termux/files/usr/bin/bash
set -u
export PATH="/data/data/com.termux/files/usr/bin:/system/bin"
export TZ="Asia/Tehran"

ROOT="$HOME/OptimusAI_V41_LIVE"
LOGDIR="$ROOT/output/base_share/logs"
mkdir -p "$LOGDIR"
LOG="$LOGDIR/daily_$(date +%Y%m%d).log"
exec >> "$LOG" 2>&1

echo
echo "===== START $(date '+%F %T %Z') ====="
cd "$ROOT" || exit 1

DOW="$(python -c 'from datetime import datetime; from zoneinfo import ZoneInfo; print(datetime.now(ZoneInfo("Asia/Tehran")).weekday())')"
case "$DOW" in
  5|6|0|1|2) ;;
  *)
    echo "STATUS=CLOSED_MARKET_NO_NEW_CAPTURE"
    echo "===== END ====="
    exit 0
    ;;
esac

echo "STEP=GIT_UPDATE"
git pull --ff-only origin main || { echo "STATUS=FAIL_GIT_UPDATE"; exit 1; }

echo "STEP=MARKET_WATCH_IDENTITY"
python -u market_watch_identity_catalog.py || { echo "STATUS=FAIL_MARKET_WATCH_CAPTURE"; exit 1; }

echo "STEP=WHOLE_MARKET_HISTORY_AND_RANKING"
python -u base_share_whole_market_first_pass.py || { echo "STATUS=FAIL_WHOLE_MARKET_REPORT"; exit 1; }

echo "STEP=FULL_PLAIN_SYMBOL_RANKING"
python -u base_share_plain_symbol_trend_report.py || { echo "STATUS=FAIL_PLAIN_SYMBOL_REPORT"; exit 1; }

echo "STEP=DAILY_RANK_CHANGE_COMPARISON"
python -u base_share_daily_rank_change_report.py || { echo "STATUS=FAIL_RANK_CHANGE_REPORT"; exit 1; }

echo "STATUS=DAILY_BASE_SHARE_AND_COMPARISON_COMPLETE"
echo "RANKING_JSON=$ROOT/output/base_share/latest_plain_symbol_trend_report.json"
echo "RANKING_TXT=$ROOT/output/base_share/latest_plain_symbol_trend_report.txt"
echo "COMPARISON_JSON=$ROOT/output/base_share/latest_daily_rank_change_report.json"
echo "COMPARISON_TXT=$ROOT/output/base_share/latest_daily_rank_change_report.txt"
echo "===== END $(date '+%F %T %Z') ====="
