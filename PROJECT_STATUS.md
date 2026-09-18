# OptimusAI V4.1 LIVE

## Current Baseline

- Local path: `~/OptimusAI_V41_LIVE`
- GitHub repository: `abolfazlabasi740-bot/options-report`
- Current operational commit: `4b908b2`
- Commit message: `Add Bale listener and symbol-specific V4.1 reports`
- GitHub main has been successfully pushed to this commit.

## هدف پروژه

تولید گزارش واقعی اختیار معامله با داده OptionSchool24، اجرای موتور امتیازدهی Six-Block V4.1 و ارسال گزارش Card-style به Bale.

## معماری

OptionSchool24
→ Data Validation
→ Six-Block Scoring
→ Risk Overlay
→ Card Report
→ Bale Listener
→ Bale

یک موتور تحلیل مرکزی وجود دارد و Bale موتور تحلیل جداگانه ندارد.

## Six-Block V4.1

### Liquidity — 20
- Trade Value: 7
- Volume: 5
- Open Interest: 3
- Spread: 3
- Depth: 2

### Valuation — 25
- Black-Scholes Difference: 8
- IV: 7
- IV/HV Ratio: 5
- Time Value: 5

### Payoff — 18
- Breakeven Distance: 10
- Leverage: 5
- Moneyness: 3

### Time — 15
- Trading Days: 6
- Calendar Days: 2
- Theta: 7

### Greeks — 12
- Delta: 4
- Gamma: 3
- Vega: 3
- Rho: 2

### Market — 10
- Last vs Close
- Intraday Range

Missing factors are redistributed only within the same block according to available weight.

## FinalScore

BaseScore از مجموع شش Block ساخته می‌شود و سپس V4 Overlay اعمال می‌شود:

- Execution Penalty
- Leverage cap
- Decay Penalty
- Confidence

RemainingDays فعلی:
`(روزهای تقویمی - 1).clip(lower=0)`

قراردادهای منقضی و قراردادهای فاقد شرایط لازم وارد رتبه‌بندی نهایی نمی‌شوند.

## Global Report

دستور Bale:

`گزارش`

یا:

`کل`

نتیجه:
- دریافت فایل جدید از OptionSchool24
- اجرای Six-Block Scoring
- انتخاب Top 15 کل بازار
- ساخت Card Report
- ارسال به Bale

## Symbol Report

هر Prefix نماد مانند:

`ضهرم`
`ضملت`
`ضصاد`

نتیجه:
- دریافت فایل جدید
- اجرای همان Six-Block Scoring
- فیلتر نماد قبل از رتبه‌بندی
- رتبه‌بندی کل قراردادهای واجد شرایط همان نماد
- انتخاب حداکثر Top 5
- ارسال Card Report به Bale

قاعده مهم:
Symbol Filter باید قبل از Top-N انجام شود.

اگر کمتر از 5 قرارداد واجد شرایط وجود داشته باشد، همان تعداد موجود گزارش می‌شود و هیچ داده‌ای ساخته نمی‌شود.

قاعده نام‌گذاری:
- ض = Call
- ط = Put

## Bale Listener

فایل اصلی:

`bale_listener.py`

این فایل:
- پیام Bale را دریافت می‌کند.
- دستور را Normalize می‌کند.
- برای هر درخواست داده جدید OptionSchool24 می‌گیرد.
- گزارش را با همان Report Engine تولید می‌کند.
- `output/latest_report.txt` را به‌روزرسانی می‌کند.
- گزارش را به Bale ارسال می‌کند.

### اجرای Listener

در Termux:

```bash
cd ~/OptimusAI_V41_LIVE
python3 bale_listener.py
```

پس از اجرای آن، پنجره Termux باید باز بماند.

### دستورات Bale

```
گزارش
```
→ Top 15 کل بازار

```
کل
```
→ Top 15 کل بازار

مثال:

```
ضهرم
```
→ حداکثر Top 5 قرارداد واجد شرایط ضهرم

مثال:

```
ضملت
```
→ حداکثر Top 5 قرارداد واجد شرایط ضملت

توقف Listener:

```
Ctrl + C
```

