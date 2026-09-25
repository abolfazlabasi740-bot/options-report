# Economic Scoring Audit — OptimusAI V4.1.1

## هدف

این ممیزی برای تفکیک «آنچه در کد اجرا می‌شود» از «آنچه از نظر اقتصادی باید قبل از نهایی‌سازی سیاست امتیازدهی تأیید شود» انجام شده است.

این سند هیچ وزن، آستانه، جهت امتیازدهی یا فرمول فعال را تغییر نمی‌دهد. موارد زیر صرفاً وضعیت فعلی، ریسک سیاستی و آزمون لازم برای اعتبارسنجی اقتصادی را ثبت می‌کند.

## وضعیت اجرایی فعلی

- موتور مرجع فعال در مسیر TSETMC-only: `tsetmc_scoring_engine.py`
- `scoring_engine.py` موتور تاریخی/Legacy است و نباید به‌عنوان منبع سیاست امتیازدهی Runtime تفسیر شود.
- نسخه معماری فعال: TSETMC Evidence Ranking
- Six-Block weights:
  - Liquidity = 20
  - Valuation = 25
  - Payoff = 18
  - Time = 15
  - Greeks = 12
  - Market = 10
- Missing factor فقط داخل همان Block بازتوزیع می‌شود.
- Block کاملاً فاقد داده، امتیاز صفر تلقی نمی‌شود و برای FinalScore مانع ایجاد می‌کند.
- Contract Type از نام نماد استنتاج نمی‌شود.
- Moneyness تا زمان وجود Contract Type صریح، غایب است و وزن آن در Payoff بازتوزیع می‌شود.
- Status در Market هنوز نگاشت عددی تأییدشده ندارد و وزن آن بین عوامل موجود همان Block بازتوزیع می‌شود.
- Risk thresholds رسمی در دسترس نیست؛ RiskPenalty فعلاً صفر و وضعیت آن صریحاً KNOWN_GAP_THRESHOLDS_NOT_AVAILABLE است.
- Overlay فعال FinalScore را با ExecutionPenalty، DecayPenalty و DataConfidence تعدیل می‌کند.
- MIN_LEVERAGE در مسیر تولیدی gate فعال است و مقدار مشاهده‌شده فعلی 3.5 است؛ منشأ تأیید این مقدار باید جداگانه بسته شود.

## ممیزی عامل‌به‌عامل

### 1. Liquidity

عوامل:
- Trade Value: بیشتر بهتر
- Volume: بیشتر بهتر
- Open Interest: در موتور فعال TSETMC استفاده نمی‌شود
- Spread: در موتور فعال TSETMC در Ranking استفاده نمی‌شود
- Depth: در موتور فعال TSETMC در Ranking استفاده نمی‌شود

ارزیابی:
- Trade Value، Volume، Open Interest و Depth عمدتاً شاخص‌های ظرفیت/قابلیت معامله هستند، نه به‌تنهایی شاخص فرصت اقتصادی.
- Spread شاخص مستقیم‌تری از هزینه اجرای معامله است.
- Spread در BaseScore حضور دارد و دوباره در ExecutionPenalty استفاده می‌شود. بنابراین exposure تکراری واقعی وجود دارد.

نتیجه ممیزی:
- منطق اجرایی فعلی قابل بازتولید است.
- تکرار Spread باید در پروتکل اقتصادی صریحاً توجیه شود: یک‌بار به‌عنوان کیفیت نقدشوندگی و بار دوم به‌عنوان جریمه قابلیت اجرا.
- تا قبل از تأیید این سیاست، مقدار یا وزن تغییر نکند.

### 2. Valuation

عوامل:
- Time Value: بیشتر بهتر
- Black-Scholes Difference: در موتور فعال TSETMC محاسبه نمی‌شود
- IV: در موتور فعال TSETMC محاسبه نمی‌شود
- IV/HV: در موتور فعال TSETMC محاسبه نمی‌شود

نکته کلیدی:
- IV به‌صورت مستقل «بیشتر بهتر» امتیاز می‌گیرد، در حالی که IV/HV «کمتر بهتر» است.
- این دو جهت می‌توانند در بعضی مقاطع یک قرارداد را همزمان تقویت و تضعیف کنند.
- از نظر اقتصادی، IV بالا ذاتاً فرصت یا مزیت نیست؛ ارزش آن به قرارداد، قیمت‌گذاری، ریسک، نقدشوندگی و مقایسه با نوسان تاریخی وابسته است.
- Black-Scholes Difference نیز فقط در صورت معتبر بودن ورودی‌های مدل و فرضیات آن، معیار قابل اتکای mispricing است.

