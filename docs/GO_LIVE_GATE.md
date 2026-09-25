# GO-LIVE GATE — OptimusAI V4.1

## Purpose

این سند مرز عبور پروژه از توسعه و Evidence Mode به بهره‌برداری عملیاتی را مشخص می‌کند. وجود کد یا فایل در GitHub به‌تنهایی Evidence اجرایی محسوب نمی‌شود.

## Active architecture

مسیر فعال گزارش‌دهی:

TSETMC Raw
→ Exact Identity
→ Canonical TSETMC
→ Intelligence / Feature Evidence
→ Scoring
→ Ranking
→ Report
→ Audit
→ Bale

OptionSchool24 در مسیر فعال Runtime قرار ندارد و صرفاً آرشیو/شاهد تاریخی است.

## Current source boundary

TSETMC تنها Source of Truth بازار و هویت قرارداد است.

الزام‌ها:
- شناسه صریح قرارداد اختیار از خود منبع؛
- شناسه صریح دارایی پایه از خود منبع؛
- endpoint و زمان دریافت؛
- payload و hash قابل ردیابی؛
- عدم استفاده از inference بر اساس پیشوند نماد؛
- برای داده فاقد Evidence مستقیم: «داده موجود نیست».

## Market-hours continuity

در صورت دریافت Refresh معتبر از TSETMC، حالت داده LIVE_TSETMC_REFRESH است.

در صورت عدم دسترسی به Refresh و وجود آخرین Snapshot معتبر TSETMC، حالت LAST_KNOWN_TSETMC_SNAPSHOT است.

Snapshot قبلی هرگز به‌عنوان حرکت زنده بازار معرفی نمی‌شود و live_movement_claim باید NOT_CLAIMED باقی بماند.

## Evidence boundary

وجود خروجی CI، وجود کد Adapter یا موفقیت یک اجرای قبلی، به‌تنهایی Live Evidence فعلی ایجاد نمی‌کند.

Live TSETMC، BestLimits، semantic mapping، freshness، اقتصادی‌بودن Opportunity Intelligence و استقرار فعلی Termux باید با Evidence مستقل و قابل ردیابی اثبات شوند.

## Bale

Bale فقط Distribution Layer است و تحلیل جدیدی انجام نمی‌دهد.

گزارش ارسالی باید همان latest_report.txt مورد تأیید Audit باشد و hash گزارش، منبع و Evidence مقصد قابل تطبیق باشند.

Evidence قدیمی Termux/Bale تا زمانی که روی Commit و Runtime فعلی مجدداً تأیید نشده، صرفاً Historical Evidence محسوب می‌شود.

## Scoring and Ranking

تا بسته‌شدن Evidence Gate مربوط به فیلدهای لازم TSETMC، Scoring و Ranking تولیدی فعال نمی‌شوند.

هیچ Buy/Sell signal در Evidence Mode تولید نمی‌شود.

## Current blockers

- Live TSETMC evidence روی Runtime مستقر؛
- BestLimits evidence package واقعی و time-locked؛
- semantic mapping و Adapter Contract freeze؛
- market-data freshness validation؛
- economic validation of Opportunity Intelligence؛
- تأیید مجدد Termux → Bale روی همان Commit فعال.

## Release rule

هیچ Engine یا Layer مجاز نیست صرفاً بر اساس وجود کد، از Shadow/Controlled به Production ارتقا پیدا کند.

Gate closure فقط با Evidence قابل بازتولید انجام می‌شود.
