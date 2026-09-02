# دستورالعمل اجرایی مبتنی بر Master Project Book

## مرجع حاکم

- مرجع رسمی: `../reference/Master Project Book.docx`
- SHA-256 مرجع: `3cba9235181063f040f6df83f18e2b739395528f417d1179ec02eb2ce10f9268`
- Baseline اجرایی: `PROTOCOL_OPTIONS_RANKING_V3`
- وضعیت V4: Candidate و غیرمجاز برای معرفی به‌عنوان Production

## زنجیره رسمی اجرا

`Source Adapter → Raw Evidence → Validation → Parsing/Normalization → Financial → Analytics/Features → Scoring → Risk → Decision → Strategy → Reporting → Audit → Learning → Knowledge`

دستور رسمی اجرای زمان‌بندی‌شده:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\smart_money_project\scripts\run_scheduled.ps1 -ProjectRoot .\smart_money_project
```

## قواعد غیرقابل نقض

- منبع داده Production فعلی فقط Optionschool24 است.
- تمام گزارش‌های درخواستی مرتبط با Optionschool24، بدون استثنا، باید در قالب، ساختار جدول رتبه‌بندی و پروتکل اجرایی `PROTOCOL_OPTIONS_RANKING_V3` تهیه و ارائه شوند. استفاده از قالب، رتبه‌بندی یا ادعای نسخه‌ای غیر از V3 برای این گزارش‌ها ممنوع است؛ مگر آن‌که کاربر صراحتاً دستورالعمل رسمی جایگزین را تصویب کند.
- هیچ عدد، وزن، آستانه، فرمول، API یا نتیجه بدون Evidence ساخته نمی‌شود.
- داده مفقود امتیاز ثابت نمی‌گیرد و وزن عامل مفقود داخل همان بلوک بازتوزیع می‌شود.
- Score تنها ورودی Decision نیست و خروجی سیگنال قطعی خرید یا فروش تولید نمی‌کند.
- Learning فقط Candidate تغییر تولید می‌کند و اجازه تغییر خودکار Production ندارد.
- هر Run باید Input، Version، Feature، Score، Risk، Decision، Report، Learning و Hash Manifest داشته باشد.

## مدل امتیازدهی مصوب

### قرارداد قطعی جدول اصلی V3

جدول اصلی رتبه‌بندی در تمام گزارش‌های Optionschool24 باید دقیقاً ۱۱ ستون زیر را با همین ترتیب و عنوان داشته باشد:

`رتبه | نماد | اعمال | آخرین | سر به سری | پایه | اهرم | فاصله سر به سری | سررسید | باقی مانده روز | امتیاز`

افزودن، حذف، جابه‌جایی یا تغییر عنوان این ۱۱ ستون مجاز نیست. جداول تحلیلی تکمیلی، در صورت نیاز، باید بعد از جدول اصلی و با عنوان جداگانه ارائه شوند.

### تعریف گزارش V4 کاندید

گزارش V4 کاندید، نسخه آزمایشی است و Production محسوب نمی‌شود. همه عوامل، وزن‌ها و محاسبات V3 را ثابت نگه می‌دارد و فقط می‌تواند یک فیلتر صلاحیت اعلام‌شده (در اجرای فعلی: `اهرم >= 3`) و یک بخش تحلیل سهم پایه/اخبار در انتهای گزارش اضافه کند. جدول اصلی همچنان همان ۱۱ ستون V3 است.

| بلوک | وزن | عوامل داخلی |
|---|---:|---|
| Liquidity | ۲۰ | Trade Value ۳۵٪، Volume ۲۵٪، OI ۱۵٪، Spread ۱۵٪، Depth ۱۰٪ |
| Valuation | ۲۵ | BS Edge ۳۲٪، IV ۲۸٪، IV/HV ۲۰٪، Time Value ۲۰٪ |
| Payoff | ۱۸ | Break-even Distance ۵۵٫۵۶٪، Leverage ۲۷٫۷۸٪، Moneyness ۱۶٫۶۷٪ |
| Time | ۱۵ | Trading Days ۴۰٪، Calendar Days ۱۳٫۳۳٪، Theta ۴۶٫۶۷٪ |
| Greeks | ۱۲ | Delta ۳۳٫۳۳٪، Gamma ۲۵٪، Vega ۲۵٪، Rho ۱۶٫۶۷٪ |
| Market Structure | ۱۰ | Last vs Close ۴۰٪، Intraday Range ۳۰٪، Status ۳۰٪ |

## مرزهای تأیید

- `Last vs Close` و `Intraday Range` با Robust Percentile معکوس V3 اجرا می‌شوند.
- نگاشت عددی وضعیت‌های «در سود/بی‌تفاوت/در ضرر» مصوب نیست؛ Status امتیاز ساختگی نمی‌گیرد و Missing محسوب می‌شود.
- Master جریمه پله‌ای Risk برابر ۰/۵/۱۰/۲۰ را ثبت کرده، اما آستانه دقیق پنج وضعیت نامطلوب را ارائه نکرده است.
- تا بازیابی کد مرجع `PROTOCOL_OPTIONS_RANKING_V3.py` یا Configuration معتبر، Risk جاری با برچسب Transitional اجرا و در Audit به‌عنوان Known Gap ثبت می‌شود.

## خروجی معتبر

فقط خروجی Run تازه که Run ID، فایل ورودی، SHA-256، نسخه Config، نسخه کد و Hash Manifest منطبق داشته باشد گزارش تازه محسوب می‌شود. هیچ فایل قدیمی نباید به‌عنوان گزارش Run جدید معرفی شود.
