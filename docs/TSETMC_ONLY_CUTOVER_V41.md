# TSETMC-Only Cutover — V4.1.1

Date: 2026-09-24

## Decision
TSETMC is now the sole source of truth for option instruments and market data.
OptionSchool24 is no longer a runtime comparison dependency.

Previous OptionSchool24 snapshots and the 369/109 reconciliation history remain archival evidence only. They are not consumed by the TSETMC source engine and are never used to fill missing TSETMC fields.

## Source boundary
TSETMC Option Market-Watch is the universe and identity boundary. Each option instrument is represented by TSETMC's explicit instrument ID, contract side, underlying ID, strike and expiry. Quote and BestLimits evidence is fetched by explicit TSETMC IDs.

## No inference
Only verified TSETMC source representations populate canonical fields. Unknown values remain null.
TSETMC remainedDay is retained as raw evidence but is not silently mapped to canonical calendar-days until the convention is frozen.
BestLimits is retained as raw evidence until exact field mapping is verified.
Open interest, contract size, collateral, IV/HV and Greeks are not fabricated.
Derived fields are not activated merely because OptionSchool24 previously supplied similarly named values.

## Cutover sequence
1. TSETMC-only raw/canonical snapshot.
2. TSETMC row-level option and underlying quote evidence.
3. Exact BestLimits field mapping.
4. TSETMC-supported contract specification and open-interest evidence.
5. Freeze date, trading-day, intrinsic, breakeven, leverage and model conventions.
6. Derive IV/HV/Greeks/Black-Scholes only from TSETMC-supported inputs.
7. Re-enable Six-Block scoring only after the evidence gate passes.
8. Reconnect Opportunity, Replay, Audit and Bale to the TSETMC-only canonical dataset.

Until step 7, no FinalScore is promoted from the old OptionSchool-backed runtime.

## Consequence
The old reconciliation loop is no longer on the critical path. The 109 unmatched OptionSchool symbols do not block TSETMC development. Historical reconciliation remains available only for audit/history.


## 2026-09-24 control update

The active TSETMC report path now applies an optional symbol-prefix filter to the TSETMC Market-Watch universe before the bounded per-instrument enrichment limit. This prevents a symbol-scoped request from accidentally inspecting only the first N market-watch records. No ranking is implied; scoring remains OFF.


## Regression correction — 2026-09-24

The first symbol-filter control exposed two test-fixture issues: the baseline fixture now contains two Market-Watch rows and the bounded test must explicitly limit it; the quote-failure test must select the intended symbol before enrichment. Both were corrected. CI also exposed that `tsetmc_live_smoke.py --allow-network-unavailable` intentionally writes `NETWORK_UNAVAILABLE` but exits non-zero; the live-schema workflow now explicitly permits that exit only when the resulting artifact status is exactly `NETWORK_UNAVAILABLE`. Any other failure remains blocking.
