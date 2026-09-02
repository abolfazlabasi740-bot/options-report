# Options Analytics System

این پروژه طبق `reference/Master Project Book.docx` اداره می‌شود.

- Baseline اجرایی: `PROTOCOL_OPTIONS_RANKING_V3`
- V4: Candidate و غیرمجاز برای معرفی به‌عنوان Scoring Production
- منبع داده Production: Optionschool24
- نسخه پروژه: `3.2.0`

دستورالعمل اجرایی کامل در `docs/EXECUTION_BASELINE.md` و خلأهای تأییدنشده در `docs/KNOWN_GAPS.md` ثبت شده‌اند.

## زنجیره اجرا

`Data → Parsing → Financial → Analytics → Scoring → Risk → Strategy → Decision → Reporting → Audit → Learning → Knowledge`

## موتورهای فعال

- Data: دریافت و اعتبارسنجی XLSX واقعی Optionschool24
- Parsing: کنترل Schema مصوب ۳۸ ستونی و Schema Hash
- Financial: محاسبات Call/Put و Featureهای مشتق‌شده
- Analytics: Data Confidence، Missing Data، Flags و Feature Registry
- Scoring: شش بلوک V3 با Robust Percentile و بازتوزیع وزن Missing
- Risk: موتور مستقل؛ حالت جاری Transitional است چون آستانه‌های پله‌ای Master موجود نیست
- Strategy: فقط قرارداد و وضعیت Rule؛ بدون ساخت Rule حدسی
- Decision: ترتیب Gateهای مصوب و خروجی تصمیم‌یار، بدون سیگنال خرید/فروش
- Reporting: Markdown رسمی و DOCX درخواستی
- Audit: Run Manifest، Input Manifest، Feature/Ranking Snapshot و Hash Manifest
- Learning/Knowledge: ثبت تجربه خام، بدون تغییر خودکار Production

## اجرای Pipeline با فایل محلی

```powershell
.\scripts\run_pipeline.ps1 -InputWorkbook '..\optionschool24_all_1786362326.xlsx'
```

## دانلود و اجرا

```powershell
.\scripts\run_pipeline.ps1 -Download
```

## اجرای رسمی زمان‌بندی‌شده

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\smart_money_project\scripts\run_scheduled.ps1 -ProjectRoot .\smart_money_project
```

## تست

```powershell
.\tests\master_baseline_test.ps1
.\tests\smoke_test.ps1 -WorkbookPath '..\optionschool24_all_1786362326.xlsx'
```

هر گزارش تازه باید Run ID، SHA-256 ورودی، نسخه Config، Digest رتبه‌بندی، Audit و Hash Manifest مخصوص همان Run را داشته باشد. فایل تاریخی گزارش تازه محسوب نمی‌شود.

## GitHub Actions و ارسال خودکار به بله

نسخه قابل‌اجرای GitHub در مسیر زیر قرار دارد:

` .github/workflows/optionschool-v4-to-bale.yml `

راهنمای کامل نصب، Secretها، زمان‌بندی و خطاها:

`docs/GITHUB_BALE_SETUP_FA.md`

این Workflow به‌صورت خودکار فایل Optionschool24 را می‌گیرد، موتور V3 را با
فیلتر Candidate اهرم حداقل ۳ اجرا می‌کند، تحلیل سهم پایه را از TSETMC اضافه
می‌کند، PDF راست‌به‌چپ B Nazanin می‌سازد و آن را به Bale می‌فرستد. فرمول‌ها و
وزن‌های V3 تغییر نکرده‌اند و خروجی همچنان تصمیم‌یار بدون سیگنال قطعی خرید/فروش
است.
