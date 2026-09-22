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


## Direct Workbook Schema Inspection — 2026-09-21

The archived real workbook `optionschool24_all_1788105478761.xlsx` was inspected with the spreadsheet workbook reader.

- Sheet: `sheet1`
- Used range: `A1:AL410`
- Header count: 38 columns
- Explicit source fields confirmed: symbol, strike, base price, expiry, days, open interest, volume, trade value, prices, status, leverage, IV/HV, contract size, order-book fields, and Greeks.
- Explicit Underlying / `نماد سهم پایه`: not present.
- Explicit Contract Type / `نوع قرارداد`: not present.
- Therefore Chain Identity readiness remains `INSUFFICIENT_DATA` for this source, and symbol-based CALL/PUT inference remains disabled.

The archived source contains rows such as `ضهرم6047` and `ضهرم7060`. These are preserved only as observed source symbols; their prefixes are not converted into contract-type evidence.


## Live Source Schema Audit Tool — 2026-09-21

- Added `live_schema_audit.py` to download the current OptionSchool24 export and emit schema metadata only.
- Added manual GitHub workflow: `.github/workflows/live-schema-audit.yml`.
- Raw live workbook is not committed by the workflow; only the metadata JSON is uploaded as an artifact.
- The live workflow is intentionally separate from deterministic regression tests.
- In the current execution environment on 2026-09-21, direct DNS access to `s3.optionschool24.com` was unavailable, so no current-live schema claim is made from this environment.
- Archived workbook schema remains verified as: 38 columns on `sheet1`, explicit Strike/Expiry, no explicit Underlying/Contract Type.

## Multi-Source Data Architecture Decision — 2026-09-21

The target FindChart-style intelligence model is explicitly multi-source. OptionSchool24 remains the option-analytics enrichment source, while TSETMC/TSE becomes the market-state, instrument-identity and historical-market source. The Six-Block scoring model is unchanged.

- TSETMC/TSE is planned for canonical instrument identity, option/base-share market data, history, market state, order book and client-type evidence where explicitly available.
- OptionSchool24 remains the source for verified option-specific analytics such as Black-Scholes-related fields, IV/HV, Greeks and breakeven that are already present in its export.
- FindChart-style technical filters, pattern detection, opportunity cases, persistence and novelty will be derived from the merged canonical dataset rather than from a single workbook.
- Historical timestamped snapshots are required for persistence/recurrence and pattern detection.
- Symbol prefixes remain invalid as standalone CALL/PUT evidence.
- No live TSETMC integration is claimed until a real runtime response is captured, normalized and hashed.
- Detailed source responsibilities and implementation sequence are documented in docs/DATA_SOURCE_ARCHITECTURE.md.

This decision supersedes the earlier single-source architecture description for the future Opportunity/FindChart layer; it does not change the active V4.1.1 Six-Block scoring or current Bale report path.

## TSETMC Source Adapter — Current Phase

- Evidence-preserving TSETMC adapter added as `tsetmc_adapter.py`.
- The adapter isolates TSETMC CDN JSON access from scoring and Opportunity engines.
- Supported source boundaries: instrument search, instrument info, instrument identity, current quote, order book, client type, daily history and market overview.
- Successful responses retain endpoint, retrieval timestamp and SHA-256 payload hash.
- Canonical normalization uses TSETMC instrument code as the instrument key.
- Underlying, Contract Type, Strike and Expiry remain unavailable unless explicitly sourced; no symbol-prefix inference is performed.
- Unit coverage was added in `tests/test_tsetmc_adapter.py` for response unwrapping, payload hashing, symbol encoding, soft-block rejection and identity-inference prevention.
- Documentation added at `docs/TSETMC_ADAPTER.md`.
- This is an implementation milestone, not live verification. Termux has not been claimed as updated or tested from this GitHub change.
- Next controlled layer: TSETMC-to-OptionSchool24 mapping with explicit match states and no synthetic identity.


## TSETMC Mapping Gate — Current Phase

- Added `tsetmc_mapping.py` as the controlled source-mapping boundary.
- Mapping states are explicit: EXACT_INSTRUMENT_ID, SYMBOL_ONLY_CANDIDATE, AMBIGUOUS and NO_MATCH.
- Only an explicit instrument identifier match is eligible for promotion into the canonical merged snapshot.
- Symbol-only matches remain candidates and are never silently promoted.
- Added regression coverage for exact, symbol-only, ambiguous and no-match paths.
- Six-Block scoring, FinalScore, Top-N ranking and Bale output remain unchanged.
- Next layer is canonical multi-source snapshot construction from only promoted exact matches plus independently validated OptionSchool24 analytics.


## Canonical Multi-Source Snapshot — 2026-09-21

- Added `canonical_snapshot.py` as the controlled merge boundary between TSETMC and OptionSchool24.
- Only EXACT_INSTRUMENT_ID mappings are promoted.
- SYMBOL_ONLY_CANDIDATE, AMBIGUOUS and NO_MATCH remain outside the promoted canonical dataset.
- TSETMC is preferred for explicitly sourced market-reference fields; OptionSchool24 supplies option analytics and fields not verified from TSETMC.
- Missing fields remain missing; no contract identity is synthesized from symbol naming.
- A deterministic SHA-256 snapshot identifier is generated for the promoted canonical records.
- Added regression tests for exact-only promotion, missing-identity protection and deterministic snapshot identity.
- Six-Block scoring, FinalScore, ranking and Bale output remain untouched.
- Live activation is still blocked pending real Termux TSETMC response evidence and a real merged snapshot.


## Historical Snapshot & Pattern Intelligence — 2026-09-21

