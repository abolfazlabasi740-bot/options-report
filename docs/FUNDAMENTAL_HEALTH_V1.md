# کارت سلامت بنیادی V1 — مشخصات Shadow

فایل موجود در پوشه `کارت سلامت بنیادی` یک قالب HTML/CSS با placeholder است، نه موتور محاسبه. قواعد محاسباتی مرجع در `دستورلعمل 5.docx` قرار دارند. این سند آن قواعد را به قرارداد قابل‌آزمون تبدیل می‌کند.

## اصلاح‌های اصلی

- رشد واقعی: `((1 + رشد اسمی) / (1 + تورم هم‌دوره)) - 1`
- `EPS_TTM / Price` با نام درست `Earnings Yield`
- `P/E = Price / EPS_TTM` فقط وقتی EPS مثبت و مخرج معتبر است
- `Dividend Yield = DPS / Price`
- EPS دوازده‌ماهه از چهار فصل افزایشی ساخته می‌شود تا دوباره‌شماری رخ ندهد.
- کیفیت سود با `CFO/NI`، `FCF/NI`، accrual و رشد مطالبات نسبت به فروش سنجیده می‌شود.
- نمودار Y فقط مختصات نمایش است، نه امتیاز بنیادی؛ با clamp و حالت range=0.

## بلوک‌ها

`EarningsQuality`، `CashConversion`، `BalanceSheet`، `GrowthEfficiency`، `RelativeValuation` و `GovernanceEvent`.

پروفایل‌های بانک، هلدینگ، بیمه و غیرمالی جدا هستند؛ نسبت‌های بانک با خودرو/فولاد در یک peer set مخلوط نمی‌شوند.

## قرارداد Evidence

هر metric باید `source`، `evidence_id`، `release_timestamp`، `period_end`، `as_of`، `unit`، `direction`، `formula` و `missing_reason` داشته باشد. اطلاعاتی که بعد از `decision_time` منتشر شده‌اند، look-ahead محسوب می‌شوند.

## وضعیت اجرا

`UnderlyingQualityScore` مستقل از `OptionScore` و در وضعیت `SHADOW_ONLY` است. تا اتصال point-in-time به Codal/TSETMC/پیام ناظر و گذراندن آزمون‌های monotonicity، missingness، sector isolation و walk-forward، این امتیاز وارد رتبه‌بندی Production نمی‌شود.

