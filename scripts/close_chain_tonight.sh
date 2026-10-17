#!/data/data/com.termux/files/usr/bin/bash
cd ~/OptimusAI_V41_LIVE
LOG=logs/close_chain_tonight.log
for attempt in 1 2 3; do
  python3 base_share_whole_market_first_pass.py > /dev/null 2>&1
  LH=$(python3 -c "import json;print(json.load(open('output/base_share/latest_whole_market_opportunity_report.json')).get('latest_history_date'))")
  [ "$LH" = "20261017" ] && break
  sleep 1800
done
if [ "$LH" != "20261017" ]; then
  echo "$(date '+%F %T') EOD 20261017 هنوز در TSETMC نبود (بعد از ۳ تلاش)" >> $LOG
  exit 1
fi
python3 base_share_plain_symbol_trend_report.py >> $LOG 2>&1
python3 scripts/rolling_window_fifo_7d.py >> $LOG 2>&1
python3 scripts/build_option_enabled_ranking.py >> $LOG 2>&1
python3 - << 'PYEOF' >> $LOG 2>&1
import json, shutil, os
t = json.load(open('output/base_share/latest_plain_symbol_trend_report.json'))
assert t.get('latest_history_date') == '20261017', 'stale'
rw = json.load(open('output/base_share/latest_plain_symbol_trend_report_rolling7.json'))['rolling_window']
os.makedirs('output/central_archive/2026-10-17/base_share', exist_ok=True)
for f in ['latest_whole_market_opportunity_report.json', 'latest_plain_symbol_trend_report.json',
          'latest_plain_symbol_trend_report_rolling7.json']:
    shutil.copy(f'output/base_share/{f}', f'output/central_archive/2026-10-17/base_share/')
print('✅ CHAIN CLOSED & ARCHIVED | data:', t['latest_history_date'],
      '| window:', rw['window_dates'], '| dropped:', rw['fifo_dropped_date'])
PYEOF