نتیجه ممیزی:
- جهت‌های فعلی «سیاست‌های اجرایی موجود» هستند، نه نتیجه تأیید اقتصادی مستقل.
- قبل از نهایی‌سازی باید با یک آزمون تاریخی out-of-sample بررسی شود که این جهت‌ها واقعاً با تعریف فرصت موردنظر پروژه هم‌راستا هستند.

### 3. Payoff

عوامل:
- Breakeven Distance: فاصله کمتر بهتر
- Leverage: بیشتر بهتر، با clip و percentile
- Moneyness: فعلاً غایب

نکته کلیدی:
- Breakeven Distance یک معیار payoff-oriented است، ولی بدون Contract Type صریح، تفسیر اقتصادی آن می‌تواند برای Call و Put متفاوت باشد.
- Leverage هم gate است و هم در رتبه‌بندی اثر دارد. این «double arithmetic» نیست، اما یک قرارداد ابتدا با leverage پایین حذف می‌شود و سپس leverage قراردادهای باقی‌مانده امتیاز می‌گیرد.
- Moneyness عمداً تا زمان دسترسی به نوع قرارداد فعال نشده است.

نتیجه ممیزی:
- عدم استنتاج Contract Type تصمیم حفاظتی صحیح برای جلوگیری از inference است.
- منشأ و هدف MIN_LEVERAGE=3.5 باید ثبت و تأیید شود.
- جهت و وزن Leverage باید با تعریف «فرصت» پروژه، نه صرفاً جذابیت اهرم، اعتبارسنجی شود.

### 4. Time

عوامل:
- Calendar Days: کمتر بهتر
- Trading Days: در موتور فعال TSETMC استفاده نمی‌شود
- Theta absolute: در موتور فعال TSETMC محاسبه نمی‌شود

نکته کلیدی:
- Time-to-expiry هم در Block Time وارد می‌شود و هم از طریق DecayPenalty در Overlay اثر می‌گذارد.
- RemainingDays > 0 نیز gate تولیدی است.
- بنابراین سه نقش متفاوت وجود دارد: eligibility gate، ranking factor و risk/decay overlay.

نتیجه ممیزی:
- این سه نقش می‌توانند از نظر طراحی قابل دفاع باشند، اما باید در پروتکل روشن شود که چرا اثر زمان در سه لایه تکرار می‌شود.
- Theta با absolute value جهت قرارداد را حذف می‌کند؛ این انتخاب نیازمند validation اقتصادی است.

### 5. Greeks

عوامل:
- Greeks در موتور فعال TSETMC محاسبه نمی‌شوند؛ بنابراین این Block فعلاً unavailable است.

نکته کلیدی:
- magnitude-only بودن Greeks عمداً جهت قرارداد را وارد نمی‌کند.
- برای Opportunity Intelligence، «بیشتر بودن قدرمطلق» لزوماً به معنی فرصت بهتر نیست.
- بدون Contract Type و بدون تعریف صریح strategy/objective، تفسیر Delta/Vega/Rho و حتی Gamma می‌تواند policy-dependent باشد.

نتیجه ممیزی:
- فعلاً این بخش را نباید با حدس اقتصادی اصلاح کرد.
- نیاز به تعریف رسمی هدف امتیازدهی و validation روی معاملات/سناریوهای تاریخی دارد.

### 6. Market

عوامل:
- Last vs Close: انحراف مطلق کمتر بهتر
- Intraday Range: کمتر بهتر
- Status: نگاشت عددی فعال نیست

نکته کلیدی:
- هر دو عامل فعال Market در نسخه فعلی بیشتر «ثبات قیمت» را پاداش می‌دهند تا «فرصت حرکت».
- بنابراین اگر هدف پروژه Opportunity Detection باشد، جهت فعلی باید جداگانه validation شود.
- Status عمداً بدون نگاشت عددی مانده است و این محدودیت نباید با حدس پر شود.

نتیجه ممیزی:
- Market block از نظر فنی deterministic است، ولی از نظر اقتصادی هنوز policy-validated نیست.

## Overlay

