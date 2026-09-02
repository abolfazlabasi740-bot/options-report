# راه‌اندازی نسخه GitHub گزارش V4 و ارسال به بله

این بسته همان موتور موجود پروژه را اجرا می‌کند و فقط لایه اجرا را برای
GitHub Actions قابل‌حمل کرده است:

`Optionschool24 → Parsing → Financial → Analytics → Scoring V3 → Risk → V4 leverage gate → TSETMC context → Markdown → PDF RTL/B Nazanin → Bale`

فرمول‌ها و وزن‌های امتیازدهی V3 در این انتقال تغییر نکرده‌اند. V4 همچنان
Candidate است؛ فیلتر اجرایی این Workflow فقط `اهرم >= 3` است و خروجی سیگنال
خرید/فروش تولید نمی‌کند.

## فایل‌های لازم

- `.github/workflows/optionschool-v4-to-bale.yml`
- `scripts/run_github_report.ps1`
- `scripts/render_report_pdf.py`
- `scripts/send_to_bale.py`
- `requirements-github.txt`
- `assets/fonts/BNazanin.ttf`
- `reference/Master Project Book.docx`

## اتصال مخزن

یا خود پوشهٔ `smart_money_project` را در مخزن GitHub قرار دهید، یا محتویات آن
را مستقیماً در ریشهٔ مخزن کپی کنید؛ Workflow هر دو چیدمان را خودکار تشخیص
می‌دهد.
فایل Word مرجع و فونت B Nazanin عمداً داخل پروژه قرار گرفته‌اند تا اعتبارسنجی
SHA-256 و PDF روی Runner به فایل‌های نصب‌شده روی رایانه شخصی وابسته نباشد.

## Secretهای اجباری

در `Settings → Secrets and variables → Actions` دو Secret بسازید:

| نام | مقدار |
|---|---|
| `BALE_BOT_TOKEN` | توکن Bot بله، بدون فاصله و بدون کوتیشن |
| `BALE_CHAT_ID` | شناسه عددی چت/کانال مقصد که Bot در آن مجوز ارسال دارد |

توکن را در کد، فایل اکسل، Issue یا لاگ چاپ نکنید. Workflow فقط آن را به
اسکریپت ارسال می‌دهد و پاسخ موفق/خطا را بدون توکن ثبت می‌کند.

## زمان‌بندی

زمان پیش‌فرض Workflow ساعت `۱۲:۴۵` به وقت `Asia/Tehran` در روزهای شنبه تا
چهارشنبه است. برای هماهنگ‌کردن با زمان فعلی سامانه خودتان، فقط خط `cron` در
فایل Workflow را تغییر دهید. اجرای دستی نیز از زبانه Actions با
`Run workflow` فعال است.

## خروجی هر اجرا

در هر Run این موارد ساخته و در Artifact گیت‌هاب نگهداری می‌شوند:

- گزارش Markdown با جدول اصلی دقیقاً ۱۱ ستون V3؛
- PDF راست‌به‌چپ با فونت B Nazanin؛
- فایل خام Optionschool؛
- Run Snapshot، Ranking/Feature Snapshot؛
- Audit، Learning و Hash Manifest.

بخش «بحث آموزشی اجباری» در Markdown و PDF باقی می‌ماند. هیچ تغییر خودکار در
وزن‌ها یا Ruleهای Production انجام نمی‌شود.

برای اینکه مقایسه‌ی واقعی هفت‌روزه بین Runهای جداگانه حفظ شود، Workflow فایل‌های
خام روزانه را با یک commit کوچک به همان شاخه‌ی پیش‌فرض برمی‌گرداند. بنابراین
مجوز `Contents: Read and write` باید در تنظیمات Repository برای Actions فعال
باشد. اگر Branch Protection اجازه‌ی این commit را ندهد، ارسال PDF همچنان انجام
می‌شود اما پنجره‌ی یادگیری فقط فایل‌های موجود در همان Run را خواهد داشت.

## خطاهای متداول

### `BALE_BOT_TOKEN is missing`

Secretها در سطح همان Repository تعریف نشده‌اند یا نامشان دقیق نیست.

### `Forbidden` یا `chat not found`

Bot را به چت/کانال اضافه کنید، مجوز ارسال بدهید و مقدار `BALE_CHAT_ID` را
اصلاح کنید.

### خطای Excel/ImportExcel

Runner ابتدا از parser داخلی OpenXML استفاده می‌کند و به Excel یا Microsoft
Office وابسته نیست. `ImportExcel` فقط fallback اختیاری است؛ در صورت خطای
ساختار XLSX یا ناقص‌بودن فایل، اجرای دستی را دوباره با فایل سالم اجرا کنید.

### خطای PDF یا فونت

وجود `assets/fonts/BNazanin.ttf` و کوچک‌تر بودن فایل PDF از ۵۰ مگابایت را
بررسی کنید. نبود فونت باعث توقف عمدی مرحله PDF می‌شود تا گزارش با فونت
ناخواسته ارسال نشود.

## تفاوت با اجرای محلی

در ویندوز، parser در صورت وجود Excel از COM استفاده می‌کند. در GitHub که Excel
نصب نیست، parser داخلی OpenXML اجرا می‌شود و فقط در صورت خطای آن،
`ImportExcel` به‌عنوان fallback اختیاری امتحان می‌شود؛ ساختار ۳۸ستونه قبل از
امتیازدهی کنترل می‌شود. لایه امتیاز، ریسک، تصمیم،
گزارش و یادگیری مشترک باقی می‌ماند.
