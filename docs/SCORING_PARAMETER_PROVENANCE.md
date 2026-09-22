# Scoring Parameter Provenance — OptimusAI V4.1

## Scope

این سند منشأ و وضعیت تأیید پارامترهای مؤثر بر FinalScore را از وزن‌های Six-Block جدا می‌کند.

## Six-Block

وزن‌های Six-Block مرجع فعلی و ثابت پروژه هستند و این ممیزی آن‌ها را تغییر نمی‌دهد:

- Liquidity = 20
- Valuation = 25
- Payoff = 18
- Time = 15
- Greeks = 12
- Market = 10

## Active V4 Overlay Observed in Code

در `scoring_engine.py` تابع `score_v4_overlay()` مقادیر زیر مستقیماً در محاسبه FinalScore استفاده می‌شوند:

- Execution penalty:
  - spread reference = 12.0
  - spread scaling denominator = 28.0
  - intermediate cap = 0.35
  - missing-spread penalty = 0.10
  - final execution cap = 0.45
- Decay penalty:
  - RemainingDays <= 2 → 0.30
  - RemainingDays <= 5 → 0.18
  - RemainingDays <= 10 → 0.08
  - otherwise → 0.00
- Confidence multiplier:
  - lower clip = 0.55
  - upper clip = 1.00
- Leverage score normalization:
  - input leverage is clipped at 12
  - normalized leverage score is clipped at 0.92

## Provenance Status

Repository search and the current project documentation identify the Overlay as an active V4 component, but do not currently provide an explicit approved-source record for the numeric constants listed above.

Therefore:

- The constants are **observed active parameters**, not newly approved parameters.
- This audit does **not** change them.
- No new value is invented in this document.
- The project must not describe these constants as independently validated economic thresholds unless a source/protocol is added.
- Any future change to these constants requires a separate versioned decision, regression comparison and audit evidence.

## Operational Rule

Until parameter provenance is explicitly documented, the current Overlay remains the deployed/reference implementation for reproducibility, while its numeric assumptions remain an open validation item.

This item is separate from the Six-Block weight integrity gate.

## Acceptance Evidence Required

To close this gate, the project should retain at least one authoritative source for each numeric family:

1. approved protocol/specification;
2. explicit signed-off project decision;
3. historical baseline with reproducible rationale and regression evidence.

No parameter should be silently replaced by a model-generated or guessed value.

## Current Status

**OPEN — PROVENANCE VALIDATION**

No scoring code was modified as part of this audit.
