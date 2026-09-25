# Economic Scoring Audit — OptimusAI V4.1.1

## هدف

این ممیزی فقط وضعیت واقعی موتور امتیازدهی فعال TSETMC را ثبت می‌کند و مواردی را که هنوز از نظر اقتصادی نیازمند اعتبارسنجی هستند از منطق اجرایی تفکیک می‌کند. این سند هیچ وزن، آستانه یا فرمول Production را تغییر نمی‌دهد.

## وضعیت اجرایی تأییدشده

- موتور فعال: `tsetmc_scoring_engine.py`
- `scoring_engine.py` فقط Legacy/Historical است و منبع Runtime نیست.
- منبع داده Ranking: فقط canonical TSETMC و مشتقات قطعی همان داده‌ها.
- Ranking scope: `OPPORTUNITY_CANDIDATES`
- وزن بلوک‌ها:
  - Liquidity = 20
  - Valuation = 25
  - Payoff = 18
  - Time = 15
  - Greeks = 12
  - Market = 10
- Greeks در موتور فعال فعلاً unavailable است.
- IV، Open Interest، Risk-Free Rate و Buy/Sell Signal در Ranking فعال استفاده نمی‌شوند.
- Missing data به صفر تبدیل نمی‌شود.
- بازتوزیع داده مفقود فقط داخل همان Block انجام می‌شود.
- Block کاملاً فاقد عامل معتبر برای یک ردیف، برای همان ردیف unavailable می‌ماند و Final Score روی Blockهای دارای شواهد نرمال می‌شود.
- Contract Type فقط از فیلد صریح identity استفاده می‌شود و از نام نماد استنتاج نمی‌شود.

## عوامل فعال

### Liquidity
- Trade Value: بیشتر بهتر
- Volume: بیشتر بهتر

### Valuation
- Time Value: بیشتر بهتر

### Payoff
- Breakeven Distance: کمتر بهتر
- Leverage: بیشتر بهتر
- Moneyness: کمتر بهتر

### Time
- Calendar Days: کمتر بهتر

### Market
- Last vs Close: کمتر بهتر
- Intraday Range: کمتر بهتر

### عوامل غیرفعال
- Greeks
- IV / IV-HV
- Black-Scholes Difference
- Open Interest
- Spread
- Bid/Ask Depth
- Trading Days
- Theta

این موارد در موتور فعال فعلی وارد امتیاز Ranking نمی‌شوند و نباید به‌عنوان عامل فعال گزارش شوند.

## ممیزی اقتصادی عامل‌ها

### 1. Trade Value و Volume

این دو عامل شواهد فعالیت معاملاتی هستند، نه به‌تنهایی شواهد سودآوری یا mispricing. جهت «بیشتر بهتر» از نظر فنی deterministic است، اما اعتبار آن به‌عنوان Opportunity Factor هنوز با داده تاریخی واقعی تأیید نشده است.

### 2. Time Value

فرمول فعال بر اساس نوع قرارداد صریح، قیمت پایه، قیمت اعمال و آخرین قیمت محاسبه می‌شود و مقدار منفی به صفر تبدیل نمی‌شود؛ مقدار منفی از نظر اقتصادی به‌عنوان Time Value پذیرفته نمی‌شود.

مسئله باز: آیا «Time Value بیشتر» در تعریف فرصت پروژه باید در همه رژیم‌های بازار و برای هر دو نوع قرارداد امتیاز مثبت داشته باشد؟ این باید با replay تاریخی واقعی آزمون شود.

### 3. Breakeven Distance

فاصله سر‌به‌سر از قیمت پایه به‌صورت نرمال‌شده محاسبه می‌شود. جهت فعلی «فاصله کمتر بهتر» است.

مسئله باز: این معیار باید در Call و Put و در استراتژی هدف پروژه به‌صورت جداگانه validation شود؛ صرفاً deterministic بودن فرمول برای اثبات مطلوبیت اقتصادی کافی نیست.

