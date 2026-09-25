# OptimusAI V4.1 — Gate 7 Execution Control

## Purpose

این سند مرز کنترل‌شده انتشار را تعریف می‌کند. هیچ تغییر عددی، وزن‌دهی، Threshold یا Signal Policy صرفاً با این سند ایجاد نمی‌شود.

## Active production boundary

Source of Truth فعال: TSETMC.

OptionSchool24 در Runtime فعال نیست و فقط به‌عنوان آرشیو/شاهد تاریخی نگهداری می‌شود.

تا بسته‌شدن Evidence Gateهای لازم:
- Six-Block scoring فعال نمی‌شود؛
- Ranking و Top-N تولیدی فعال نمی‌شود؛
- Bale فقط Distribution Layer است؛
- Opportunity Intelligence در حالت Shadow/Controlled باقی می‌ماند؛
- TSETMC identity فقط با شناسه صریح منبع پذیرفته می‌شود؛
- symbol-prefix inference ممنوع است؛
- synthetic market, IV, rate, dividend, parity یا identity ممنوع است؛
- Buy/Sell signal تولیدی فعال نمی‌شود.

## Evidence classes

Evidence باید بین این طبقات تفکیک شود:

- Repository / code evidence
- CI / regression evidence
- Real-source evidence
- Deployed-runtime evidence
- Distribution evidence
- Economic / historical validation evidence

هیچ طبقه‌ای جای طبقه دیگر را نمی‌گیرد.

## Controlled work sequence

### Parameter provenance

منشأ پارامترهای فعال باید مستند و قابل بازتولید باشد. مقدار جایگزین حدسی ممنوع است.

### Historical sensitivity

مدل منجمد باید روی داده تاریخی واقعی ارزیابی شود، بدون تغییر پارامترهای تولیدی. فایل منبع، hash و نتیجه اجرای تکرارشونده باید قابل ردیابی باشد.

### Market freshness

زمان بازار باید از زمان دریافت جدا نگهداری شود. وضعیت stale یا unknown باید صریح باشد.

### Exact TSETMC identity

شناسه قرارداد اختیار و شناسه دارایی پایه باید مستقیماً از پاسخ منبع استخراج شوند. Symbol inference مجاز نیست.

### BestLimits

Capture واقعی، payload کامل، endpoint، زمان‌های دریافت، hash و شواهد مستقل semantic باید قبل از freeze شدن Adapter Contract ثبت شوند.

### Economic validation

Opportunity Intelligence باید با نمونه‌های واقعی/تاریخی ارزیابی شود. اجرای فنی به‌تنهایی مجوز Promotion نیست.

### Final release review

پس از تکمیل Evidenceهای لازم، Audit باید linkage بین Source، Snapshot، Report، Runtime و Distribution را بررسی کند و سپس مرز Production تعیین شود.

## Current state

Regression و کنترل‌های Repository در مسیر کنترل‌شده قرار دارند.

TSETMC-only architecture در کد فعال است.

Live TSETMC evidence هنوز باید روی Runtime واقعی تأیید شود.

BestLimits live evidence و semantic mapping هنوز Production Freeze نشده‌اند.

Economic validation هنوز باز است.

Current Termux → Bale evidence باید روی همان TSETMC-only Commit مجدداً تأیید شود.

## Release rule

Gate closure با Evidence انجام می‌شود، نه با وجود فایل یا موفقیت یک اجرای قدیمی.

هیچ Component مجاز به Self-Promotion از Shadow/Controlled به Production نیست.
