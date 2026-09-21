# V4.1 Shadow Opportunity Engine

## Purpose

`opportunity_engine.py` is a discovery-only layer. It scans the full V4.1 scored universe and writes auditable cases without changing:

- FinalScore
- Six-Block weights
- Top-N ranking
- Bale message contents

## Case families

### Relative Value Anomaly
Uses the existing cross-sectional `Score_BlackScholesDiff` plus liquidity and data-confidence evidence.

No call/put direction is inferred.

### Breakeven Compression
Uses `Score_BreakevenDistance` and `BreakevenDistancePct`.

This identifies a compact breakeven-distance condition. It does not by itself claim a directional payoff advantage.

### Liquidity Confirmed
Uses `BlockScore_Liquidity` and `ExecutionPenalty`.

The liquidity block is measured on its existing 0–20 scale; the discovery threshold is 75% of that block weight.

### Near Expiry Risk
Uses `RemainingDays <= 10`.

This is a risk case, not an opportunity signal.

## Statuses

- `CONFIRMED`: current evidence satisfies the explicit discovery rule.
- `WATCH`: a discovery condition exists but confirmation is incomplete.
- `REJECTED`: current evidence does not satisfy the condition.
- `INSUFFICIENT_DATA`: required evidence is missing.

## Snapshot / audit

For a real workbook the snapshot identifier is the workbook SHA-256.

For test doubles where no physical workbook exists, a deterministic SHA-256 is generated from a canonical CSV representation of the supplied DataFrame. This fallback is for testability only.

Each successful report writes:

`output/latest_opportunity_shadow.json`

The main audit stores only the Shadow summary and the artifact filename.

## Current limitations

This is intentionally not the final Opportunity Engine.

It does not yet have:

- multi-contract case clustering
- chain-structure confirmation
- TSETMC/base-share market-state confirmation
- FindChart pattern confirmation
- Red Team challenge (now implemented as non-blocking `REDTEAM-SHADOW-1.0`)
- persistence / novelty / recurrence across snapshots
- Case lifecycle memory
- dynamic routing
- attention allocation
- confirmed directional payoff semantics

These layers must be added in Shadow mode before affecting ranking or Bale output.

## Red Team Shadow

Each Opportunity Shadow case is independently challenged for data-quality warnings, confidence weakness, liquidity/execution weakness and near-expiry alternative explanations. A challenge never changes FinalScore or ranking. It is evidence for the future Case/CEO layer.


## Case Memory Shadow

`case_memory_shadow.py` tracks NEW, PERSISTENT, STRENGTHENING, WEAKENING, RESOLVED and RECURRING states for analytical cases. Historical state is audit context only and is never an input to FinalScore or current ranking.


## Chain Identity Shadow

`chain_identity_shadow.py` creates a chain only when the underlying identifier, expiry and strike are explicitly available in the same snapshot. It never parses an option symbol to guess the underlying or Call/Put type.

Validated chains can generate a `CHAIN_STRUCTURE_ANOMALY` review case when member FinalScores have a dispersion of at least 20 points. This threshold is discovery-only and does not modify scoring or ranking.

If explicit identity fields are absent, the row remains `INSUFFICIENT_DATA`; it is not forced into a guessed chain.


## Cross-Chain Structure — 1.1

The chain layer now distinguishes:

- Chain identity: underlying + expiry
- Strike identity: strike within the chain
- Contract identity: chain + strike + explicit CALL/PUT when available

A `CHAIN_STRUCTURE_ANOMALY` is emitted only when a validated full chain contains at least two members and the cross-contract FinalScore dispersion is at least 20 points.

A separate `CALL_PUT_STRUCTURE_AVAILABLE` case is emitted only when explicit CALL and PUT fields exist at a common strike. The system does not infer contract type from the option symbol.

Neither case is a pricing verdict. They are evidence for the later Relative Value / Parity analysis layer.


## Relative Value Evidence — 1.1

For explicit CALL/PUT pairs at a common strike, the shadow layer records paired
observable fields and also compares each side with adjacent explicit strikes
when available. Neighbor comparisons are evidence only; they do not create
synthetic prices, IVs, rates, dividends, or parity values.

A pair remains WATCH/INSUFFICIENT_DATA. No parity mispricing claim is produced
until the required economic inputs and contract specifications are validated.


## Case Explanation Shadow — 2026-09-21

- Engine: `CASE-EXPLANATION-SHADOW-1.0`.
- Purpose: classify existing case evidence as OBSERVED, EXPLAINED, UNEXPLAINED, DATA_GAP or RED_TEAM_CHALLENGE.
- EXPLAINED is restricted to mechanically derived relationships; it does not assert economic causality.
- Missing evidence remains DATA_GAP and is never converted to zero or a negative score.
- Red Team challenges are carried through as RED_TEAM_CHALLENGE without changing the original case status.
- The layer is non-blocking, deterministic and score/ranking neutral.


### Integration

The Opportunity Shadow pipeline now runs Case Explanation immediately after Red Team. The result is exposed as `case_explanations` in the audit object. This is contextual evidence only: it cannot mutate Case status, FinalScore, ranking or delivery output.


## Source Schema Audit in Shadow Artifact

The Opportunity Shadow result now persists the `schema_audit` block and exposes schema readiness in its summary.
This is audit-only. It does not alter FinalScore, ranking, case status, or Bale output.
When explicit Underlying or Contract Type is absent, the result remains `INSUFFICIENT_DATA` and no symbol-based inference is activated.


## Historical Snapshot Integration — 2026-09-21

Opportunity Shadow now accepts explicit historical snapshot context.

historical_snapshot.py provides append-only snapshot storage, deterministic record hashing, field-level deltas, explicit added/removed/changed/unchanged states, and historical case context.

historical_pattern_shadow.py adds descriptive, threshold-free sequence detection from retained history: consistent field direction sequences, price/volume concordance or divergence, and FinalScore/price alignment or divergence.

These classifications are evidence only. They never mutate FinalScore, Top-N ranking, Case status, or Bale output.

The current report path stores history using source-local option symbol identity because an explicit TSETMC instrument identifier is not yet available in the live OptionSchool24 report path. This is explicitly marked as SOURCE_LOCAL_SYMBOL and is not presented as canonical cross-source identity.

## Base-Share Intelligence — 2026-09-21

base_share_intelligence.py is available as a Shadow engine and requires explicit instrument_id.

Option linkage requires explicit underlying_id. Symbol text is not used to attach an option to a base share.

Live activation remains gated on real TSETMC runtime evidence.
