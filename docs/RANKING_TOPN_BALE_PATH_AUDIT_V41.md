# Ranking → Top-N → Bale Path Audit — V4.1.1

## Scope

این ممیزی مسیر خروجی را از `FinalScore` تا رتبه، Top-N و ارسال Bale بررسی می‌کند.

هیچ تغییر در Scoring، وزن‌ها، Gateها یا گزارش انجام نشده است.

## نتیجه

### 1. منبع رتبه‌بندی — PASS

در `report_engine.py`، پس از اعمال Production Eligibility و در صورت وجود Symbol Filter، داده‌ها با ترتیب زیر مرتب می‌شوند:

- `FinalScore` نزولی
- `ارزش` نزولی
- `حجم` نزولی
- `نماد` صعودی

بنابراین معیار اصلی رتبه‌بندی فقط `FinalScore` است و سه فیلد بعدی فقط Tie-breaker هستند.

### 2. Symbol Filter — PASS

فیلتر نماد قبل از Sort و قبل از Top-N اجرا می‌شود.

نتیجه: درخواست یک نماد، از کل قراردادهای واجد شرایط همان نماد رتبه‌بندی می‌شود و Top-N از همان مجموعه انتخاب می‌گردد.

این رفتار با Regression Test موجود برای Symbol Filter نیز کنترل شده است.

### 3. Top-N — PASS

پس از Sort، دستور `head(limit)` اعمال می‌شود.

- Global: مقدار گزارش‌ساز 15
- Symbol: مقدار گزارش‌ساز 5

مقادیر بالا از کد فعال مشاهده شده‌اند؛ این سند آن‌ها را تغییر نمی‌دهد.

### 4. Shadow Engines — PASS / Non-Blocking

Opportunity Shadow، Chain، Relative Value، Explanation، Red Team و Replay قبل/در جریان تولید گزارش اجرا می‌شوند، اما طبق قرارداد معماری:

- FinalScore را تغییر نمی‌دهند.
- Sort را تغییر نمی‌دهند.
- Top-N را تغییر نمی‌دهند.
- متن گزارش تولیدی را به‌عنوان موتور دوم بازنویسی نمی‌کنند.

بنابراین مسیر Production Ranking از مسیر Shadow جدا باقی مانده است.

### 5. Bale Listener — PASS

مسیر فعال Listener:

`Bale command`
→ دریافت Workbook جدید OptionSchool24
→ `build_report()`
→ همان Scoring/Ranking Path
→ `save_report()`
→ ارسال متن همان Report به Bale

برای Global، دستورات `گزارش`، `همه` و `کل` به یک مسیر 15-تایی متصل هستند.

برای درخواست نماد، همان Report Engine با Symbol Filter و Top-5 استفاده می‌شود.

### 6. Audit قبل از ارسال — PASS

`save_report()` ابتدا Audit را می‌سازد و `audit_integrity.status=PASS` را الزام می‌کند.

در مسیر مستقل Runtime Verification نیز پیش از ارسال Bale موارد زیر کنترل می‌شوند:

- هویت و SHA-256 منبع
- SHA-256 گزارش
- تطبیق SHA گزارش با Audit
- وجود فایل منبع
- تطبیق SHA فایل منبع
- Audit Integrity = PASS
- وجود Receipt واقعی Bale

بنابراین مسیر Runtime Verification برای اثبات «گزارش تولیدشده همان گزارشی است که ارسال شده» طراحی شده است.

## نکته مهم

مسیر Ranking فعلی از نظر معماری، یک مسیر واحد دارد:

`FinalScore → Sort → Top-N → Report → Bale`

در ممیزی فعلی، مسیر موازی دیگری که بتواند Ranking یا Top-N را تغییر دهد مشاهده نشد.

## وضعیت Gateها

- Ranking integrity: VERIFIED BY CODE + REGRESSION
- Top-N integrity: VERIFIED BY CODE + REGRESSION
- Bale path integrity: VERIFIED BY CODE + REGRESSION
- Physical Bale runtime: طبق Project Status با Evidence واقعی بسته شده است.
- TSETMC exact option identity: هنوز pending.
- Scoring parameter provenance: هنوز OPEN.
- Economic validation of opportunity quality: جداگانه باز است.

## Evidence

Files audited:

- `scoring_engine.py`
- `report_engine.py`
- `bale_listener.py`
- `bale_runtime_verification.py`
- `tests/test_regressions.py`

Observed source SHAs at audit time:

- scoring_engine.py: `9874909b018d762ef3ad529cba5ae0d2c2421e8f`
- report_engine.py: `e54f74880109089d4045ce4eafad137c3a6b0559`
- bale_listener.py: `eb3edb1e7264d98e099aaf5d5ebc4b08f0f788c2`
- bale_runtime_verification.py: `a82fe10547ed61edaa9338129f57675cb0da505b`
- tests/test_regressions.py: `bd06f9ad73169b1c9697fbfa8d49090e41eb7ab8`

## تصمیم

مسیر Ranking/Top-N/Bale فعلاً نیاز به تغییر کدی ندارد.

تمرکز بعدی باید روی مواردی باشد که واقعاً هنوز مانع Cutover کامل هستند:

1. Scoring Parameter Provenance
2. Exact TSETMC Option Identity
3. Source Freshness / Market Timestamp
4. Economic Validation مستقل از Technical Integrity
