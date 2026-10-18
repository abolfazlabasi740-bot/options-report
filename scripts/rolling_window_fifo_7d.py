#!/usr/bin/env python3
"""Rolling 7-Trading-Session FIFO Window (conservative policy).
- Preserves full-history scoring (final_score, weights, components).
- Restricts comparison/ranking/display views to the last 7 trading sessions.
- Adds rolling_window metadata to the JSON report.
"""
import json, os
from collections import defaultdict

BASE = os.path.expanduser('~/OptimusAI_V41_LIVE/output/base_share')
SRC = os.path.join(BASE, 'latest_plain_symbol_trend_report.json')
DST = os.path.join(BASE, 'latest_plain_symbol_trend_report_rolling7.json')
WINDOW_SIZE = 7
POLICY = 'FIFO_7_TRADING_DAYS'

def collect_dates(obj, dates):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in ('date', 'latest_market_date', 'session_date') and isinstance(v, str) and v.isdigit():
                dates.add(v)
            collect_dates(v, dates)
    elif isinstance(obj, list):
        for x in obj:
            collect_dates(x, dates)

def main():
    with open(SRC) as f:
        report = json.load(f)
    dates = set()
    collect_dates(report, dates)
    all_dates = sorted(d for d in dates if len(d) == 8)
    if len(all_dates) < WINDOW_SIZE:
        print(f'WARN: only {len(all_dates)} session dates found (< {WINDOW_SIZE}); window = all')
    window_dates = all_dates[-WINDOW_SIZE:]
    fifo_dropped = all_dates[-WINDOW_SIZE - 1] if len(all_dates) > WINDOW_SIZE else None
    window_set = set(window_dates)
    kept = 0
    def filter_rows(obj):
        nonlocal kept
        if isinstance(obj, list):
            out = []
            for x in obj:
                if isinstance(x, dict):
                    d = x.get('date') or x.get('latest_market_date') or x.get('session_date')
                    if isinstance(d, str) and d.isdigit() and len(d) == 8 and d not in window_set:
                        continue
                    kept += 1
                out.append(filter_rows(x) if isinstance(x, (dict, list)) else x)
            return out
        if isinstance(obj, dict):
            return {k: filter_rows(v) for k, v in obj.items()}
        return obj
    filtered = filter_rows(report)
    filtered['rolling_window'] = {
        'policy': POLICY,
        'window_size': WINDOW_SIZE,
        'window_dates': window_dates,
        'fifo_dropped_date': fifo_dropped,
        'source_report': os.path.basename(SRC),
        'latest_history_date_preserved': report.get('latest_history_date'),
    }
    with open(DST, 'w') as f:
        json.dump(filtered, f, ensure_ascii=False, indent=1)
    print('STATUS = ROLLING_WINDOW_7D_COMPLETE')
    print('ALL_SESSION_DATES_COUNT =', len(all_dates))
    print('WINDOW_DATES =', window_dates)
    print('FIFO_DROPPED_DATE =', fifo_dropped)
    print('ROWS_KEPT =', kept)
    print('OUTPUT =', DST)

if __name__ == '__main__':
    main()
