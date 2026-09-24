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

## Current scoring state
Six-Block scoring and production ranking remain OFF while the TSETMC field-evidence gate is open. Missing evidence is represented as «داده موجود نیست».

## Next controlled gates
1. Verify exact BestLimits mappings.
2. Verify contract specification and open-interest evidence.
3. Freeze calendar/trading-day, intrinsic, breakeven, leverage and model conventions.
4. Derive model fields only from supported TSETMC inputs.
5. Re-enable Six-Block scoring only after the evidence gate passes.
6. Reconnect Opportunity, Replay, Audit and Bale to the TSETMC-only canonical dataset.

No Buy/Sell signal is emitted during this evidence-only phase.

## Runtime verification
Repository inspection alone is not runtime evidence. Termux execution, source freshness and Bale delivery must be reverified on the deployed commit after cutover changes.
