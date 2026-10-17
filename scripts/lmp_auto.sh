#!/data/data/com.termux/files/usr/bin/bash
# ═══════════════════════════════════════════════════════════
#  🤖 LMP Auto v2 — پایشگر ۲۴ ساعته اسکنر سود لحظه آخری
#  بازار باز:    هر ۷ دقیقه  (شنبه تا چهارشنبه ۹:۰۰–۱۲:۳۰)
#  بعد از بازار: هر ۳۰ دقیقه (۱۲:۳۰–۲۴:۰۰ روز معاملاتی)
#  شب/تعطیل:     هر ۶۰ دقیقه
# ═══════════════════════════════════════════════════════════

cd ~/OptimusAI_V41_LIVE
LOG="output/reports/lmp/auto.log"
mkdir -p output/reports/lmp

echo "🤖 LMP Auto v2 (24h) استارت — $(date)" | tee -a "$LOG"

while true; do
    HOUR=$(date +%H | sed 's/^0//')
    MIN=$(date +%M | sed 's/^0//')
    DAY=$(date +%u)  # 1=Mon...7=Sun

    # روزهای معاملاتی: شنبه(6)، یکشنبه(7)، دوشنبه(1)، سه‌شنبه(2)، چهارشنبه(3)
    case "$DAY" in
        1|2|3|6|7) TRADING=1 ;;
        *)         TRADING=0 ;;
    esac

    # تعیین بازه و دوره اسکن
    INTERVAL=3600
    PHASE="🌑 شب/تعطیل"
    if [ "$TRADING" -eq 1 ]; then
        if [ "$HOUR" -ge 9 ] && { [ "$HOUR" -lt 12 ] || { [ "$HOUR" -eq 12 ] && [ "$MIN" -le 30 ]; }; }; then
            INTERVAL=420
            PHASE="🟢 بازار باز"
        elif [ "$HOUR" -ge 12 ]; then
            INTERVAL=1800
            PHASE="🌙 بعد از بازار (آمادگی فردا)"
        elif [ "$HOUR" -lt 6 ]; then
            INTERVAL=3600
            PHASE="🌑 بامداد"
        else
            INTERVAL=1800
            PHASE="🌅 قبل از بازار"
        fi
    fi

    echo "[$(date '+%H:%M:%S')] $PHASE ▶️ اسکن..." | tee -a "$LOG"
    python3 scripts/lmp_scanner.py >> "$LOG" 2>&1 \
        && echo "[$(date '+%H:%M:%S')] ✅ تمام" | tee -a "$LOG" \
        || echo "[$(date '+%H:%M:%S')] ⚠️ خطا در اسکن" | tee -a "$LOG"

    echo "[$(date '+%H:%M:%S')] 😴 خواب $((INTERVAL/60)) دقیقه" | tee -a "$LOG"
    sleep "$INTERVAL"
done
