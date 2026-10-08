# OptimusAI V41 — Bridge / Runtime / Evidence Runbook

## 1. معماری نهایی
GitHub repository `abolfazlabasi740-bot/options-report` لایه repository/control/evidence است.
Termux runtime در `~/OptimusAI_V41_LIVE` اجرای واقعی را انجام می‌دهد.
Bridge بین این دو قرار دارد.

مسیر اجرا:
GitHub `bridge-commands` → Termux Bridge → `~/OptimusAI_V41_LIVE` → اجرای Python/Git → Receipt → GitHub `bridge-results`

## 2. اجزای نرم‌افزاری
- Bridge: `scripts/termux_command_bridge_agent.py`
- Runner گزارش: `scripts/run_corrected_last_minute_report.py`
- Runtime پروژه: `~/OptimusAI_V41_LIVE`
- Queue branch: `bridge-commands`
- Result branch: `bridge-results`
- Bridge work area: `~/.termux_command_bridge`
- Queue clone: `~/.termux_command_bridge/queue`
- Lock: `~/.termux_command_bridge/bridge_agent.lock`
- Log: `~/.termux_command_bridge/bridge_agent.log`

## 3. نرم‌افزار/دسترسی‌های لازم
Bridge برای کارکرد خود به Python، Git و GitHub CLI (`gh`) و احراز هویت GitHub نیاز دارد.
Bridge در زمان startup `gh auth status` و `gh auth setup-git` را کنترل می‌کند.
فرمان‌های مجاز: python/python3/git/bash/sh/printf/pwd/ls.
فرمان‌های مخرب یا پرریسک مانند rm، sudo، ssh، scp، curl، wget، chmod و chown مسدودند.

## 4. سخت‌افزار/محیط لازم
- یک دستگاه Android دارای Termux
- دسترسی شبکه به GitHub
- اجرای Bridge daemon در Termux
- فضای کاری پروژه در `~/OptimusAI_V41_LIVE`
سخت‌افزار اضافه یا سرور جدا برای این معماری لازم نیست؛ Termux همان execution host است.

## 5. چرخه Queue و Receipt
هر فرمان یک JSON با `command_id` و `argv` در `bridge-commands` ایجاد می‌کند.
Bridge حداکثر هر 5 ثانیه Queue را poll می‌کند.
برای هر فرمان timeout پیش‌فرض 120 ثانیه است.
پس از اجرا، Receipt شامل status، exit_code، زمان شروع/پایان، cwd، argv، stdout، stderr، project_head و result_sha256 ساخته می‌شود.
Receipt ابتدا در `bridge-results` منتشر و با SHA بررسی می‌شود؛ فقط پس از آن Queue item acknowledge/delete می‌شود.

## 6. نکته مهم درباره Receipt
404 در چند ثانیه اول به معنی شکست اجرای فرمان نیست.
اجرای گزارش امروز حدود 44 ثانیه طول کشید و Receipt بعداً در `bridge-results` ظاهر شد.
بنابراین فرآیند استاندارد:
Queue → انتظار برای Receipt تا سقف 120 ثانیه → دریافت Receipt → بررسی SUCCESS/exit_code=0 → استفاده از stdout.
اجرای مجدد قبل از پایان پنجره انتظار ممنوع است، مگر اینکه Receipt نهایی TIMEOUT/FAILED/ERROR باشد.

## 7. شواهد اجرای موفق 2026-10-08
Command ID: `zz_run_report_20261008_24`
Status: SUCCESS
Exit code: 0
Execution: حدود 44 ثانیه
Snapshot: 1405/07/16 11:15:57
Refresh: SUCCESS
Valid option candidates: 186
Displayed contracts: 15
Project head: `cba8092ad0f49346508369974862c4fedf5b344c`
Result SHA256: `fa87eaf893cba6c80915513de6714fb4386f2f89a6fb5f54b506c3a3a8455eae`

## 8. Restore و رفع وابستگی‌ها
در اجرای امروز چند dependency قدیمی از Git history بازیابی شد:
- `last_minute_profit_engine.py` از commit `3837a4d5a215abf4defcccf66b28daf99bb99e3b`
- `underlying_trend_engine.py` از commit `377d323027a2a40c233adf844e50a32d7cf18a98`
- `bull_call_spread_engine.py` از همان commit `377d323...`
هر فایل پس از restore با `python -m py_compile` کنترل شد.

## 9. گزارش و منبع داده
گزارش `فرصت لحظه آخری آپشن` از TSETMC به‌عنوان Single Source of Truth استفاده می‌کند.
ابتدا سهم‌های پایه قوی کشف می‌شوند، سپس زنجیره آپشن همان سهم ارزیابی می‌شود.
خروجی نهایی حداکثر 3 قرارداد از هر سهم پایه دارد و مجبور به پر کردن سهمیه نیست.
گزارش امروز 15 قرارداد از 186 کاندیدای معتبر تولید کرد.

## 10. کنترل‌های عملیاتی
- بدون Receipt واقعی، اجرای موفق اعلام نشود.
- Receipt باید SUCCESS و exit_code=0 باشد.
- stderr در صورت FAILED/TIMEOUT/ERROR ملاک عیب‌یابی است.
- project_head و result_sha256 برای audit نگهداری شوند.
- قبل از اجرای مجدد، bridge-results برای همان command_id بررسی شود تا duplicate execution ایجاد نشود.
- خارج از ساعات بازار TSETMC، آخرین snapshot معتبر استفاده شود؛ refresh ساختگی یا داده حدسی مجاز نیست.

## 11. نتیجه
این سند مرجع واحد معماری، مسیر داده، مسیر اجرای گزارش، اجزای نرم‌افزاری/سخت‌افزاری، مکان Receipt و رویه رفع خطاست تا در اجرای بعدی دوباره مسیرها و منطق Receipt از ابتدا بررسی نشود.
