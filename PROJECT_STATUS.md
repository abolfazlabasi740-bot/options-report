# OptimusAI V4.1 LIVE

## Corrective revision — V4.1.1 (2026-09-19)

Base: `ac6621600fffeac53c4426607818d62e8269b348` on GitHub main.
This revision is prepared for GitHub distribution. Updating and restarting the Termux instance is a separate deployment step.
The historical status below describes the old baseline, not the current test results.

- Validate schema, finite positive critical data, active days, minimum leverage and unique symbols before cross-sectional scoring.
- Apply the existing 0.92 leverage score cap before block/BaseScore calculation.
- Calculate intraday range from high/low prices, never bid/ask quotes; missing factors remain missing and redistribute within their block.
- Reject final scores with an entirely unavailable block rather than silently treating that block as zero.
- Use one breakeven-distance calculation for scoring and display.
- Preserve the existing six block weights and time-factor directions; investment-policy redesign is outside this patch.
- Preserve the documented `calendar_days - 1` convention and disclose it. Its source convention still needs separate confirmation.
- Report data-completeness index, missing-factor flags and penalties. The index is not a probability of profit or full coverage of every factor.
- Source workbook has no market timestamp: freshness remains UNVERIFIED and is explicitly disclosed. Download time is not market time.
- Both senders require explicit `BALE_CHAT_ID`. No automatic first/last-message recipient selection. Request errors do not expose token-bearing URLs.
- Cards are split at card/newline boundaries where possible.
- CLI and Bale use the same engine and write `output/latest_report.txt` plus `output/latest_audit.json` with source SHA-256 and selected score components.

Validation: `python -m unittest discover -s tests -v` (20 regression tests).
Real workbook fetched on 2026-09-19: 460 rows, 174 eligible, 286 excluded, no entirely missing block among eligible rows.
No messages were sent to Bale. No production Termux instance was changed.

