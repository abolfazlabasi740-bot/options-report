#!/data/data/com.termux/files/usr/bin/bash
cd ~/OptimusAI_V41_LIVE
MODE=$(python3 -c "import sys; sys.path.insert(0,'scripts'); from freshness_gate import get_data_mode; print(get_data_mode())")
if [ "$MODE" = "LIVE" ]; then
    python3 scripts/fetch_tsetmc_live.py >> ~/logs/hourly.log 2>&1
fi
python3 scripts/theory_gap_3pct.py >> ~/logs/hourly.log 2>&1
# ارسال آخرین گزارش به بات بله (در صورت آماده بودن)
# python3 scripts/send_bale.py --latest >> ~/logs/hourly.log 2>&1
