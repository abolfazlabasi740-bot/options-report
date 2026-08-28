#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
cd "$HOME/options_report"

LOG="$HOME/options_report/schedule.log"
DOWNLOAD_URL="${OPTIONSCHOOL24_URL:-https://s3.optionschool24.com/export/excel?type=1}"
FORCE="${FORCE:-0}"

now="$(date '+%Y-%m-%d %H:%M:%S')"
dow="$(date +%u)"
hour="$(date +%H)"
minute="$(date +%M)"

if [[ "$FORCE" != "1" ]]; then
  # شنبه تا چهارشنبه
  case "$dow" in 6|7|1|2|3) ;; *)
    echo "$now | خارج از روز بازار" >> "$LOG"; exit 0;; esac

  # ساعات بازار
  if (( 10#$hour < 9 || 10#$hour > 12 )); then
    echo "$now | خارج از ساعت بازار" >> "$LOG"; exit 0
  fi

  # دقیقه‌های ۱۵ تا ۲۰ و ۴۵ تا ۵۰ (تحمل تاخیر کرون)
  m=$((10#$minute))
  if ! (( (m >= 15 && m <= 20) || (m >= 45 && m <= 50) )); then
    echo "$now | خارج از دقیقه مجاز" >> "$LOG"; exit 0
  fi
fi

stamp="$(date +%s)"
tmp="download_$$.xlsx"

echo "$now | شروع دانلود خودکار" >> "$LOG"
curl -L --fail --silent --show-error \
  -H 'Cache-Control: no-cache' -H 'Pragma: no-cache' \
  -A 'Mozilla/5.0' "${DOWNLOAD_URL}&t=${stamp}" -o "$tmp"

[[ -s "$tmp" ]] || { echo "$now | فایل خالی دانلود شد" >> "$LOG"; rm -f "$tmp"; exit 1; }

mv "$tmp" "optionschool24_all_$(date +%Y%m%d_%H%M%S).xlsx"
latest="$(ls -t optionschool24_all_*.xlsx | head -n 1)"
echo "$now | فایل جدید دانلود شد: $latest" >> "$LOG"

# ⚠️ این خط را با فراخوانی واقعی تولید گزارش جایگزین کن
# report_text="$(bash generate_report.sh "$latest")"
report_text="$(head -c 200 "$latest" | base64)"   # فعلاً نمونه/پلاسبو

reporthash="$(printf '%s' "$report_text" | sha256sum | awk '{print $1}')"
hashfile=".last_report_hash"

if [[ -f "$hashfile" && "$(cat "$hashfile")" == "$reporthash" ]]; then
  echo "$now | گزارش بدون تغییر؛ ارسال لغو شد" >> "$LOG"
  exit 0
fi

# ⚠️ اینجا فرمان ارسال به بله را بگذار
# bash send_to_bale.sh "$report_text"

echo "$reporthash" > "$hashfile"
echo "$now | گزارش با محتوای جدید ارسال شد: $latest" >> "$LOG"
