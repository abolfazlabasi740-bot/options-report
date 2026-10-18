#!/data/data/com.termux/files/usr/bin/bash
# wait_for_today_eod.sh — wait until TSETMC publishes today's EOD row in the
# daily closing-price history, then run the full report chain.
#
# Usage (Termux):
#   nohup bash scripts/wait_for_today_eod.sh >> output/base_share/logs/wait_eod_$(date +%Y%m%d).log 2>&1 &
#
# Behavior:
#   - Checks a small set of liquid symbols every CHECK_INTERVAL seconds.
#   - If EOD for "today" appears for any of them (data has landed), runs:
#       base_share_whole_market_first_pass.py
#       base_share_plain_symbol_trend_report.py
#       base_share_daily_rank_change_report.py
#       scripts/rolling_window_fifo_7d.py
#       scripts/build_management_analysis_report.py
#   - Non-trading days (Thu/Fri Tehran): exits immediately, nothing to wait for.
#   - Gives up after MAX_ATTEMPTS checks and logs clearly (no invented data).
set -u
export TZ="Asia/Tehran"

ROOT="$HOME/OptimusAI_V41_LIVE"
cd "$ROOT" || exit 1

CHECK_INTERVAL="${CHECK_INTERVAL:-1800}"   # 30 minutes
MAX_ATTEMPTS="${MAX_ATTEMPTS:-16}"         # up to 8 hours total

echo "[$(date '+%F %T %Z')] wait_for_today_eod started"

# Tehran trading days: Sat(5) Sun(6) Mon(0) Tue(1) Wed(2) in Python weekday()
DOW="$(python -c 'from datetime import datetime; from zoneinfo import ZoneInfo; print(datetime.now(ZoneInfo("Asia/Tehran")).weekday())')"
case "$DOW" in
  5|6|0|1|2) ;;
  *)
    echo "[$(date '+%F %T %Z')] STATUS=NON_TRADING_DAY_NO_WAIT"
    exit 0
    ;;
esac

TODAY="$(python -c 'from datetime import datetime; from zoneinfo import ZoneInfo; print(datetime.now(ZoneInfo("Asia/Tehran")).strftime("%Y%m%d"))')"
echo "[$(date '+%F %T %Z')] waiting for EOD date $TODAY"

check_eod() {
  python - "$TODAY" <<'PY'
import json, sys, urllib.request

target = sys.argv[1]
headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json",
           "Referer": "https://tsetmc.com/"}
# Liquid big names; if any of them has today's row, the EOD batch has landed.
# insCode values fetched from GetInstrumentSearch (TSETMC canonical ids).
PROBES = [
    ("فولاد",   "46348559193224090"),
    ("فملی",    "46348559193224090"),
]
# Re-resolve ids at runtime via search (robust against id churn).
def resolve(symbol):
    from urllib.parse import quote
    url = ("https://cdn.tsetmc.com/api/Instrument/GetInstrumentSearch/"
           + quote(symbol))
    req = urllib.request.Request(url, headers=headers)
    try:
        data = json.load(urllib.request.urlopen(req, timeout=20))
        recs = data.get("instrumentSearch") or []
        return recs[0]["insCode"] if recs else None
    except Exception:
        return None

found = False
for symbol, fallback in PROBES:
    ins = resolve(symbol) or fallback
    if not ins:
        continue
    url = f"https://cdn.tsetmc.com/api/ClosingPrice/GetClosingPriceDailyList/{ins}/0"
    req = urllib.request.Request(url, headers=headers)
    try:
        data = json.load(urllib.request.urlopen(req, timeout=30))
        rows = data.get("closingPriceDaily") or []
        if any(str(r.get("dEven")) == target for r in rows):
            found = True
            break
    except Exception:
        continue
print("EOD_LANDED" if found else "NOT_YET")
PY
}

attempt=1
while [ "$attempt" -le "$MAX_ATTEMPTS" ]; do
  result="$(check_eod)"
  echo "[$(date '+%F %T %Z')] attempt $attempt/$MAX_ATTEMPTS: $result"
  if [ "$result" = "EOD_LANDED" ]; then
    echo "[$(date '+%F %T %Z')] EOD for $TODAY detected — running full chain"
    python -u base_share_whole_market_first_pass.py      || { echo "STATUS=FAIL_WHOLE_MARKET"; exit 1; }
    python -u base_share_plain_symbol_trend_report.py    || { echo "STATUS=FAIL_PLAIN_SYMBOL"; exit 1; }
    python -u base_share_daily_rank_change_report.py     || { echo "STATUS=FAIL_RANK_CHANGE (non-fatal, continuing)"; }
    python -u scripts/rolling_window_fifo_7d.py          || { echo "STATUS=FAIL_ROLLING7"; exit 1; }
    python -u scripts/build_management_analysis_report.py || { echo "STATUS=FAIL_MGMT_REPORT"; exit 1; }
    echo "[$(date '+%F %T %Z')] STATUS=CHAIN_COMPLETE_FOR_$TODAY"
    exit 0
  fi
  attempt=$((attempt + 1))
  sleep "$CHECK_INTERVAL"
done

echo "[$(date '+%F %T %Z')] STATUS=EOD_NOT_PUBLISHED_AFTER_${MAX_ATTEMPTS}_ATTEMPTS — run the chain manually tomorrow"
exit 1
