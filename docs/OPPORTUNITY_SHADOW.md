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
