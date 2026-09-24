# OptimusAI V4.1.1 — Project Status

## Active runtime
The active report path is TSETMC-only.

- `report_engine.py` reads no workbook and has no OptionSchool24 runtime dependency.
- `tsetmc_first_source.py` is the canonical source builder.
- `tsetmc_adapter.py` is the TSETMC evidence boundary.
- `bale_listener.py` distributes the TSETMC report; Bale is not an analysis engine.

## Source-of-truth rule
TSETMC Option Market-Watch is the active universe and identity boundary. Explicit TSETMC instrument IDs are required. No symbol-prefix inference is promoted to identity.

Historical OptionSchool24 files and prior reconciliation artifacts remain archival evidence only. They are not consumed by the active source engine and are not used to fill missing TSETMC fields.

## Benchmark boundary
FindChart is not an active data, reconciliation, identity, scoring or signal source. Its permitted role is limited to UX/distribution reference. The formal boundary is documented in `docs/FINDCHART_BENCHMARK_ASSESSMENT_V41.md`.

## BestLimits evidence gate
The candidate semantic mapping of `zo/zd/pd/po/qd/qo` is independently corroborated by third-party references, but it is not frozen as a production adapter contract.

The isolated capture design is implemented in `live_capture_harness.py`. It captures raw TSETMC BestLimits evidence without importing the project adapter or scoring path.

Current status:
- semantic mapping: INDEPENDENTLY_CORROBORATED / LIVE_VALIDATION_PENDING
- production mapping freeze: BLOCKED
- BestLimits-derived scoring input: BLOCKED
- live market capture: NOT CLAIMED
- evidence package validator: IMPLEMENTED
- payload SHA integrity check: IMPLEMENTED
- structured independent-evidence reference check: IMPLEMENTED
- deterministic capture/evidence time-window check: IMPLEMENTED
- validator regression tests: PRESENT (execution not claimed)

Structural invariants such as `po >= pd` and non-negative quantities/counts are rejection tests only; they cannot independently prove field identity.

## Current scoring state
Six-Block scoring and production ranking remain OFF while the TSETMC field-evidence gate is open. Missing evidence is represented as «داده موجود نیست».

## Next controlled gates
1. Execute isolated live BestLimits captures against explicitly identified instruments.
2. Preserve complete raw payload, extracted raw levels, endpoint, instrument ID, UTC capture times and SHA-256 for each capture.
3. Pair every captured observation with an independently established semantic-evidence reference within a deterministic 2-second window of the capture timestamp; the exact same second is not required because independent capture introduces transport/observation latency.
4. Run regression across normal, one-sided and zero-depth observations where actually observed.
5. Freeze `BestLimitsAdapter` only after the evidence chain passes review.
6. Verify contract specification and open-interest evidence.
7. Freeze calendar/trading-day, intrinsic, breakeven, leverage and model conventions.
8. Derive model fields only from supported TSETMC inputs.
9. Re-enable Six-Block scoring only after all required evidence gates pass.
10. Reconnect Opportunity, Replay, Audit and Bale to the TSETMC-only canonical dataset.

No Buy/Sell signal is emitted during this evidence-only phase.

## Runtime verification
Repository inspection alone is not runtime evidence. Termux execution, source freshness and Bale delivery must be reverified on the deployed commit after cutover changes.

The repository now contains a mocked regression test for the capture harness, but no live-market capture artifact is being represented as completed by repository changes alone.
