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

The isolated capture design is implemented in `live_capture_harness.py`. The new `live_bestlimits_evidence_runner.py` builds a TSETMC-only evidence package by discovering explicit option/underlying IDs and capturing BestLimits twice per selected instrument.

Current status:
- semantic mapping: INDEPENDENTLY_CORROBORATED / LIVE_VALIDATION_PENDING
- production mapping freeze: BLOCKED
- BestLimits-derived scoring input: BLOCKED
- live market capture: NOT CLAIMED until the runner is actually executed
- evidence package validator: IMPLEMENTED
- payload SHA integrity check: IMPLEMENTED
- structured independent-evidence reference check: IMPLEMENTED
- semantic evidence type + six-field coverage check: IMPLEMENTED
- option/underlying role-overlap rejection: IMPLEMENTED
- deterministic capture/evidence time-window check: IMPLEMENTED
- validator regression tests: PRESENT (execution not claimed)

Structural invariants such as `po >= pd` and non-negative quantities/counts are rejection tests only; they cannot independently prove field identity.

## Current scoring state
Six-Block scoring and production ranking remain OFF while the TSETMC field-evidence gate is open. Missing evidence is represented as «داده موجود نیست».

## Next controlled gates
1. Execute `live_bestlimits_evidence_runner.py` against the live TSETMC endpoint.
2. Preserve complete raw payload, extracted raw levels, endpoint, instrument ID, UTC capture times and SHA-256 for each capture.
3. Pair every captured observation with an independently established semantic-evidence reference within the current governance correlation window of 2 seconds; this threshold is a controlled validation parameter, not proof of semantic correctness, and must be revalidated against live capture latency.
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

The repository contains regression tests for the capture harness, but no live-market capture artifact is represented as completed by repository changes alone.

## Latest controlled change
Added a fail-closed TSETMC-only live evidence runner. It performs explicit identity discovery, two time-separated BestLimits captures per selected option/underlying, preserves raw evidence and hashes, and runs the evidence validator. It does not interpret BestLimits fields and cannot unlock scoring.

Latest implementation commit: ed3ec65a0d3df9e762882526b3853d9b2b36bdef.

The blocking gate remains live BestLimits evidence. No scoring or ranking has been re-enabled by this change.
