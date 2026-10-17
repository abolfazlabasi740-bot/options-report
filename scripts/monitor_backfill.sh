#!/data/data/com.termux/files/usr/bin/bash
# ── پایش خودکار Backfill v2 ──
# هر ۲۰ دقیقه چک می‌کنه، وقتی تموم شد بازرسی نهایی اجرا می‌کنه

cd ~/OptimusAI_V41_LIVE
LOG="output/history/tsetmc/monitor.log"
REPORT="output/history/tsetmc/final_report.txt"
INTERVAL=1200  # ۲۰ دقیقه = ۱۲۰۰ ثانیه

echo "🤖 مانیتور استارت شد — $(date)" | tee "$LOG"

while true; do
    PID=$(cat output/history/tsetmc/backfill_v2.pid 2>/dev/null)
    
    if [ -z "$PID" ]; then
        echo "[$(date '+%H:%M:%S')] ❌ فایل PID پیدا نشد!" | tee -a "$LOG"
        break
    fi
    
    if kill -0 "$PID" 2>/dev/null; then
        # ── هنوز در حال اجرا ──
        LAST_LINE=$(tail -1 output/history/tsetmc/backfill_v2.log)
        echo "[$(date '+%H:%M:%S')] ✅ ALIVE → $LAST_LINE" | tee -a "$LOG"
        sleep "$INTERVAL"
    else
        # ── پروسه تموم شد! بازرسی نهایی ──
        echo "" | tee -a "$LOG"
        echo "[$(date '+%H:%M:%S')] 🏁 پروسه تموم شد! در حال اجرای بازرسی نهایی..." | tee -a "$LOG"
        echo ""
        
        {
            echo "═══════════════════════════════════════════"
            echo "  📋 گزارش نهایی Backfill v2"
            echo "  زمان: $(date)"
            echo "═══════════════════════════════════════════"
            echo ""
            echo "── فایل‌های خروجی ──"
            ls -lh output/history/tsetmc/backfill_2026101*.json 2>/dev/null | grep -v INSUFFICIENT
            echo ""
            echo "── بازرسی دقیق ──"
            python3 -c "
import json, glob
for f in sorted(glob.glob('output/history/tsetmc/backfill_2026*.json')):
    if 'INSUFFICIENT_FAILED' in f:
        continue
    d = json.load(open(f))
    obs_list = d.get('observations', [])
    obs = obs_list[0] if obs_list else {}
    rows = obs.get('rows', [])
    ok = sum(1 for r in rows if r.get('status') != 'INSUFFICIENT')
    insuf = sum(1 for r in rows if r.get('status') == 'INSUFFICIENT')
    print(f'📄 {f}')
    print(f'   status:        {d.get(\"status\")}')
    print(f'   target_date:   {d.get(\"target_date\")}')
    print(f'   total_rows:    {len(rows)}')
    print(f'   ok:            {ok}')
    print(f'   insufficient:  {insuf}')
    print(f'   error_count:   {d.get(\"error_count\", 0)}')
    print(f'   universe:      {d.get(\"total_universe\")}')
    print(f'   sha256:        {d.get(\"snapshot_sha256\", \"\")[:32]}...')
    print()
"
            echo "── چک‌پوینت‌ها ──"
            ls output/history/tsetmc/checkpoint_*.json 2>/dev/null && echo "⚠️ هنوز موجوده (ناقص)" || echo "✅ همه پاک شدن"
            echo ""
            echo "── آخرین لاگ ──"
            tail -20 output/history/tsetmc/backfill_v2.log
            echo ""
            echo "═══════════════════════════════════════════"
            echo "  ✅ بازرسی نهایی کامل شد"
            echo "═══════════════════════════════════════════"
        } | tee "$REPORT" | tee -a "$LOG"
        
        # ── نوتیفیکیشن Termux ──
        termux-notification -t "Backfill v2 ✅" --content "پروسه تموم شد! گزارش در final_report.txt" 2>/dev/null
        
        echo "[$(date '+%H:%M:%S')] ✅ گزارش نهایی ذخیره شد: $REPORT" | tee -a "$LOG"
        break
    fi
done

echo "🤖 مانیتور پایان یافت — $(date)" | tee -a "$LOG"
