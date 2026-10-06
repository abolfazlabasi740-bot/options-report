# OptimusAI V4.1.1 — Project Status

## Active runtime

مسیر فعال گزارش‌دهی TSETMC-only است.

- report_engine.py از Workbook استفاده نمی‌کند.
- tsetmc_first_source.py منبع Canonical است.
- tsetmc_adapter.py مرز Evidence منبع TSETMC است.
- Bale فقط Distribution Layer است.
- Bale report commands use the full TSETMC option universe (flow=None).

## Current live runtime evidence

آخرین Evidence واقعی منتشرشده در شاخه runtime-evidence:

- Published at: 2026-10-01T05:52:30.090099+00:00
- TSETMC records discovered: 1684
- OPPORTUNITY_CANDIDATE: 740
- Ranking-Evidence-Rows: 740
- Eligibility: PASS
- Opportunity Engine: SUCCESS
- Economic Scoring: TSETMC_ECONOMIC_SCORING / PASS
- Data Mode: LIVE_TSETMC_REFRESH
- Live Refresh: SUCCESS
- Session: OFFMARKET
- Latest explicit source timestamp: 2026-09-30T12:30:02
- Snapshot SHA: c735d0b0f14379cd24a8e462704612f67d7edfde08edfd37e244e787269e178d
- Report SHA: f919ea796cbf25582e194c781f0bef6fdd5aada662632b0c43b2f0644cd6cf83

The OFFMARKET report is explicitly treated as the latest valid TSETMC source state, not as a live movement claim.

## Source of Truth

TSETMC Option Market-Watch is the active source for Universe and Identity.

OptionSchool24 and historical reconciliation paths are not consumed by the active runtime and are not used to fill missing TSETMC fields.

## Identity rule

Option instrument identity and underlying identity must be explicitly supported by TSETMC evidence.

Symbol-prefix inference is prohibited.

## Ranking state

Six-Block Evidence Ranking is active in the current deployed runtime.

Weights:

- LIQUIDITY: 20
- VALUATION: 25
- PAYOFF: 18
- TIME: 15
- GREEKS: 12
- MARKET: 10

Missing evidence remains unavailable and is not converted to zero.

Current ranking does not compute IV or Greeks. Open interest is not used by the current ranking contract.

## Stage 1 status

Stage 1 Operational Report V1 is implemented.

- TSETMC-only full-universe ranking remains active.
- Six-Block Economic Scoring remains unchanged: 20/25/18/15/12/10.
- Stage-1 Underlying Intelligence is integrated as a descriptive layer.
- Global snapshot cache is protected from symbol-filtered report overwrites.
- Invalid post-market captures are rejected; the latest valid TSETMC snapshot is used instead.
- BUY/SELL remains OFF.
- Advanced indicators and adaptive learning are deliberately deferred until Stage 1 reports are reviewed.

## Signal state

The final business objective of OptimusAI is BUY/SELL option signals.

The Signal Engine V1 production contract is now documented in:

docs/SIGNAL_ENGINE_V1_SPEC.md

Current production signal state remains:

buy_sell_signal = NOT_GENERATED

This is a controlled boundary, not the final project objective.

BUY/SELL production requires an explicit Strategy policy, Risk policy, Decision Trace, Signal Gate and Gate 7 release evidence.

No undocumented score threshold may be used to convert Ranking into BUY or SELL.

BUY and SELL are not mirror labels. Short-option SELL_CALL/SELL_PUT requires an independently approved short-option risk policy.

## Signal Engine V1 cutover sequence

1. Implement deterministic Shadow Signal Engine. [DONE]
2. Define/version Strategy entry policy. [DONE — V1 SHADOW_ONLY]
3. Define/version Risk policy. [DONE — V1 SHADOW_ONLY]
4. Build historical TSETMC archive and observed-outcome layer. [DONE]
5. Build deterministic replay/calibration engine. [DONE]
6. Collect distinct intraday observations and run replay/sensitivity/economic validation. [ACTIVE]
7. Close Signal Gate / Gate 7 only after evidence supports a released policy. [PENDING]
8. Enable production BUY/SELL delivery through Bale only after Gate 7. [PENDING]

Until Gate 7 is closed, Shadow signal results must not alter the production report or Bale release.

## Audit / Distribution

Repository, CI, runtime and Bale evidence remain separate evidence classes.

Current deployed runtime has demonstrated:

- Audit: PASS
- Bale report delivery: successful
- Full TSETMC universe path: 4 flows / 1582 records
- Six-Block ranking report delivered through Bale

Audit failure remains release-blocking.

## Project control

- Gate 2: VERIFIED
- Gate 3: VERIFIED
- Gate 4: PENDING — exact TSETMC option identity / enrichment closure where required
- Gate 5: technical Shadow/Replay/Audit verification present; economic validation remains open
- Gate 6: CLOSED — deployed Termux + real Bale evidence
- Gate 7: NOT CLOSED
- Signal Engine: SHADOW IMPLEMENTED / PRODUCTION OFF
- Strategy policy: V1 SHADOW_ONLY
- Risk policy: V1 SHADOW_ONLY
- Historical Replay/Calibration: IMPLEMENTED / EVIDENCE COLLECTION ACTIVE
- Economic validation: OPEN — requires multiple distinct intraday TSETMC observations

No guessed economic parameter is authorized.

## Baseline observation

برای ادامه جمع‌آوری و Walk-Forward Validation، آخرین Snapshot معتبر TSETMC به‌عنوان Observation-0 / Baseline ثبت شده است.

- Baseline Snapshot SHA: 8c3957451456fe3fdad36e714778292f22447bbad227b31b2996f4c0dc05d840
- Observation retrieved at: 2026-09-27T13:59:40Z
- TSETMC rows: 1582
- MarketWatch snapshot SHA: 718187b3ae7f7d0553768b7fcf360430fedc0016633c382ca1369a2b3be655f3
- Baseline status: VALID
- Market-hours status: OFFMARKET

این Snapshot مبنای مقایسه مشاهدات بعدی است و به‌عنوان حرکت لحظه‌ای بازار تفسیر نمی‌شود. مشاهدات بعدی باید با همان منبع TSETMC و شناسه دقیق Instrument نسبت به این Baseline و سپس به‌صورت زنجیره‌ای نسبت به Observation قبلی مقایسه شوند.

## Latest economic validation implementation

- `economic_validation_engine.py` added as `ECONOMIC-VALIDATION-1.0`.
- Uses chronological walk-forward validation only; thresholds are derived from prior-entry observations and never from future observations.
- Uses exact instrument identity and observed forward option return only.
- Transaction costs and slippage remain `NOT_ASSUMED`.
- Signal generation remains `FORBIDDEN`.
- Production BUY/SELL remains OFF pending real distinct intraday observations and Gate 7 evidence.