- Engine: HIST-SNAPSHOT-1.0.
- Historical snapshots are stored append-only in output/historical_snapshots.jsonl when the report path runs.
- Snapshot records are deterministic and retain source snapshot ID, records hash, source metadata and normalized fields.
- Field-level history diff is persisted to output/latest_historical_diff.json and summarized in latest_audit.json.
- Opportunity Shadow now receives historical context without changing FinalScore, ranking or Case status.
- Engine: HIST-PATTERN-SHADOW-1.0.
- Descriptive historical patterns include consistent field direction sequences, price/volume concordance or divergence, and FinalScore/price alignment or divergence.
- Pattern detection uses an explicit window parameter and does not introduce hidden economic thresholds or trade direction.
- Current report history uses SOURCE_LOCAL_SYMBOL identity because explicit TSETMC instrument IDs are not yet available in the active report path. This is not treated as canonical cross-source identity.

## Base-Share Intelligence Shadow — 2026-09-21

- Engine: BASE-SHARE-SHADOW-1.0.
- Base-share intelligence requires explicit instrument_id.
- Option-to-base linking requires explicit underlying_id.
- No option symbol parsing is used to identify the underlying.
- Live TSETMC/base-share activation remains unverified pending real runtime evidence with endpoint, payload hash and normalized record.

## CI Gate — 2026-09-21

- GitHub Actions regression run 99 completed successfully on commit c1057833ac79d3802b2deaa1dc71301dafc59cf8.
- The failure in earlier runs was traced to an unrelated NameError in live_schema_audit.py and was fixed by removing undefined CLI-argument references from audit_live().
- Current repository regression gate is green after that fix.
- No Termux deployment/restart is claimed from GitHub CI evidence.


## Attention Allocation Shadow — 2026-09-21

- Engine: ATTENTION-SHADOW-1.0.
- Attention allocation is review-routing only and does not rank contracts or create trade direction.
- Red Team challenges route to RED_TEAM_REVIEW before other routes.
- Missing evidence routes to DATA_COMPLETION.
- Confirmed cases with historical patterns route to CROSS_SNAPSHOT_REVIEW.
- Other confirmed/watch cases are routed for evidence review or follow-up only.


## Case Lifecycle & Replay — 2026-09-21

- Engine: CASE-LIFECYCLE-SHADOW-1.0.
- Case lifecycle is persisted as an append-only event stream in output/case_lifecycle_shadow.jsonl when the active report path executes.
- Stable case identity is type::symbol; snapshot-specific case IDs remain retained for traceability.
- States include NEW, PERSISTENT, STRENGTHENING, WEAKENING, RESOLVED and RECURRING.
- Lifecycle events do not change FinalScore, ranking or Bale output.
- Engine: REPLAY-SHADOW-1.0.
- The report path now performs deterministic Shadow replay verification and writes output/latest_replay_verification.json.
- Replay compares canonical fingerprints while excluding only volatile generated_at metadata.
- Replay mismatch is treated as an integrity failure and never as a reason to adjust scores.


## Audit Integrity Gate — 2026-09-21

- Engine: AUDIT-INTEGRITY-1.0.
- Required audit evidence now includes source hash, historical snapshot identity/hash, Opportunity snapshot identity and replay verification.
- Historical and Opportunity snapshot IDs must agree.
- Replay must be REPLAY_MATCH and deterministic.
- The active report path fails closed before publishing latest_audit.json when the integrity gate fails.
- This gate validates evidence integrity only; it never adjusts scoring or ranking.


## Market Feature & Filter Shadow — 2026-09-21

- Engine: MARKET-FEATURE-SHADOW-1.0.
- Technical features operate only on explicit market-history bars and require explicit moving-average windows.
- Current primitives include return, high-low range, volume change, directional sequences, simple moving averages and close-vs-average relations.
- No default technical window or economic threshold is introduced.
- Engine: FILTER-SHADOW-1.0.
- Filters are rule-configurable with explicit operators and nested field paths.
- Missing values produce INSUFFICIENT_DATA rather than an invented zero.
- Filter results are analytical evidence only and are not connected to FinalScore or trading direction.

## TSETMC Live Smoke Path — 2026-09-21

- Added `tsetmc_live_smoke.py` and manual workflow `.github/workflows/tsetmc-live-smoke.yml`.
- The smoke test records source endpoint, retrieval time and payload SHA-256 for the TSETMC market-overview boundary.
- This workflow is separate from regression CI and does not modify scoring/ranking.
- No live smoke execution is claimed from this environment; Termux runtime evidence remains a separate gate.


## Termux Runtime Verification Gate — 2026-09-21

- Added `runtime_verification.py` and `docs/TERMUX_RUNTIME_GATE.md`.
- The gate checks critical source-file presence, Python compilation, repository SHA when available, presence-only environment flags and latest Audit Integrity evidence.
- Secret values are never recorded; environment checks are boolean-only.
- A PASS from this script is runtime evidence only when executed on the target Termux instance. No Termux execution is claimed from GitHub.


## Legacy Runtime Boundary Audit — 2026-09-21

- Confirmed legacy `score_v3()` remains inside the existing scoring chain as the baseline scoring primitive; no deletion or replacement was made.
- V4.1 Shadow intelligence layers remain observational and do not alter FinalScore or ranking.
- No unverified legacy file was promoted into the new multi-source canonical path.
- Current release gate remains: repository tests + deterministic replay + audit integrity + target Termux runtime evidence.


## Shadow Configuration Hardening — 2026-09-21

- Added `opportunity_config.py` as the single explicit configuration boundary for Shadow discovery thresholds and historical pattern window.
- Existing Shadow threshold values were not changed; they are now externally visible, validated and auditable.
- `opportunity_engine.py` no longer owns hidden literal discovery thresholds.
- `HISTORICAL_PATTERN_WINDOW` is now explicit configuration rather than an inline engine constant.
- Configuration changes remain outside FinalScore/Ranking unless a separate documented scoring change is made.