در مسیر فعال `tsetmc_scoring_engine.py`، Base Ranking با Overlayهای `ExecutionPenalty` و `DecayPenalty` مدل قدیمی یکی نیست. بنابراین پارامترهای Overlay زیر را نباید به‌عنوان پارامتر فعال TSETMC Evidence Ranking تلقی کرد.

### ExecutionPenalty

فرمول مشاهده‌شده:
- Spread <= reference: بدون جریمه افزایشی
- reference=12
- scaling denominator=28
- intermediate cap=0.35
- missing spread penalty=0.10
- final cap=0.45

این اعداد در حال حاضر «Observed Active Parameters» هستند و provenance تأییدشده اقتصادی برای آن‌ها در repository بسته نشده است.

### DecayPenalty

آستانه‌های مشاهده‌شده:
- RemainingDays <= 2 → 0.30
- RemainingDays <= 5 → 0.18
- RemainingDays <= 10 → 0.08
- بیشتر از آن → 0

این مقادیر باید با یک مرجع مصوب یا baseline تاریخی قابل بازتولید مستند شوند.

### Confidence

DataConfidence فعلی عمدتاً روی چند فیلد critical، IV، HV و Breakeven حساس است و «امتیاز کامل کیفیت داده» نیست.

نتیجه:
- نباید FinalScore را به‌عنوان یک confidence کامل درباره همه عوامل تفسیر کرد.
- اگر قرار است Confidence معنای جامع داشته باشد، باید دامنه آن بازطراحی و سپس validation شود؛ فعلاً تغییر نکند.

## Double Exposure Register

| مورد | لایه اول | لایه دوم | وضعیت |
|---|---|---|---|
| Spread | Liquidity | ExecutionPenalty | نیازمند توجیه اقتصادی |
| Time-to-expiry | Time block | DecayPenalty | نیازمند توجیه اقتصادی |
| RemainingDays | Eligibility gate | Time/Decay | gate + ranking + overlay |
| Leverage | Eligibility gate | Payoff score | gate + ranking |

هیچ‌کدام در این ممیزی حذف یا تعدیل نشده است.

## اولویت اعتبارسنجی اقتصادی

قبل از هر تغییر عددی، validation باید حداقل این چهار سؤال را پاسخ دهد:

1. آیا افزایش FinalScore در داده‌های تاریخی با تعریف واقعی «فرصت» پروژه هم‌جهت است؟
2. آیا عوامل با هم اطلاعات تکراری ایجاد می‌کنند و وزن مؤثر برخی متغیرها بیش از وزن اسمی آن‌ها می‌شود؟
3. آیا جهت هر عامل در Call و Put یکسان قابل دفاع است یا به Contract Type نیاز دارد؟
4. آیا Overlay واقعاً کیفیت اجرا/ریسک را بهبود می‌دهد یا صرفاً همان اطلاعات BaseScore را دوباره جریمه می‌کند؟

## تست‌های لازم بدون تغییر Production Policy

تا زمان تصویب اقتصادی، تست‌های بعدی باید فقط این موارد را بررسی کنند:

- deterministic بودن امتیاز برای ورودی یکسان
- حفظ مجموع وزن هر Block
- بازتوزیع فقط داخل همان Block
- عدم تبدیل missing به صفر
- عدم inference نوع قرارداد
- حفظ gateهای RemainingDays و MIN_LEVERAGE
- ثبت provenance همه پارامترهای Overlay
- ثبت اثر مستقل BaseScore و Overlay
- مقایسه ranking قبل/بعد از حذف هر عامل برای سنجش sensitivity
- replay روی داده تاریخی واقعی و بدون داده مصنوعی

## وضعیت نهایی ممیزی

- Active technical implementation: `tsetmc_scoring_engine.py` VERIFIED FOR CURRENT TSETMC CODE PATH
- Economic policy validation: OPEN
- Overlay parameter provenance: OPEN
- Contract identity for TSETMC: PENDING
- No scoring constants changed by this audit.
- No ranking or Bale output logic changed by this audit.

## تصمیم اجرایی

تا بسته‌شدن validation اقتصادی و provenance، Production Scoring تغییر عددی نمی‌کند.

مرحله بعدی پروژه باید «Historical Sensitivity / Ablation Audit» باشد: با داده واقعی موجود، اثر هر عامل و هر Block بر رتبه‌بندی و پایداری Top-N اندازه‌گیری شود، بدون اینکه خروجی Production تغییر کند.
