# Change Record — 2026-09-15 — Standalone Underlying Intelligence

## تصمیم
لایه تحلیل سهم پایه از V4/V4.1 جدا نگه داشته می‌شود تا ابتدا از نظر داده، منطق، تاریخچه، Backtest و Audit بالغ شود.

## تغییر
یک ماژول مستقل با مسیر `underlying_intelligence/` به مخزن اضافه شد.

## قابلیت‌های فعلی
- دریافت داده از TSETMC
- قیمت، حجم، ارزش و معاملات
- جریان حقیقی/حقوقی و خالص حجم
- قدرت خریدار/فروشنده حقیقی
- Best Bid / Best Ask و Spread
- SMA5/SMA20/SMA60
- RSI14
- بازده 5 و 20 روزه
- نوسان 20 روزه و موقعیت در دامنه 20 روزه
- تشخیص Eventهای پایه
- Data Quality / Confidence
- Research Score آزمایشی و شفاف
- ثبت Snapshot و Event در SQLite
- گزارش مستقل فارسی

## مرز با V4
این ماژول هیچ تغییری در وزن‌ها، Scoring یا تصمیم‌گیری V4/V4.1 ایجاد نمی‌کند و فعلاً به آن متصل نیست.

## مراحل بعدی قبل از Integration
1. Data QA
2. Multi-day flow
3. Price/Volume divergence
4. Regime detection
5. Cross-sectional ranking
6. Historical backtest
7. Calibration
8. Audit و validation
9. تعریف Interface رسمی برای V4

## وضعیت
`STANDALONE_RESEARCH / NOT_CONNECTED_TO_V4`