## Eligibility Separation — 2026-09-21

- Added `eligibility_shadow.py` with engine `ELIGIBILITY-SHADOW-1.0`.
- The layer classifies each scored row without changing FinalScore, ranking or the production report gate.
- Explicit states include: `ACTIVE_ELIGIBLE`, `EXPIRED`, `INVALID_MARKET_DATA`, `UNSCORABLE`, `MISSING_REMAINING_DAYS`, `LEVERAGE_UNAVAILABLE` and `LEVERAGE_LOW`.
- Expired contracts are now distinguishable from invalid data and remain available to Shadow/history evidence; they are not treated as active opportunities.
- Missing or low leverage is classified explicitly rather than silently converted to zero or conflated with expiry.
- Opportunity Shadow now attaches eligibility evidence to cases and reports eligibility counts, while continuing to scan the full scored universe.
- The existing production leverage reference remains 3.5 and is now exposed as `PRODUCTION_MIN_LEVERAGE_REFERENCE`; this is a reference only and does not change the active Six-Block gate.
- No production eligibility rule was removed or relaxed in this change.
- Regression tests added for active, expired, missing-leverage, low-leverage, missing-days and invalid-market-data paths.
- GitHub Actions evidence for the latest commit is not yet available; no CI pass is claimed from repository state alone.

## Next Architecture Gate

The next controlled change is to evaluate whether production Eligibility should remain a hard pre-score gate or become a separate production quality gate. That decision will be made only after replay/regression comparison on real and synthetic evidence; no FinalScore/ranking change is active yet.


## Production Eligibility Gate Trace — 2026-09-21

- The active production path was audited and confirmed to apply eligibility twice: first inside `score_dataframe()`, then again in `report_engine.build_report()`.
- Existing hard conditions remain unchanged: positive required market fields, `RemainingDays > 0`, and `اهرم >= MIN_LEVERAGE` with the current reference 3.5.
- `scoring_engine.py` now exposes an evidence-only `eligibility_gate_counts` trace and the active production rules in result attributes. No gate was relaxed.
- `report_engine.py` now classifies the raw normalized source universe before production scoring, so expired and leverage-data states can be audited even when production scoring excludes them.
- Source eligibility evidence is carried into the audit artifact through report attributes.
- This is a measurement layer, not a scoring change. FinalScore, Ranking, Top-N and Bale output remain unchanged.
- The next decision gate is now data-driven: compare the raw-source eligibility population against the scored population on a real workbook before considering any production Gate redesign.


## Opportunity Universe Separation — 2026-09-21

- Added a non-scoring `opportunity_universe()` view to `eligibility_shadow.py`.
- The raw normalized source universe is now explicitly retained for Opportunity/Audit review before production scoring gates.
- Rows are never assigned a synthetic FinalScore or opportunity status by this layer.
- Rows are classified as production-eligible versus production-gated/incomplete while retaining the detailed eligibility reason.
- Invalid market rows are excluded from the opportunity-candidate population; expired, missing-leverage and low-leverage rows remain visible as evidence candidates but are not silently promoted into the production ranking.
- `report_engine.py` now carries the full opportunity-universe summary in report attributes/audit context.
- FinalScore, Six-Block scoring, Ranking, Top-N and Bale output remain unchanged.
- This establishes the required separation: Opportunity Universe discovery can see the full source population, while Production Ranking continues to use the existing hard eligibility gate.


## Gate-Free Shadow Scoring — 2026-09-21

- Added `shadow_score_dataframe()` to `scoring_engine.py`.
- Shadow scoring reuses the exact existing `add_analytics → score_v3 → score_v4_overlay` path and removes only the production eligibility gate.
- No alternate scoring formula, new weight, synthetic value, or guessed parameter was introduced.
- `report_engine.py` now calculates Shadow scores for the full normalized source universe and passes that universe to Opportunity Engine.
- Production `score_dataframe()` remains unchanged in its eligibility behavior and continues to feed Ranking/Top-N/Bale.
- Expired contracts remain visible to Shadow for evidence/history, but contract-level opportunity cases are explicitly rejected as active opportunities; expiry-risk cases remain visible.
- Missing/low leverage rows remain inspectable in Shadow and are classified through Eligibility Shadow rather than silently disappearing.
- Added regression coverage for gate-free Shadow scoring and expired-contract separation.
- CI status for these latest commits has not been claimed here because no associated workflow run was returned by the GitHub workflow lookup; target Termux execution has also not been claimed.


## Shadow Scoring Missing-Data Hardening — 2026-09-21

- `shadow_score_dataframe()` now tolerates missing scoring columns by preserving them as NaN.
- Missing leverage is therefore retained as missing evidence instead of causing the entire Shadow path to fail.
- No missing market field is converted to zero or a synthetic neutral value.
- The same production scoring primitives remain reused; only the production eligibility gate is bypassed in Shadow.
- Regression coverage now explicitly verifies a source row with no leverage column can still pass through Shadow Scoring with leverage remaining missing.


## Explicit Underlying–Breakeven Context — 2026-09-21

- Added optional `BASE_BREAKEVEN_CONTEXT` evidence in Opportunity Engine.
- It activates only when explicit `underlying_last_price` and `underlying_close_price` fields are present.
- It records the actual underlying return, signed breakeven distance and their sign relationship.
- It does not infer CALL/PUT from symbols and does not classify the relationship as a buy/sell signal.
- Current OptionSchool24 input does not automatically receive these fields; therefore no live opportunity is claimed from this detector until the underlying fields are actually sourced and evidenced.
- Added regression coverage for explicit negative underlying return with negative breakeven distance.


## Explicit Underlying Context Enrichment — 2026-09-21

