# Live Time-Locked BestLimits Validation — V4.1

Status: DESIGN IMPLEMENTED / LIVE EVIDENCE NOT CAPTURED
Production mapping freeze: BLOCKED
Scoring: BLOCKED

## Critical audit decision

The proposed live-capture step is technically executable, but it does not by itself prove semantic field identity.

A raw BestLimits capture can prove:
- the endpoint responded;
- the instrument ID was explicitly supplied;
- the raw payload and level count were captured;
- retrieval time and payload hash are preserved.

It cannot, by itself, prove that `pd/po/qd/qo/zd/zo` mean Bid/Ask price/quantity/order-count.

Likewise, `po >= pd`, non-negative quantities, and non-negative order counts are structural invariants. They are useful rejection tests, but they are not identification proofs. A wrong mapping can pass those invariants.

## Implemented isolation

`live_capture_harness.py`:
- uses only Python standard library;
- calls TSETMC BestLimits directly;
- does not import `tsetmc_adapter.py`;
- does not import canonical snapshot, feature, scoring, strategy, or signal engines;
- records raw payload, instrument ID, endpoint, UTC capture timestamps, SHA-256 and level count;
- explicitly records mapping as OPEN and scoring as BLOCKED.

This is intentionally a capture/evidence tool, not a semantic adapter.

## What remains necessary

For a real mapping freeze, capture must be collected for multiple explicitly identified instruments and multiple intraday timestamps, including:
1. at least 3 option instruments;
2. at least 1 underlying equity;
3. multiple BestLimits levels where present;
4. ordinary two-sided books;
5. one-sided/zero-depth cases where observed;
6. repeated captures showing field behavior over time.

More importantly, the raw BestLimits observations must be paired with an independently established same-time interpretation. Merely running the invariant tests on the raw capture is insufficient.

## Execution boundary

The repository now contains the executable harness and mocked regression tests. No live market capture is claimed by this commit because repository access is not runtime execution evidence.

Only an actual successful capture artifact with its endpoint, instrument ID, timestamps, SHA-256 and raw levels can move the evidence gate forward.

OptionSchool remains excluded from this validation.