Usage:

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python report_engine.py
python report_engine.py --input data/example.xlsx --symbol ضهرم --top 5
```

Set `BALE_BOT_TOKEN` and `BALE_CHAT_ID` in the process environment before running `python bale_listener.py`.
`config/runtime.env.example` is an example, not an automatically loaded configuration.

---

## Current Baseline

- Local path: `~/OptimusAI_V41_LIVE`
- GitHub repository: `abolfazlabasi740-bot/options-report`
- Current GitHub main is the cleanup line following `f36c1b9`.
- Active runtime entry points: `report_engine.py` and `bale_listener.py`.
- Termux deployment/restart is not verified by this GitHub audit and must not be inferred from repository state.

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
Commit پایه تاریخی:
`c373d1d`

Commit Baseline تاریخی:
`4b908b2`

آخرین خط GitHub بعد از Audit & Cleanup: زنجیره Commit جدیدتر از `f36c1b9`.
وضعیت دقیق Termux از GitHub قابل استنتاج نیست و فقط پس از اجرای واقعی قابل ثبت است.

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

### Runtime Verification & Architecture Expansion

1. استقرار و Restart نسخه تمیز روی Termux و ثبت Evidence.
2. اجرای تست کامل روی آخرین Workbook واقعی OptionSchool24.
3. تطبیق خروجی Bale با Audit JSON و Snapshot Hash.
4. سپس ورود کنترل‌شده به لایه‌های Opportunity / Case / Red Team / Attention.
5. هر موتور جدید ابتدا در Shadow اجرا شود و قبل از Cutover با Golden/Regression Dataset مقایسه شود.

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
Current Baseline: post-f36c1b9 cleanup line
Next Phase: Runtime Verification & Architecture Expansion


## Audit & Cleanup — 2026-09-21

- GitHub main was audited against the active V4.1.1 path.
- Obsolete V3-only reporting code and `legacy_main` were removed from `scoring_engine.py`; the active scoring functions were not redesigned.
- `send_to_bale.py` remains only as an explicit manual one-shot sender and is not imported by the runtime listener.
- Regression coverage now includes six-block weight integrity and deterministic tie-breaking.
- GitHub Actions regression workflow added at `.github/workflows/regression.yml`.
- No claim is made here that the updated code has already been deployed/restarted on Termux.
- The repository now contains a non-blocking Shadow Opportunity Engine. It is executed from the report path and persisted to `output/latest_opportunity_shadow.json`, but it does not alter FinalScore, Top-N ranking, or Bale message content.
- The final target architecture (Case lifecycle, Red Team runtime, Attention Allocation, FindChart confirmation, Replay/Golden Dataset, etc.) is still not production-active.


## Opportunity Shadow — 2026-09-21

- Engine: `OPP-SHADOW-1.0`.
- State: `SHADOW_ACTIVE_NON_BLOCKING`.
- Full scored universe is scanned before symbol/Top-N filtering.
- Snapshot identity uses the real workbook SHA-256; deterministic DataFrame hashing is used only for test doubles without a physical file.
- Case families currently implemented: Relative Value Anomaly, Breakeven Compression, Liquidity Confirmed, Near Expiry Risk.
- Statuses: CONFIRMED, WATCH, REJECTED, INSUFFICIENT_DATA.
- Shadow output is persisted separately from the main report and summarized in `latest_audit.json`.
- CI regression suite passed on commit `04a7de5`.
- A complete Opportunity/Case system still requires chain confirmation, TSETMC/base-share confirmation, FindChart, Red Team, persistence/novelty, routing, attention allocation and lifecycle memory.


## Chain Intelligence Shadow — 2026-09-21

- Engine: `CHAIN-SHADOW-1.0`.
- State: `SHADOW_ACTIVE_NON_BLOCKING`.
- Chain identity requires explicit underlying + expiry + strike fields.
- Contract type is consumed only when an explicit type field exists.
- Option-symbol parsing is intentionally disabled.
- Validated chains can emit `CHAIN_STRUCTURE_ANOMALY` when member score dispersion reaches 20 points.
- No chain case changes FinalScore, ranking, or Bale output.


## Cross-Chain Intelligence Shadow — 2026-09-21

- Chain engine upgraded to `CHAIN-SHADOW-1.1`.
- Full chain identity is Underlying + Expiry; Strike is a structural member.
- `CHAIN_STRUCTURE_ANOMALY` uses cross-contract score dispersion only as a discovery trigger.
- `CALL_PUT_STRUCTURE_AVAILABLE` requires explicit CALL and PUT fields at a common strike.
- No option type is inferred from symbol naming.
- Cross-chain cases remain non-blocking and do not modify FinalScore, Ranking or Bale output.


## Relative Value Evidence Shadow — 2026-09-21

- Engine: `RELATIVE-VALUE-SHADOW-1.1`.
- Explicit CALL/PUT common-strike pairs are compared using observed fields only.
- Adjacent explicit strikes are included as contextual evidence when available.
- No synthetic IV, rate, dividend, price, or parity value is generated.
- No parity mispricing is declared without validated economic inputs.
- Layer remains non-blocking and does not alter FinalScore, Ranking or Bale output.


## Case Explanation Shadow — 2026-09-21

- Engine: `CASE-EXPLANATION-SHADOW-1.0`.
- Evidence is classified into OBSERVED, EXPLAINED, UNEXPLAINED, DATA_GAP and RED_TEAM_CHALLENGE.
- EXPLAINED is limited to mechanical derivation; no economic causality or trade direction is inferred.
- Layer is non-blocking and does not modify FinalScore, Ranking or Bale output.
- Regression coverage added for traceability, data gaps and Red Team challenge propagation.
- GitHub CI for the latest fix is the authoritative validation gate; Termux deployment remains unverified.


## Evidence Matrix Integration — 2026-09-21

- Case Explanation Shadow is now invoked by Opportunity Shadow after Red Team review.
- The complete explanation artifact is returned under `case_explanations` in the Opportunity result.
- Original Case status and FinalScore remain immutable.
- Integration regression test added for audit-path presence and score non-mutation.


## Source Schema Audit — 2026-09-21

- Engine: SCHEMA-AUDIT-1.0.
- A dedicated evidence-only schema audit was added.
- It records explicit Underlying, Contract Type, Expiry and Strike availability using controlled aliases.
- Symbol parsing remains disabled; missing explicit identity stays INSUFFICIENT_DATA.
- Economic parity readiness remains blocked until identity and economic inputs are separately validated.
- Synthetic regression coverage was added for explicit fields, missing identity and alias normalization.
- This is a repository-level schema readiness test. It is not evidence that the current live OptionSchool24 workbook contains the explicit identity fields.


## Real Source Schema Evidence — 2026-09-21

Archived workbook inspected from the project Library: `optionschool24_all_1788105478761.xlsx` (created 2026-08-30).

Observed source schema on `sheet1`:
- Explicit: `نماد`, `قیمت اعمال`, `تاریخ سررسید`, `وضعیت`, `اهرم`, `نوسان ضمنی`, Greeks and market/liquidity fields.
- Not explicit: Underlying / `نماد سهم پایه`.
- Not explicit: Contract Type / `نوع قرارداد`.
- Consequence: Chain identity cannot be considered ready from this source without symbol inference, and symbol inference remains disabled.
- Result for this archived source: identity readiness = `INSUFFICIENT_DATA`; contract type readiness = `INSUFFICIENT_DATA`.
- The source contains option symbols whose prefixes visually distinguish contracts, but that naming convention is not accepted as chain-direction evidence.
- This evidence belongs to the archived workbook and does not establish the schema of a fresh live download on 2026-09-21.