- Added `underlying_context_shadow.py`, engine `UNDERLYING-CONTEXT-SHADOW-1.0`.
- Underlying market data is attached only through an explicit option `underlying_id` → TSETMC `instrument_id` relationship.
- Symbol matching, symbol-prefix parsing and inferred underlying identity are disabled.
- Duplicate underlying identifiers are marked `AMBIGUOUS` and are never silently overwritten.
- Missing identifiers, missing prices, invalid prices and ambiguous identifiers remain `INSUFFICIENT_DATA`/evidence states.
- Source endpoint, retrieval timestamp and payload SHA-256 are preserved when supplied by the TSETMC record.
- The resulting `underlying_last_price` and `underlying_close_price` fields are now ready to feed the existing `BASE_BREAKEVEN_CONTEXT` detector without changing Six-Block scoring.
- Added regression coverage for exact mapping, missing identity, ambiguity, source-reference preservation and rejection of records without explicit instrument identifiers.
- This is a library-level Shadow enrichment milestone. It is not evidence of live TSETMC data or Termux execution.
- Production FinalScore, Ranking, Top-N and Bale output remain unchanged.



## Canonical Underlying Readiness Integration — 2026-09-21

- Canonical snapshot now exposes `underlying_source_status`.
- Exact TSETMC records with an explicit `underlying_id` are marked `EXPLICIT_ID_AVAILABLE`; otherwise the state remains `INSUFFICIENT_DATA`.
- This field is evidence/readiness metadata only and does not infer identity or change scoring.
- The underlying-context Shadow layer is therefore positioned directly after canonical promotion and before Opportunity contextual analysis.
- Report Engine production scoring/ranking remains unchanged.
- Remaining integration gate: feed a real canonical TSETMC snapshot into Report Engine and persist the underlying enrichment/audit artifact; this requires actual source/runtime evidence and is not yet claimed.




## TSETMC Evidence Collector & Underlying Context — 2026-09-22

- Added `tsetmc_evidence_collector.py`, engine `TSETMC-EVIDENCE-COLLECTOR-1.0`.
- The collector accepts explicit option instrument IDs only.
- It reads an explicit `underlying_id/underlyingId` from the option identity response and then requests the underlying quote by that exact instrument ID.
- Symbol search, symbol-prefix parsing and inferred CALL/PUT semantics are not used.
- Every successful source response retains endpoint, retrieval timestamp and payload SHA-256 through the adapter evidence structure.
- Missing underlying identity, insufficient quote data and source failure remain explicit evidence states; no zero-filling is performed.
- Added `tsetmc_shadow_integration.py`, engine `TSETMC-SHADOW-INTEGRATION-1.0`.
- The integration is disabled by default and can be enabled with `TSETMC_EVIDENCE_ENABLED=1`; it only enriches the Shadow universe and does not change Six-Block scoring, production eligibility, ranking or Bale output.
- If an explicit option instrument-ID column is absent, the integration returns `NO_EXPLICIT_OPTION_ID` and does not infer identity from the option symbol.
- Explicit underlying last/close prices are attached to Shadow rows when available, enabling the existing `BASE_BREAKEVEN_CONTEXT` detector to operate on real source evidence.
- Corrected a critical identity-safety issue in `tsetmc_adapter.py`: the option's own `insCode` is no longer accepted as `underlying_id` when an explicit underlying field is absent.
- Regression coverage added for exact option→underlying mapping, missing identity, insufficient quote data, duplicate IDs, disabled integration, no-option-ID protection and the corrected no-inference rule.
- This phase is code/test architecture only. No live TSETMC response or Termux deployment is claimed from these repository changes.
- Production scoring remains unchanged.



## Canonical Underlying Quote Readiness & Audit Integration — 2026-09-22

- Canonical Snapshot now distinguishes `underlying_source_status` (explicit identity availability) from `underlying_quote_status` (actual base-price context availability).
- Default canonical quote state is `NOT_ATTACHED`; identity availability alone is no longer treated as price-context availability.
- TSETMC Shadow evidence metadata is now persisted into `latest_audit.json`.
- Audit Integrity validates the optional TSETMC evidence structure without making TSETMC availability a production scoring dependency.
- Production scoring/ranking remains unchanged and network-independent by default.
- Regression coverage was extended to prevent conflating explicit underlying identity with an attached underlying quote.
- Repository CI status for the latest changes has not been observed; no CI PASS or Termux deployment is claimed.



## Opportunity Intelligence Evidence Graph — 2026-09-22

- Added `evidence_graph_shadow.py`, engine `EVIDENCE-GRAPH-SHADOW-1.0`.
- The graph connects each Shadow case to its observed evidence, historical descriptive patterns and explicit Red Team challenges.
- Each evidence node retains its upstream source label; no causal explanation or trade direction is added by the graph.
- A deterministic `graph_sha256` is generated for the complete graph.
- Opportunity Engine now returns the Evidence Graph alongside existing cases, explanations and attention allocation.
- This is an evidence/audit layer only. It does not modify FinalScore, Six-Block weights, Production eligibility, ranking or Bale output.
- The graph is designed to support later multi-family opportunity detection by proving which independent evidence families contributed to attention without turning that evidence into a hidden score.


## Multi-Factor Opportunity Evidence Cluster — 2026-09-22

