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
