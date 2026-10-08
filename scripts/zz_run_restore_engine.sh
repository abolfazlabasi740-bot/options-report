#!/data/data/com.termux/files/usr/bin/bash
set -e
bash scripts/zz_restore_engine_from_history.sh
python -m py_compile last_minute_profit_engine.py
