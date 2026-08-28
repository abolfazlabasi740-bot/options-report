#!/data/data/com.termux/files/usr/bin/bash

set -u

PROJECT_DIR="$HOME/options_report"
cd "$PROJECT_DIR" || exit 1

# زمان ایران
export TZ="Asia/Tehran"

# روزهای مجاز به تقویم پایتون:
# شنبه=5، یکشنبه=6، دوشنبه=0، سه‌شنبه=1، چهارشنبه=2
weekday=$(python3 - <<'PY'
from datetime import datetime
print(datetime.now().weekday())
PY
)

case "$weekday" in
    5|6|0|1|2)
        ;;
    *)
        echo "امروز روز معاملاتی نیست."
        exit 0
        ;;
esac

current_hm=$(date '+%H%M')

case "$current_hm" in
    0915|0945|1015|1045|1115|1145|1215)
        ;;
    *)
        echo "این زمان، زمان برنامه‌ریزی‌شده گزارش نیست: $current_hm"
        exit 0
        ;;
esac

today=$(date '+%Y%m%d')
slot=$(date '+%H%M')
marker=".sent_${today}_${slot}"

# جلوگیری از ارسال تکراری در یک بازه زمانی
if [ -f "$marker" ]; then
    echo "گزارش بازه $slot قبلاً ارسال شده است."
    exit 0
fi

ts=$(date '+%Y%m%d_%H%M%S')
new_file="optionschool24_all_${ts}.xlsx"
tmp_file=".download_${ts}.tmp"

echo "دانلود فایل Optionschool24 در بازه $slot ..."

curl -L --fail --silent --show-error \
    --connect-timeout 30 \
    --max-time 120 \
    "https://s3.optionschool24.com/export/excel?type=1" \
    -o "$tmp_file" || {
        echo "خطا در دانلود فایل."
        rm -f "$tmp_file"
        exit 1
    }

bytes=$(stat -c%s "$tmp_file" 2>/dev/null || echo 0)

if [ "$bytes" -lt 5000 ]; then
    echo "فایل دانلودشده معتبر نیست؛ حجم: $bytes bytes"
    rm -f "$tmp_file"
    exit 1
fi

mv -f "$tmp_file" "$new_file"

echo "فایل ورودی:"
stat -c 'نام: %n | زمان: %y | حجم: %s bytes' "$new_file"
sha256sum "$new_file"

# چون هر بازه باید پیام جداگانه ارسال کند،
# کنترل هش ارسال قبلی موقتاً حذف می‌شود.
rm -f .last_report_hash

if ./run_options_report.sh; then
    touch "$marker"
    echo "گزارش بازه $slot با موفقیت تولید و ارسال شد."
else
    echo "خطا در تولید یا ارسال گزارش."
    rm -f "$marker"
    exit 1
fi

# حذف نشانگرهای قدیمی‌تر از ۱۰ روز
find . -maxdepth 1 -type f -name '.sent_*' -mtime +10 -delete
