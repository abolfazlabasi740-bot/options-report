# Underlying Intelligence — مستقل از V4

هدف این لایه ساخت و اعتبارسنجی موتور تحلیل سهم پایه است. این پروژه عمداً هیچ import یا dependency از V4/V4.1 ندارد.

## اصول حاکم
- هیچ داده‌ای ساخته نمی‌شود؛ مقدار ناموجود `داده موجود نیست` است.
- هر اجرا یک Snapshot در SQLite ثبت می‌کند.
- Research Score فقط آزمایشی است و توصیه خرید/فروش/نگهداری نیست.
- تا قبل از Backtest و Validation، خروجی وارد V4 نمی‌شود.
- API و منطق جمع‌آوری داده از TSETMC در یک لایه مستقل نگهداری می‌شود.
- این لایه فعلاً برای پژوهش و بلوغ مدل است، نه Production Scoring در V4.

## اجرا در Termux
`python3 -m pip install -U requests`

`python3 run_underlying.py وبملت`

`python3 run_underlying.py وبملت ذوب خودرو`

`python3 run_underlying.py --file symbols.txt`

## شواهد
- `data/underlying.sqlite`: Snapshotها و Eventها
- `reports/`: گزارش هر اجرا

## معماری بلوغ
1. Data QA
2. Snapshot history
3. multi-day flow
4. divergence
5. regime detection
6. cross-sectional ranking
7. backtest
8. calibration
9. audit
10. approved interface برای V4

## وضعیت
`STANDALONE_RESEARCH / NOT_CONNECTED_TO_V4`
