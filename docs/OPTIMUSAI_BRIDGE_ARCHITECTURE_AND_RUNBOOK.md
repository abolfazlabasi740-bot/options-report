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
Bridge به Python، Git و GitHub CLI (`gh`) و احراز هویت GitHub نیاز دارد.
Bridge در startup `gh auth status` و `gh auth setup-git` را کنترل می‌کند.
فرمان‌های مجاز: python/python3/git/bash/sh/printf/pwd/ls.
فرمان‌های پرریسک مانند rm، sudo، ssh، scp، curl، wget، chmod و chown مسدودند.

## 4. سخت‌افزار/محیط لازم
- Android دارای Termux
- دسترسی شبکه به GitHub
- Bridge daemon فعال در Termux
- پروژه در `~/OptimusAI_V41_LIVE`
سخت‌افزار یا سرور جدا لازم نیست؛ Termux execution host است.

## 5. چرخه Queue و Receipt
هر فرمان با `command_id` و `argv` در `bridge-commands` ایجاد می‌شود.
Bridge حداکثر هر 5 ثانیه Queue را poll می‌کند.
timeout پیش‌فرض هر فرمان 120 ثانیه است.
Receipt شامل status، exit_code، زمان شروع/پایان، cwd، argv، stdout، stderr، project_head و result_sha256 است.
Receipt ابتدا در `bridge-results` منتشر و با SHA تأیید می‌شود؛ سپس Queue item acknowledge/delete می‌شود.

## 6. قانون Receipt
404 در چند ثانیه اول به معنی شکست نیست.
اجرای گزارش 2026-10-08 حدود 44 ثانیه طول کشید و Receipt بعداً ظاهر شد.
رویه استاندارد:
Queue → انتظار تا سقف 120 ثانیه → دریافت Receipt → SUCCESS و exit_code=0 → استفاده از stdout.
قبل از پایان این پنجره، اجرای مجدد همان فرمان انجام نشود؛ مگر Receipt نهایی FAILED/TIMEOUT/ERROR باشد.

## 7. حذف کامل کپی‌پیست دستی
هدف: کاربر برای اجرای عادی دستورات و گزارش‌ها در Termux هیچ copy/paste دستی انجام ندهد.

مسیر استاندارد:
ChatGPT درخواست را به JSON فرمان تبدیل می‌کند → فرمان در `bridge-commands` ثبت می‌شود → Bridge daemon خودکار Queue را poll می‌کند → فرمان در `~/OptimusAI_V41_LIVE` اجرا می‌شود → Receipt در `bridge-results` ثبت می‌شود → ChatGPT Receipt را می‌خواند و نتیجه را ارائه می‌کند.

بنابراین:
- کپی‌کردن فرمان ChatGPT و paste دستی در Termux برای اجرای عادی ممنوع/غیرضروری است.
- تغییر دستی خط‌به‌خط اسکریپت‌ها انجام نمی‌شود.
- تغییرات کد باید به‌صورت کامل در repository اعمال شوند.
- سپس sync/restore، compile/test و اجرای واقعی از طریق Bridge انجام می‌شود.
- فقط در مواردی که Android/Termux نیاز به اقدام محلی یا احراز هویت داشته باشد، دخالت کاربر لازم است.
- 404 موقت Receipt نباید باعث اجرای تکراری شود.

## 8. تغییر و استقرار کد
1. تغییر کامل در GitHub ایجاد می‌شود.
2. commit ثبت می‌شود.
3. Bridge تغییر را به runtime می‌رساند یا فرمان restore/sync اجرا می‌کند.
4. `py_compile` و تست لازم اجرا می‌شود.
5. Receipt ثبت می‌شود.
6. فقط پس از SUCCESS نتیجه نهایی اعلام می‌شود.

## 9. شواهد اجرای موفق 2026-10-08
Command ID: `zz_run_report_20261008_24`
Status: SUCCESS
Exit code: 0
Execution: حدود 44 ثانیه
Snapshot: 1405/07/16 11:15:57
Refresh: SUCCESS
Valid option candidates: 186
Displayed contracts: 15
Project head: `cba8092ad0f49346508369974862c4fedf5b344c`

## 10. Restore وابستگی‌های امروز
- `last_minute_profit_engine.py` از commit `3837a4d5a215abf4defcccf66b28daf99bb99e3b`
- `underlying_trend_engine.py` از commit `377d323027a2a40c233adf844e50a32d7cf18a98`
- `bull_call_spread_engine.py` از همان commit `377d323...`
هر فایل پس از restore با `python -m py_compile` کنترل شد.

## 11. گزارش و منبع داده
گزارش `فرصت لحظه آخری آپشن` از TSETMC به‌عنوان Single Source of Truth استفاده می‌کند.
ابتدا سهم‌های پایه بررسی می‌شوند و سپس زنجیره آپشن همان سهم ارزیابی می‌شود.
خروجی حداکثر 3 قرارداد از هر سهم پایه دارد و مجبور به پر کردن سهمیه نیست.
گزارش موفق امروز 15 قرارداد از 186 کاندیدای معتبر تولید کرد.

## 12. کنترل‌های عملیاتی
- بدون Receipt واقعی، موفقیت اعلام نشود.
- Receipt باید SUCCESS و exit_code=0 باشد.
- stderr در FAILED/TIMEOUT/ERROR ملاک عیب‌یابی است.
- project_head و result_sha256 برای audit نگهداری شوند.
- قبل از اجرای مجدد، bridge-results برای همان command_id بررسی شود.
- خارج از ساعات بازار TSETMC، آخرین snapshot معتبر استفاده شود؛ داده حدسی مجاز نیست.

## 13. نتیجه
این سند مرجع واحد معماری، مسیر داده، مسیر اجرای گزارش، اجزای نرم‌افزاری/سخت‌افزاری، مسیر Receipt و روش حذف copy/paste دستی است.
