# G7-5 Opportunity Validation Protocol — V4.1

## Status

OPEN — protocol frozen; independent observed labels are still required.

## Purpose

G7-5 must distinguish technical execution of Opportunity Shadow from economic validation. This document freezes the validation contract without introducing new thresholds or labels.

## Case families under validation

| Case type | Current evidence required | Economic claim allowed today |
|---|---|---|
| RELATIVE_VALUE_ANOMALY | Score_BlackScholesDiff, liquidity, DataConfidence | Cross-sectional deviation only; no directional or mispricing conclusion |
| BREAKEVEN_COMPRESSION | Score_BreakevenDistance, BreakevenDistancePct | Compact breakeven condition only |
| LIQUIDITY_CONFIRMED | BlockScore_Liquidity, ExecutionPenalty | Execution/liquidity follow-up only |
| NEAR_EXPIRY_RISK | RemainingDays | Risk flag only |
| BASE_BREAKEVEN_CONTEXT | Explicit underlying last/close + breakeven distance | Contextual alignment only |
| CHAIN_STRUCTURE_ANOMALY | Explicit validated chain identity + member scores | Structural review only |
| CALL_PUT_STRUCTURE_AVAILABLE | Explicit CALL/PUT + common strike | Pair availability only; no parity/mispricing claim |

## Frozen validation rules

1. Validation must use a retained historical/observed snapshot, not a synthetic fixture.
2. The source snapshot must retain its SHA-256 and retrieval/source provenance.
3. Labels must be independent of the FinalScore and Opportunity Shadow output being evaluated.
4. A label may be OBSERVED_CONFIRMED, OBSERVED_NOT_CONFIRMED, or UNRESOLVED.
5. Missing or ambiguous labels remain UNRESOLVED; they are never converted to negative or positive outcomes.
6. False-positive, false-negative, precision/recall and unresolved counts must be retained by case family.
7. No production ranking, FinalScore, eligibility or Bale output may be changed by the validation run.
8. No economic label may be inferred from the same derived feature that created the case.
9. Directional payoff claims remain blocked until contract identity, CALL/PUT semantics and required economic inputs are independently validated.

## Independence boundary

The current Opportunity Shadow is derived from the scored OptionSchool24 dataframe. Therefore its own CONFIRMED/WATCH status is not an independent validation label.

A Golden fixture, replay match, deterministic hash, or CI success is also not economic validation.

## Required evidence package for closure

- physical source file and SHA-256;
- source/retrieval timestamp where available;
- frozen case-definition version;
- independent observed outcome/label;
- label provenance;
- matched case identifier;
- unresolved cases;
- confusion counts by case family;
- deterministic validation artifact SHA-256.

## Closure rule

G7-5 may be marked VERIFIED only after at least one real retained dataset has independently sourced outcome labels for the case family being validated, with unresolved cases explicitly retained and the complete evidence package reproducible.

Until then, Opportunity Shadow remains A2 / discovery-only and cannot authorize production Signal/Buy/Sell behavior.
