# Ranking / Top-N / Bale Path Audit — V4.1.1

## Current path
The former workbook-based path is archival. The active path is:

`TSETMC Market-Watch`
→ explicit option instrument IDs
→ TSETMC quote / BestLimits / instrument-info evidence
→ TSETMC-only canonical snapshot
→ evidence-only report
→ Bale distribution

## Current control
Six-Block scoring, ranking and Buy/Sell signaling are OFF until the TSETMC evidence gate closes.

No historical OptionSchool24 field is copied into the active canonical dataset. Historical reconciliation remains audit evidence only.

## Bale boundary
Bale receives the report produced by `report_engine.py`. It does not calculate, rank or enrich the report.

## Required production cutover evidence
- exact TSETMC instrument identity
- exact field mappings
- market-data timestamp/freshness evidence
- deterministic regression evidence
- deployed Termux evidence
- successful Bale delivery receipt

Until those controls are evidenced on the same deployed commit, production ranking remains closed.
