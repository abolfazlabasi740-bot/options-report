#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

LATEST_EXCEL=$(ls -t data/optionschool24_all_*.xlsx 2>/dev/null | head -n 1)

if [ -z "$LATEST_EXCEL" ]; then
    echo "خطا: هیچ فایل اکسلی در پوشه data یافت نشد."
    exit 1
fi

echo "در حال پردازش جدیدترین فایل: $LATEST_EXCEL"
python3 generate_report.py "$LATEST_EXCEL"
python3 send_report.py
