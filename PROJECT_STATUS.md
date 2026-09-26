# OptimusAI V4.1.1 — Project Status

## Active runtime

مسیر فعال گزارش‌دهی TSETMC-only است.

- report_engine.py از Workbook استفاده نمی‌کند.
- tsetmc_first_source.py منبع Canonical است.
- tsetmc_adapter.py مرز Evidence منبع TSETMC است.
- Bale فقط Distribution Layer است.
- Bale report commands use the full TSETMC option universe (flow=None).

## Current live runtime evidence

آخرین اجرای واقعی Bale گزارش کرده است:

- TSETMC records discovered: 1582
- flows checked: 4
- OPPORTUNITY_CANDIDATE: 746
- Ranking-Evidence-Rows: 746
- Eligibility: PASS
- Opportunity Engine: SUCCESS
- Six-Block Ranking: PASS
- Data Mode: LIVE_TSETMC_REFRESH
- Live Refresh: SUCCESS
- Market/Report session: OFFMARKET
- latest explicit source timestamp: 2026-09-26T12:29:59
- Snapshot SHA: 8e97d6f2052f80aed87c302032ec72342cda0056ff2874d4e64415a73b6895cf

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

1. Implement deterministic Shadow Signal Engine.
2. Define/version Strategy entry policy.
3. Define/version Risk policy.
4. Define expiry, freshness and missing-evidence policies.
5. Add deterministic regression and replay/golden cases.
6. Run historical sensitivity/ablation and economic validation.
7. Close Signal Gate / Gate 7.
8. Only then enable production BUY/SELL delivery through Bale.

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
- Signal Engine: SPECIFIED / PENDING IMPLEMENTATION
- Strategy policy: PENDING
- Risk policy: PENDING
- Economic validation: OPEN

No guessed economic parameter is authorized.
