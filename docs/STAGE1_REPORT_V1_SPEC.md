# OptimusAI Stage 1 — Operational Report V1

## هدف

مرحله اول پروژه باید قبل از توسعه‌های پیشرفته، یک مسیر گزارش‌دهی پایدار، قابل ممیزی و TSETMC-only ایجاد کند.

## اجزای Stage 1

1. TSETMC Option Market-Watch به‌عنوان منبع حقیقت Universe و Identity.
2. Economic Scoring شش‌بلوک با وزن‌های مصوب:
   - LIQUIDITY 20
   - VALUATION 25
   - PAYOFF 18
   - TIME 15
   - GREEKS 12
   - MARKET 10
3. Missing Evidence = UNAVAILABLE_NOT_ZERO.
4. گزارش می‌تواند خارج از ساعت بازار از آخرین Snapshot معتبر استفاده کند و آن را به‌عنوان حرکت زنده معرفی نمی‌کند.
5. Ranking روی Universe کامل انجام می‌شود و محدودیت نمایش فقط بعد از Ranking اعمال می‌شود.
6. تحلیل پایه در Stage 1 با قابلیت‌های موجود TSETMC شامل SMA5/10/20/50، RSI14، MACD12/26، بازده 5/20 جلسه‌ای، نسبت حجم/ارزش، وضعیت روند، عمق سفارش و قدرت خریدار/فروشنده حقیقی انجام می‌شود.
7. underlying_intelligence_engine.py یک Bias توصیفی تولید می‌کند:
   BULLISH / BEARISH / NEUTRAL / CONFLICTED
8. BUY/SELL در Stage 1 تولید نمی‌شود.
9. SuperTrend، Bollinger، Ichimoku، الگوهای پیشرفته Price Action و Adaptive Learning به Stageهای بعدی منتقل شده‌اند.
10. Outcome Tracking و Walk-Forward Validation خارج از مرز Stage 1 و برای توسعه بعدی باقی می‌مانند.

## Cache Integrity

Snapshot سراسری نباید با گزارش فیلترشده یک نماد یا یک پایه overwrite شود.

گزارش ابتدا Universe کامل TSETMC را دریافت می‌کند و سپس فیلتر نمایش را اعمال می‌کند.

Snapshot بسته بازار فقط زمانی معتبر است که:
- حداقل 15 Instrument مجزا داشته باشد؛
- Identity معتبر TSETMC داشته باشد؛
- حداقل یک timestamp صریح بازار TSETMC داشته باشد.

در غیر این صورت، سیستم Fail-Closed است و فقط به آخرین Snapshot معتبر قبلی برمی‌گردد.

## Stage 1 خروجی

گزارش شامل:
- وضعیت بازار و Data Mode
- وضعیت Ranking
- قراردادهای برتر موجود بر اساس Economic Score
- تحلیل پایه‌های مرتبط
- Bias و Confidence توصیفی
- نقدشوندگی، Payoff، زمان و Market evidence
- Audit SHA256

این خروجی هنوز سیگنال خرید/فروش نیست.

## مرحله بعد

پس از دریافت و بررسی گزارش‌های Stage 1، توسعه به‌صورت تدریجی انجام می‌شود:
- SuperTrend
- Bollinger
- Ichimoku/Kumo
- ATR/ADX و سایر شاخص‌های منتخب
- Candlestick/Price Action پیشرفته
- Event/Sequence detection
- Directional CALL/PUT Gate
- Outcome Learning و Adaptive Weighting

هر توسعه باید با شواهد TSETMC، نسخه‌بندی و Walk-Forward Validation وارد Production شود.