- Added `opportunity_evidence_cluster.py`, engine `OPPORTUNITY-CLUSTER-SHADOW-1.0`.
- The detector aggregates already-observed evidence into independent evidence families without introducing a new FinalScore or ranking layer.
- Explicit families include Relative Value, Breakeven, Base Context, Liquidity/Execution, Chain Structure and Time Risk.
- Two independent families produce `MULTI_FAMILY_WATCH`; three or more produce `MULTI_FAMILY_CONFIRMED`. These are evidence classifications, not trade recommendations.
- Historical patterns and Red Team challenges remain attached to the cluster; contradictory evidence is preserved rather than netted away.
- Missing evidence remains a data gap and is never converted to zero or neutral evidence.
- Expired non-risk cases cannot form an active multi-factor cluster; expiry-risk evidence remains observable.
- Each cluster has deterministic `cluster_sha256`; the aggregate also has `clusters_sha256`.
- Opportunity Engine now exposes the Evidence Graph and Multi-Factor Evidence Clusters together in Shadow output and reports cluster counts in the summary.
- FinalScore, Six-Block weights, Production Eligibility, Ranking, Top-N and Bale output remain unchanged.
- Regression coverage added for independent-family detection, single-family rejection, contradiction retention, missing-data handling, deterministic hashing, expiry separation and input immutability.
- This is an architecture/test milestone. No live Termux execution or CI PASS is claimed by the code commits alone.


## Standalone Equity Intelligence Shadow — 2026-09-22

- Added `equity_intelligence_shadow.py`, engine `EQUITY-INTELLIGENCE-SHADOW-1.0`.
- Equity monitoring is now defined as a separate analysis mode: `EQUITY_ONLY`; it does not require option-specific fields and does not alter the existing Six-Block option scoring path.
- Evidence families: Price Structure, Liquidity, Price/Volume, Flow, Market Relative and Historical Pattern.
- Equity identity requires an explicit instrument identifier (`instrument_id` / TSETMC `insCode` aliases). Symbol text is never used to infer identity.
- Missing fields remain `INSUFFICIENT_DATA`; no zero-filling or hidden thresholds are introduced.
- Output is deterministic and audit-oriented. Direction inference and score changes are explicitly disabled.
- Added regression coverage for standalone observation, identity safety, missing-data handling, deterministic output and score/direction separation.
- This milestone establishes Equity Intelligence as a parallel capability. Production Option Ranking and Bale output are unchanged; orchestration integration remains a separate gate requiring real-data validation.


## Equity Evidence Graph & Multi-Factor Cluster — 2026-09-22

- Added `equity_evidence_cluster_shadow.py`, engine `EQUITY-CLUSTER-SHADOW-1.0`.
- Standalone equity cases with at least two independently observed evidence families can be grouped into a deterministic evidence cluster; this is not a score or trade signal.
- Added `EQUITY-EVIDENCE-GRAPH-SHADOW-1.0` inside the Equity Intelligence layer. The graph connects equity cases to explicit evidence, historical context and Red Team challenges.
- Equity clustering and graph generation are now attached to the standalone Equity Intelligence output as Shadow artifacts.
- Direction inference and score changes remain disabled; missing evidence is retained as incomplete evidence.
- Option Evidence Graph/Cluster engines and the Six-Block option scoring path are not modified by this integration.
- Regression tests were added for multi-family equity clustering, single-family rejection and deterministic hashing.
- This remains a Shadow architecture milestone. No production stock ranking, no option ranking change, no Bale production change, and no Termux live execution are claimed.


## Equity Opportunity Detector Shadow — 2026-09-22

- Added `equity_opportunity_shadow.py`, engine `EQUITY-OPPORTUNITY-SHADOW-1.0`.
- Equity opportunity discovery consumes only already-observed multi-family evidence clusters for the same explicit equity instrument.
- At least two independently observed evidence families are required; single-family or incomplete evidence cannot create an opportunity candidate.
- Candidate types are descriptive context classifications; no hidden numeric threshold was introduced.
- Each candidate retains supporting cases, evidence families, cluster identity, historical context and Red Team challenges.
- Status is `WATCH`; the detector does not issue Buy/Sell instructions, directional conclusions, FinalScore changes or ranking changes.
- Missing evidence is never converted to zero or neutral evidence. Explicit benchmark fields remain mandatory for market-relative evidence.
- Deterministic `opportunity_id`, `opportunity_sha256` and aggregate `opportunities_sha256` are generated.
- Standalone Equity Intelligence now exposes the opportunity detector output alongside its evidence graph and multi-factor clusters.
- Regression tests were added for multi-family detection, single-family rejection, missing-data handling, descriptive price/volume evidence, explicit benchmark requirements and deterministic output.
- This remains a Shadow milestone. No production stock ranking, option ranking, Bale output or Termux live execution is changed or claimed.


## Equity Opportunity Lifecycle & Cross-Snapshot Memory — 2026-09-22

- Added `equity_opportunity_lifecycle_shadow.py`, engine `EQUITY-LIFECYCLE-SHADOW-1.0`.
- Equity opportunities now have a stable cross-snapshot identity based on explicit instrument ID, opportunity type and evidence-family set.
- Lifecycle states: `NEW`, `PERSISTENT`, `STRENGTHENING`, `WEAKENING`, `RECURRING`, `RESOLVED`.
- The lifecycle is append-only JSONL evidence and never changes FinalScore, ranking or opportunity classification.
- A disappeared opportunity is marked `RESOLVED`; if the same stable opportunity identity later reappears it is marked `RECURRING`.
- Changes in the explicit opportunity status are recorded as strengthening or weakening; unchanged status is persistent.
- Lifecycle persistence is optional and requires an explicit path. Without a path the detector reports `NOT_PERSISTED` rather than silently writing to an unknown location.
- Deterministic event hashing is retained for audit/replay.
- Regression coverage was added for new→persistent, resolve→recur, strength transition and explicit identity separation.
- No production stock ranking, option ranking, Bale output or Termux execution is changed or claimed.


## Equity Cross-Snapshot Pattern Intelligence — 2026-09-22

