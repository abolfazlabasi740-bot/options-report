# Scoring Path Audit — V4.1.1

## هدف

این ممیزی مسیر واقعی امتیازدهی از BaseScore تا FinalScore را بررسی می‌کند تا مشخص شود آیا یک عامل اقتصادی بیش از یک‌بار وارد رتبه‌بندی شده، آیا یک Gate همزمان نقش Score دارد، و آیا پارامترهای فعال منشأ مستند دارند یا خیر.

این ممیزی هیچ وزن، آستانه یا فرمول فعال را تغییر نمی‌دهد.

## مسیر فعلی

`score_dataframe()`
→ eligibility gates
→ `add_analytics()`
→ `score_v3()`
→ Six-Block BaseScore
→ `score_v4_overlay()`
→ FinalScore

### Six-Block

- Liquidity = 20
- Valuation = 25
- Payoff = 18
- Time = 15
- Greeks = 12
- Market = 10

## یافته‌های ممیزی

### 1. Spread دو بار اثر می‌گذارد — CONFIRMED

Spread در Liquidity با وزن 3 وارد BaseScore می‌شود:

`Score_Spread = robust_percentile(Spread_Percentage, lower-is-better)`

همان `Spread_Percentage` دوباره در Overlay برای `ExecutionPenalty` استفاده می‌شود.

نتیجه: یک ویژگی واحد، هم در BaseScore و هم به‌صورت ضریب کاهنده FinalScore اثر دارد.

این لزوماً خطای طراحی نیست؛ می‌تواند به‌عنوان «امتیاز فرصت + جریمه قابلیت اجرا» عمدی باشد. اما تا زمان تأیید پروتکل، باید به‌عنوان **Double Exposure / نیازمند توجیه مستقل** ثبت شود.

### 2. Time-to-expiry دو بار اثر می‌گذارد — CONFIRMED

روزهای معاملاتی و روزهای تقویمی در Block Time وارد BaseScore می‌شوند.

همان مفهوم RemainingDays نیز در Overlay با DecayPenalty وارد FinalScore می‌شود.

همچنین RemainingDays > 0 یک eligibility gate است.

این سه نقش باید از هم تفکیک شوند:

- Gate: حذف قرارداد منقضی/غیرقابل‌استفاده
- BaseScore: ترجیح نسبی زمانی در مقطع مقایسه
- Overlay: کنترل ریسک نزدیک‌شدن به سررسید

ساختار قابل دفاع است، ولی پارامترهای Decay باید منبع/پروتکل مستقل داشته باشند.

### 3. Leverage هم Gate است و هم Score — CONFIRMED

`MIN_LEVERAGE` برای eligibility استفاده می‌شود و Leverage همچنین در Payoff با وزن 5 امتیاز می‌گیرد.

این الزاماً Double Counting عددی نیست، زیرا یکی Gate و دیگری رتبه‌بندی نسبی است؛ اما یک قرارداد ابتدا باید از حداقل اهرم عبور کند و سپس از اهرم بالاتر امتیاز بگیرد.

منشأ و تأیید `MIN_LEVERAGE` باید مانند سایر پارامترهای مؤثر بر FinalScore مستند شود.

### 4. Confidence پوشش کامل همه عوامل را ندارد — CONFIRMED

`DataConfidence` فقط مجموعه محدودی از فیلدهای Critical، IV، HV و Breakeven را در کاهش امتیاز لحاظ می‌کند.

در مقابل، بسیاری از عوامل دیگر مانند Depth، Spread، Time Value، Greeks، Theta و برخی عوامل بازار می‌توانند missing باشند و وزن آن‌ها داخل همان Block بازتوزیع می‌شود.

بنابراین `DataConfidence` در وضعیت فعلی «درجه کامل‌بودن کل داده‌های امتیازدهی» نیست؛ بلکه یک شاخص محدود از completeness است.

تا زمان تعریف رسمی دامنه آن، نباید این ستون به‌عنوان Full Data Quality Score توصیف شود.

### 5. جهت برخی عوامل نیازمند تأیید سیاست سرمایه‌گذاری است — OPEN

کد فعلی برای برخی عوامل جهت مکانیکی تعیین کرده است، از جمله:

- IV: higher-is-better
- IV/HV: lower-is-better
- Theta magnitude: lower-is-better
- Greeks magnitude: higher-is-better
- Last-vs-Close absolute deviation: lower-is-better
- Intraday range: lower-is-better

این‌ها «واقعیت داده» نیستند؛ انتخاب‌های سیاست امتیازدهی هستند.

به‌خصوص Greeks به‌صورت magnitude-only و بدون جهت قرارداد استفاده می‌شوند و Contract Type هنوز صریح نیست. بنابراین این بخش باید در پروتکل اقتصادی پروژه تأیید شود و فعلاً نباید به‌عنوان منطق اقتصادی اثبات‌شده معرفی شود.

### 6. BaseScore و FinalScore یک معنی ندارند — CONFIRMED

BaseScore امتیاز Six-Block است.

FinalScore پس از BaseScore با ExecutionPenalty، DecayPenalty و DataConfidence تعدیل می‌شود.

بنابراین مقایسه تاریخی یا گزارش‌گیری باید مشخص کند کدام ستون مبناست. رتبه تولیدی باید فقط از FinalScore استفاده کند تا دو مسیر موازی ایجاد نشود.

## پارامترهای باز

پارامترهای عددی Overlay و حداقل اهرم فعلی، تا زمانی که منبع/تصمیم مصوب و regression evidence برای آن‌ها ثبت نشود، «Observed Active Parameters» هستند، نه thresholds اقتصادی تأییدشده.

موارد باز:

1. Execution penalty constants
2. Decay penalty constants
3. Confidence clipping
4. Leverage normalization cap
5. MIN_LEVERAGE
6. جهت اقتصادی عوامل فوق

## تصمیم ممیزی

- هیچ تغییر عددی در Scoring Engine انجام نشد.
- Spread double exposure ثبت شد.
- Time/Decay double exposure ثبت شد.
- Gate/Score leverage interaction ثبت شد.
- دامنه واقعی DataConfidence ثبت شد.
- جهت عوامل بدون Contract Type به‌عنوان موضوع validation ثبت شد.
- Gate 7 همچنان به‌دلیل provenance و validation اقتصادی بسته نمی‌شود.

## شواهد کد

این ممیزی بر نسخه فعلی `scoring_engine.py` در شاخه اصلی مخزن انجام شده و SHA فایل در زمان ممیزی:

`9874909b018d762ef3ad529cba5ae0d2c2421e8f`

است.

این سند صرفاً ممیزی طراحی فعلی است و هیچ ادعایی درباره اعتبار اقتصادی پارامترها ندارد.
