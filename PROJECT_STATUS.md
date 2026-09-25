# OptimusAI V4.1.1 — Project Status

## Active runtime

مسیر فعال گزارش‌دهی TSETMC-only است.

- report_engine.py از Workbook استفاده نمی‌کند.
- tsetmc_first_source.py منبع Canonical است.
- tsetmc_adapter.py مرز Evidence منبع TSETMC است.
- Bale فقط Distribution Layer است.

## Source of Truth

TSETMC Option Market-Watch منبع فعال Universe و Identity است.

OptionSchool24 و reconciliationهای قدیمی در Runtime فعال مصرف نمی‌شوند و برای تکمیل فیلدهای مفقود TSETMC نیز استفاده نمی‌شوند.

## Identity rule

شناسه قرارداد اختیار و شناسه دارایی پایه باید صریحاً از TSETMC دریافت شوند.

Symbol-prefix inference مجاز نیست.

## Reporting continuity

گزارش‌دهی خارج از ساعت بازار نیز امکان‌پذیر است:

- LIVE_TSETMC_REFRESH یعنی Refresh معتبر TSETMC در اجرای جاری دریافت شده است.
- LAST_KNOWN_TSETMC_SNAPSHOT یعنی Refresh جاری قابل استفاده نبوده و آخرین Snapshot معتبر TSETMC استفاده شده است.
- مسیر Cached هرگز حرکت زنده بازار را ادعا نمی‌کند.
- live_movement_claim باید NOT_CLAIMED باشد.
- report و audit باید data_mode، live_refresh_status، fallback_reason، basis_source_market_timestamp و Snapshot hash را حفظ کنند.

این مسیر هیچ منبع ثانویه‌ای برای تکمیل داده اضافه نمی‌کند.

## BestLimits evidence gate

Runner و Validator برای Capture واقعی، حفظ payload خام، hash، زمان و شناسه صریح در Repository وجود دارند.

اما وجود Runner یا تست‌های آن به‌تنهایی Live Evidence ایجاد نمی‌کند.

تا زمانی که Capture واقعی و semantic mapping با Evidence مستقل تأیید و Adapter Contract freeze نشده باشد، BestLimits-derived scoring input مسدود است.

## Scoring state

Six-Block scoring و production ranking تا بسته‌شدن Evidence Gateهای لازم فعال نیستند.

فیلد فاقد Evidence مستقیم باید «داده موجود نیست» باقی بماند.

## Runtime verification

Repository inspection جایگزین Runtime Evidence نیست.

Termux، Source freshness و Bale delivery باید روی Commit مستقر و فعال مجدداً تأیید شوند.

## Immediate controlled path

- Capture واقعی TSETMC و BestLimits؛
- حفظ raw payload و hash؛
- تأیید semantic mapping؛
- freeze کردن Adapter Contract؛
- تأیید freshness؛
- تأیید contract specification و open-interest evidence؛
- تکمیل conventions موردنیاز محاسباتی فقط بر اساس Source Evidence؛
- سپس بازبینی مجدد Scoring، Ranking، Audit و Bale روی Dataset Canonical TSETMC.

No Buy/Sell signal is emitted during this evidence-only phase.