- Added `equity_pattern_shadow.py`, engine `EQUITY-PATTERN-SHADOW-1.0`.
- It analyzes append-only Equity opportunity lifecycle events across snapshots.
- A pattern requires at least two observations of the same stable opportunity identity.
- Descriptive pattern classes include repeated observation, recurring pattern, oscillating pattern, and persistent/strengthening pattern.
- Resolved snapshots are retained as historical evidence and are not silently treated as missing observations.
- The engine reports observed states, transitions, snapshots, evidence families and recurrence counts.
- No causal conclusion, directional inference, score modification or ranking change is produced.
- Deterministic `patterns_sha256` is generated.
- Regression tests cover repeated patterns, recurrence, minimum observation requirements, determinism and direction/score isolation.
- Integration into runtime orchestration remains deliberately separate until explicit lifecycle persistence is supplied; no live execution is claimed.


## Equity Opportunity → Lifecycle → Cross-Snapshot Integration — 2026-09-22

- Equity opportunity detection now accepts an optional explicit `lifecycle_path`.
- When supplied, detected opportunities are persisted through `EQUITY-LIFECYCLE-SHADOW-1.0`.
- The same append-only lifecycle evidence is then analyzed by `EQUITY-PATTERN-SHADOW-1.0`.
- Cross-snapshot patterns are exposed as Shadow evidence only; they do not modify FinalScore, ranking, direction, or production decisions.
- When no lifecycle path is supplied, the result explicitly reports `NOT_PERSISTED`; no default filesystem path is assumed.
- `analyze_equities()` now exposes the same optional lifecycle path and passes it through to the opportunity detector.
- This creates the intended evidence chain: Equity evidence → multi-family cluster → opportunity → lifecycle memory → cross-snapshot pattern.
- No Termux live execution, CI pass, or production ranking change is claimed by this integration.


## Equity Historical Confirmation Layer — 2026-09-22

- Added `equity_historical_confirmation_shadow.py`, engine `EQUITY-HISTORICAL-CONFIRMATION-SHADOW-1.0`.
- Matching is performed only against the stable lifecycle opportunity identity: explicit instrument ID + opportunity type + sorted evidence-family set.
- A matching cross-snapshot pattern is attached as `REPEATED_EVIDENCE`; otherwise the opportunity explicitly reports `NO_CROSS_SNAPSHOT_CONFIRMATION`.
- Historical confirmation records observation count, recurrence count, first/last snapshot and evidence families.
- Historical confirmation is evidence-only: no Buy/Sell direction, no FinalScore change, no ranking change and no causal inference.
- The opportunity detector now attaches this confirmation when an explicit lifecycle path is supplied.
- This establishes a clean separation between current evidence and historical recurrence evidence.


## Equity Multi-Level Historical Memory — 2026-09-22

- Added `equity_memory_shadow.py`, engine `EQUITY-MEMORY-SHADOW-1.0`.
- Historical confirmation is now classified into explicit evidence-memory levels:
  - `NEW_OR_UNCONFIRMED`
  - `REPEATED`
  - `PERSISTENT_OR_STRENGTHENING`
  - `OSCILLATING`
  - `RECURRING`
- Classification is descriptive and derives only from lifecycle/cross-snapshot evidence already observed.
- The memory layer is attached to Equity opportunities when lifecycle persistence is supplied.
- No hidden economic threshold, causal inference, direction inference, FinalScore change or ranking change is introduced.
- Missing historical evidence remains explicitly unconfirmed; it is never converted to zero evidence.
- Deterministic `memory_sha256` is produced.


## Equity Historical Memory Profiles — 2026-09-22

- Added `equity_memory_profile_shadow.py`, engine `EQUITY-MEMORY-PROFILE-SHADOW-1.0`.
- Historical memory is now summarized per Opportunity as a descriptive profile.
- Profile continuity distinguishes `SINGLE_OR_UNCONFIRMED`, `REPEATED`, and `RECURRING`.
- Profile records preserve observation count, recurrence count, pattern type and first/last snapshot when supplied.
- The profile layer is derived only from existing historical confirmation/memory evidence.
- No economic threshold, causal inference, direction inference, FinalScore modification or ranking change is introduced.
- The Opportunity Engine now exposes `historical_memory_profiles` when lifecycle persistence is active.


## Equity Historical Timeline Integrity — 2026-09-22

- Corrected `equity_pattern_shadow.py` so RESOLVED lifecycle events are preserved in the historical timeline instead of being discarded.
- Patterns now expose `timeline_event_count` and `resolution_count`, while `observation_count` continues to represent active/non-resolved observations.
- Recurrence evidence therefore retains the resolution event that occurred between observations.
- Added regression coverage for NEW → RESOLVED → RECURRING.
- No scoring, ranking, direction inference or causal inference is changed.


## Equity Historical Evidence Fusion — 2026-09-22

- Added `equity_historical_evidence_fusion_shadow.py`, engine `EQUITY-HISTORICAL-EVIDENCE-FUSION-SHADOW-1.0`.
- Current opportunities can now receive a descriptive historical evidence state derived from cross-snapshot confirmation, historical memory and memory continuity.
- States are limited to evidence descriptions such as `NO_HISTORICAL_CONFIRMATION`, `HISTORICAL_CONTEXT_PRESENT`, `REPEATED_HISTORICAL_EVIDENCE`, and `RECURRING_HISTORICAL_EVIDENCE`.
- The layer does not infer direction, causality, Buy/Sell action, FinalScore or ranking.
- Missing evidence is not converted to zero.
- Opportunity Engine integration includes the memory profile on each opportunity and recalculates the final `opportunities_sha256` after all historical enrichment.


## Equity Historical Red Team & Conflict Fusion — 2026-09-22