### 4. Leverage

موتور فعال مقدار اهرم را از `S / P` مشتق می‌کند، مشروط به مثبت بودن آخرین قیمت.

این مهم‌ترین مورد نیازمند ممیزی اقتصادی مستقل است، زیرا نسبت قیمت پایه به قیمت اختیار فقط زمانی معنای اقتصادی موردنظر پروژه را دارد که واحد قیمت‌ها، اندازه قرارداد و تعریف leverage در داده TSETMC دقیقاً هم‌خوان باشند.

بنابراین فعلاً:
- فرمول تغییر نمی‌کند.
- وزن تغییر نمی‌کند.
- هیچ threshold جدیدی اضافه نمی‌شود.
- اعتبار اقتصادی آن با داده تاریخی و نمونه‌های واقعی بررسی می‌شود.

### 5. Calendar Days

جهت فعلی «کمتر بهتر» است.

این جهت لزوماً معادل «ریسک کمتر» یا «فرصت بیشتر» نیست و می‌تواند به هدف استراتژی وابسته باشد. بنابراین قبل از تغییر، با Historical Sensitivity/Ablation آزمون می‌شود.

### 6. Last vs Close و Intraday Range

هر دو عامل فعال فعلی به‌صورت «کمتر بهتر» امتیاز می‌گیرند.

در نتیجه موتور فعلی بیشتر ثبات/فاصله کمتر را پاداش می‌دهد و هنوز ثابت نشده که این سیاست با Opportunity Detection موردنظر پروژه هم‌جهت است.

## Double-Exposure / Policy Audit

در موتور فعال فعلی، Overlayهای ExecutionPenalty و DecayPenalty در `tsetmc_scoring_engine.py` وجود ندارند و نباید به‌عنوان بخشی از Production TSETMC Evidence Ranking گزارش شوند.

مواردی که همچنان باید بررسی شوند:
- اثر هم‌زمان چند عامل مرتبط با قیمت و payoff
- هم‌بستگی Trade Value و Volume
- هم‌بستگی Breakeven Distance و Moneyness
- اثر مشترک Calendar Days با سایر عوامل
- اینکه نرمال‌سازی percentile باعث غلبه یک خانواده اطلاعاتی بر وزن اسمی Blockها نشود.

## Timestamp و وضعیت بازار

در اجرای واقعی اخیر:
- TSETMC refresh موفق بوده است.
- بازار OFFMARKET بوده است.
- timestamp صریح بازار از رکوردهای دریافت‌شده استخراج نشده است.
- زمان retrieval موجود است و نباید به‌عنوان source market timestamp جایگزین شود.
- `LIVE_MOVEMENT_CLAIM = NOT_CLAIMED` صحیح است.

## Historical Sensitivity / Ablation Audit

مرحله بعدی، بدون تغییر Production Output:

1. Replay روی Snapshotهای واقعی TSETMC.
2. محاسبه Ranking فعلی به‌عنوان baseline.
3. حذف یک عامل در هر بار.
4. حذف یک Block در هر بار.
5. اندازه‌گیری جابه‌جایی Top-N و Spearman/Rank correlation در صورت کفایت داده.
6. بررسی پایداری Top-N در چند snapshot.
7. بررسی جداگانه Call و Put.
8. بررسی هم‌بستگی عوامل.
9. ثبت همه نتایج با SHA و timestamp.
10. عدم اعمال نتیجه به Production تا زمان تأیید سیاست اقتصادی.

## وضعیت نهایی

- Technical implementation: VERIFIED AGAINST ACTIVE CODE PATH
- Production scoring constants: UNCHANGED
- Economic policy validation: OPEN
- Leverage semantic validation: OPEN
- Time-direction validation: OPEN
- Market-direction validation: OPEN
- Historical sensitivity/ablation: NEXT
- Source timestamp availability: OPEN
- No buy/sell signal is generated by this ranking layer.