Token نباید داخل کد یا GitHub ذخیره شود؛ Listener از متغیر محیطی `BALE_BOT_TOKEN` استفاده می‌کند.

## تست‌های واقعی انجام‌شده

### Global
فایل واقعی OptionSchool24:
`optionschool_20260918_134314.xlsx`

15 قرارداد با FinalScore معتبر تولید شد.

نمونه Top:
- ضخود7133: 69.52
- ضملت7042: 69.29
- ضخود7134: 67.97
- ضستا7060: 66.93
- ضملی7074: 66.82
- ضستا7061: 66.69
- ضخود7132: 66.59
- ضملت7043: 65.33
- ضملت7044: 65.25
- ضستا7062: 64.88
- ضخود7135: 64.16
- ضهرم7062: 63.15
- ضسپا7029: 62.99
- ضستا7063: 62.45
- ضخود8059: 61.70

### Symbol
برای `ضهرم` چهار قرارداد واجد شرایط پیدا شد:
- ضهرم7062: 63.15
- ضهرم7063: 59.85
- ضهرم7064: 57.61
- ضهرم7065: 51.27

این تست ثابت کرد Symbol Filter قبل از Top-N اجرا می‌شود.

### Bale
Listener با موفقیت دستورات `گزارش` و `ضهرم` را دریافت و گزارش را ارسال کرده است.

نمونه لاگ موفق:

```
COMMAND = گزارش | CHAT_ID = ...
SENT 1/1
REPORT_OK command=گزارش
```

و:

```
COMMAND = ضهرم | CHAT_ID = ...
SENT 1/1
REPORT_OK command=ضهرم
```

### Python
تست Compile موفق:

```bash
python3 -m py_compile report_engine.py scoring_engine.py bale_listener.py
```

### Git
Commit پایه:
`c373d1d`

Commit فعلی:
`4b908b2`

Push به `main` موفق بوده است.

## فایل‌های اصلی

- `PROJECT_STATUS.md`
- `report_engine.py`
- `scoring_engine.py`
- `bale_listener.py`
- `send_to_bale.py`
- `requirements.txt`
- `.gitignore`
- `config/runtime.env.example`

`send_to_bale.py` فعلاً نگه داشته شده و هنوز تصمیم نهایی درباره حذف آن گرفته نشده است؛ Listener اصلی `bale_listener.py` است.

## خطوط قرمز

- داده ساختگی ممنوع.
- Token و Secret نباید Commit شوند.
- تغییر Six-Block بدون تست و ثبت نسخه ممنوع.
- ادعای تست بدون Evidence ممنوع.
- فایل قدیمی فقط بعد از بررسی کاربرد حذف شود.
- موتور تحلیل دوم برای Bale ساخته نشود.
- موتور فعلی سیگنال Buy/Sell تولید نمی‌کند.
- تحلیل TSETMC و تحلیل سهم پایه فعلاً مستقل است و هنوز به V4.1 متصل نشده است.

## مرحله بعدی

### Project Audit & Cleanup

1. بررسی وضعیت واقعی Termux و GitHub.
2. تطبیق فایل‌های Local با GitHub.
3. شناسایی Backup و فایل‌های قدیمی.
4. بررسی کاربرد `send_to_bale.py`.
5. بررسی و تکمیل مستندات.
6. حذف فقط فایل‌های واقعاً اضافه.
7. اجرای تست کامل.
8. Commit و Push نسخه تمیز بعدی.

## دستور ادامه در چت بعدی

برای ادامه پروژه از همین نقطه:

> از وضعیت Commit 4b908b2 پروژه OptimusAI V4.1 ادامه بده. مرحله بعد Project Audit & Cleanup است. ابتدا وضعیت واقعی Termux و GitHub را بررسی کن و بدون تغییر در Six-Block Scoring، فایل‌های اضافه و قدیمی را ممیزی کن.

## وضعیت

Six-Block Scoring: ACTIVE
OptionSchool24 Live Data: ACTIVE
Global Top 15: VERIFIED
Symbol Top 5: VERIFIED
Bale Listener: VERIFIED
Bale Card Report: VERIFIED
GitHub: SYNCED
Current Baseline: 4b908b2
Next Phase: Project Audit & Cleanup