- Added `equity_historical_redteam_shadow.py`, engine `EQUITY-HISTORICAL-REDTEAM-SHADOW-1.0`.
- Equity lifecycle events now preserve explicit Red Team challenge evidence so historical challenge context is not lost between snapshots.
- The fusion layer compares the current opportunity with prior lifecycle events using the same explicit opportunity identity.
- States are descriptive only: `HISTORICAL_SUPPORT_PRESENT`, `HISTORICAL_CONTRADICTION_PRESENT`, `HISTORICAL_MIXED_EVIDENCE`, `HISTORICAL_DATA_GAP`, `HISTORICAL_NO_MATCH`.
- A historical contradiction is reported only when explicit prior Red Team evidence exists; no contradiction is inferred from price movement, resolution, or disappearance alone.
- Resolved lifecycle events remain historical evidence but are not treated as active support.
- Current and historical Red Team evidence remain attached for audit/review; no evidence is netted into a score.
- Direction inference, causal inference and score changes remain disabled.
- The Equity Opportunity Engine now exposes `historical_redteam_fusion` after historical confirmation/memory enrichment and recomputes `opportunities_sha256`.
- Added regression coverage for no historical match, historical support, mixed historical Red Team evidence and safety isolation.
- No production stock ranking, option ranking, Six-Block scoring, Bale output or Termux runtime behavior is changed by this Shadow layer.
- Repository-side implementation is complete for this phase; runtime/CI execution evidence has not been claimed.


## Stable Opportunity-Key Consolidation — 2026-09-22

- Historical confirmation and historical Red-Team fusion now reuse the canonical `opportunity_key()` helper from `equity_opportunity_lifecycle_shadow.py`.
- This removes duplicated key-construction logic and reduces the risk of identity drift between lifecycle, pattern, confirmation and Red-Team layers.
- No scoring, ranking, direction inference, causal inference or production output is changed.
- This is a deterministic integrity/refactoring milestone; runtime/CI execution evidence is still required before claiming PASS.


## Regression Gate Verified — 2026-09-22

- GitHub Actions regression workflow completed successfully on commit `11497867785503f285d1c899af6f53bf4b57a0e9`.
- Workflow run: `35682261385`; job: `106601525273`; conclusion: SUCCESS.
- Test command executed: `python -m unittest discover -s tests -v`.
- Result: 137 tests ran in 1.783s; all tests passed.
- The run specifically validates the JSON-safe Audit metadata correction introduced immediately before this gate.
- This is CI evidence only; it does not establish Termux deployment, live OptionSchool24 execution, live TSETMC enrichment or current Bale delivery.
- Gate 2 of `docs/GO_LIVE_GATE.md` is now VERIFIED for this commit.


## Historical Opportunity Identity Hardening — 2026-09-22

- Fixed the Equity historical-memory profile attachment so both lifecycle/profile identity keys use the same sorted evidence-family representation.
- Added regression coverage that verifies a persisted Equity opportunity receives its historical memory profile under the canonical identity.
- Historical confirmation and historical Red-Team fusion already reuse the shared lifecycle `opportunity_key()` helper.
- This hardening changes no scoring, ranking, direction inference, causal inference or production output.
- Runtime/CI execution evidence is still pending; repository commits alone are not treated as PASS.


## Live OptionSchool24 Schema Gate — 2026-09-22

- The live OptionSchool24 schema audit was promoted from manual-only dispatch to also run automatically on pushes to main; manual workflow_dispatch remains available.
- Verification commit: 1a95b1d34f4c957ed4da82a361e51fb4c06c2e24.
- Live schema workflow run: 35683941940; job: 106606672001; conclusion: SUCCESS.
- The workflow fetched the live OptionSchool24 export and completed the schema audit successfully.
- Retrieval timestamp: 2026-09-22T03:39:34.323109+00:00.
- Source SHA-256: bdf7278bd3fe091d563f53ebfb58b58665a2ef1cbfda491b48582c5a4bd7fcb9.
- Fresh source observed by the audit: 457 rows and 38 columns.
- Core schema fields including symbol, strike, underlying-price field, expiry, trading days, open interest, volume, trade value, last/close prices, breakeven, Black-Scholes difference, leverage, IV/HV and bid/ask fields were present.
- Identity readiness remains INSUFFICIENT_DATA; contract-type readiness remains INSUFFICIENT_DATA; symbol inference remains DISABLED.
- Economic parity remains NOT_READY_UNTIL_IDENTITY_AND_ECONOMIC_INPUTS_ARE_VALIDATED.
- This is genuine live OptionSchool24 schema evidence, but it is not yet Gate 3 full-report evidence: the report engine still must be executed against this fresh workbook and its row/eligibility/report/audit outputs captured.
- Regression workflow also passed on the same verification commit.
- No live TSETMC enrichment or Termux/Bale runtime evidence is implied by this gate.


## V4.1 Live Gate 3 Verification — 2026-09-22

- Full V4.1 Report Engine was executed successfully against a fresh live OptionSchool24 download in GitHub Actions.
- Verification commit: f9a42f041d61db8a97e58f28cbc208463e585d4b.
- Live workflow run: 35684027740; job: 106606928933; conclusion: SUCCESS.
- Fresh report source file: optionschool_20260922_071052_767703.xlsx.
- Report source SHA-256: 4252022bd88d2452d856c42bfcd65224e1af430161ad3072bacd925cbeb693fc.
- Production selected_count: 15.
- Source universe scanned by Opportunity Shadow: 457 contracts.
- Eligibility counts: ACTIVE_ELIGIBLE=130; LEVERAGE_LOW=327.
- Opportunity Shadow status: SUCCESS; cases_total=1828; confirmed_total=233; watch_total=66; confirmed_risk_total=53.
- Multi-factor cluster count: 73; multi-factor confirmed count: 18.
- Replay status: REPLAY_MATCH; deterministic=true; first_hash and second_hash are identical.
- Audit integrity status: PASS.
- Gate 3 artifact was uploaded successfully as gate3-live-report-evidence, artifact ID 10676111412.
- TSETMC evidence was DISABLED for this live run; therefore this run does not establish Gate 4.
- Gate 3 of docs/GO_LIVE_GATE.md is now VERIFIED for this commit.
- This evidence is GitHub-hosted live-source execution, not Termux deployment evidence and not Bale delivery evidence.


## TSETMC Gate 4 Identity Boundary — 2026-09-22

- Live OptionSchool24 data currently exposes no explicit option instrument-ID field among the accepted TSETMC integration aliases.
- The live schema therefore remains identity-incomplete for exact option→underlying evidence attachment.
- The TSETMC integration correctly refuses symbol-prefix or symbol-only inference; this is an intentional safety boundary, not a failure of the scoring engine.
- The existing mapping layer retains symbol-only matches as SYMBOL_ONLY_CANDIDATE and promotes only explicit instrument-ID matches to EXACT_INSTRUMENT_ID.
- Gate 4 therefore remains pending until the deployed source supplies an explicit option instrument ID, or a separately approved identity source provides an exact instrument-ID mapping that satisfies the existing promotion rules.
- No Six-Block score, ranking, opportunity status or production output is changed by this limitation.


## Current Gate Evidence — 2026-09-22

- Latest main regression run: 35686797029 (run 271), commit 56c99b866ab1aea96731c56221e7805a30a04912, conclusion SUCCESS.
- Latest live-schema run on the same commit: 35686797019 (run 7), conclusion SUCCESS.
- The current live source still does not expose an explicit option instrument ID accepted by the TSETMC integration; Gate 4 remains pending by design.
- Gate 6 remains pending because current Termux/Bale delivery has not been re-verified on the deployed V4.1.1 runtime. Repository evidence and GitHub CI do not substitute for that runtime evidence.
- No Six-Block weights, production eligibility gate, ranking logic, or Bale report content was changed in this step.


## Bale Delivery Hardening — 2026-09-22

- Reviewed the live Bale path: `bale_listener.py` → `report_engine.py` → `bale_transport.py`.
- Fixed the documented all-market command alias: `همه` now follows the same 15-contract path as `گزارش` and `کل`.
- Added regression coverage for Bale message chunk integrity, multi-chunk POST delivery, and fail-closed network errors in `tests/test_bale_transport.py`.
- This hardening does not alter Six-Block scoring, production eligibility, ranking, opportunity detection, or report calculations.
- Gate 6 is still not claimed as VERIFIED: real delivery from the deployed Termux runtime requires runtime evidence and an actual Bale delivery acknowledgement.


## Bale Regression Gate — 2026-09-22

- The Bale transport hardening commit `0588683b877323f702efdc7673d5cf464b8ce37e` passed the full GitHub regression workflow.
- Regression run: `35687931714` (run 278); conclusion: SUCCESS.
- The same commit also passed the live OptionSchool24 schema/report workflow: `35687931728` (run 14); conclusion: SUCCESS.
- Bale transport tests now cover message-content preservation across chunks, multi-chunk POST delivery, and fail-closed handling of network errors.
- The `گزارش`, `همه` and `کل` commands share the same global Top-15 report path.
- This verifies repository/CI behavior only. Gate 6 is still not marked VERIFIED because actual deployed Termux execution and a real Bale delivery acknowledgement have not been captured on this commit.


## Bale Runtime Evidence Tooling — 2026-09-22

- Added `bale_runtime_verification.py` as a one-shot, evidence-preserving delivery verifier.
- It does not run a second analysis engine and does not regenerate data; it sends the existing `output/latest_report.txt` produced by Report Engine.
- Before sending, it requires `latest_audit.json` with `audit_integrity.status=PASS` and explicit source filename/SHA-256.
- On success it writes `output/bale_delivery_verification.json` containing report SHA-256, source SHA-256, audit status, generation time and chunk count.
- Token values are never written to the evidence artifact.
- Runtime verification now also compiles the Bale transport and delivery-verification modules.

## Current CI Verification — 2026-09-22

- Commit: `3ec5da91247aad3e893f75e1006328eba06a1325`.
- Regression workflow run: `35704198322`, job `106669091419`, SUCCESS.
- Regression result: `142 tests`, all passed.
- Live OptionSchool24 workflow run: `35704198237`, job `106669091168`, SUCCESS.
- Live workflow completed schema audit, full V4.1 report, Gate 3 evidence generation and artifact upload successfully on the same commit.
- These CI results verify the new runtime-evidence tooling at repository level; they do not constitute actual Termux/Bale delivery evidence.


## Bale Runtime Evidence Hardening — 2026-09-22

- Regression workflow verified commit `822b30a8908d955ccacb3815901414e4c3ff9b3f`: run `35704668186`, job `106670595740`, SUCCESS.
- Live OptionSchool24 workflow verified the same commit: run `35704668179`, SUCCESS; fresh Gate 3 artifact was uploaded as artifact `10683887197`.
- Bale transport now supports an opt-in receipt mode that records only non-secret `message_id` and `chat_id` returned by Bale.
- `bale_runtime_verification.py` now fails closed if Bale does not return a message receipt and records the receipt in `output/bale_delivery_verification.json` without recording the bot token.
- Default Listener behavior is unchanged: it still returns the chunk count and uses the same Report Engine.
- No Six-Block, FinalScore, ranking, Opportunity Shadow, or production output logic was changed.
- Gate 6 remains pending actual execution of `python3 bale_runtime_verification.py` on the deployed Termux instance with the real Bale environment; GitHub CI cannot substitute for that runtime evidence.
