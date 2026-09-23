# Gate 7 Evidence Ledger — V4.1

Date: 2026-09-23

## Verified evidence

| Gate | Evidence | Status |
|---|---|---|
| Gate 2 | Regression CI on main | VERIFIED |
| Gate 3 | Fresh OptionSchool24 source + Audit PASS + Replay MATCH | VERIFIED |
| Gate 6 | Physical Termux execution + Bale receipts | CLOSED |
| Gate 7 Control | Release-boundary CI + secret tracking check | VERIFIED |

## Open evidence

### G7-1 — Parameter provenance
Status: OPEN

The active V4 Overlay constants are observed from production code but do not yet have an authoritative protocol/decision or reproducible historical baseline recorded in the repository.

Required: evidence source for each affected numeric parameter family. No guessed replacement values.

### G7-2 — Historical sensitivity / ablation
Status: VERIFIED — EVIDENCE ARTIFACT HASH/PROVENANCE RECONCILED

The evidence-only implementation reuses the canonical V4.1.1 shadow scorer and performs one-block-at-a-time ablation. It does not modify Production FinalScore, eligibility, ranking, report or Bale output.

Termux evidence run:
- Files: 35
- Sheets: 35
- Sensitivity OK: 35
- Unresolved: 0
- Top-N: 15
- Source period: historical OptionSchool24 workbooks already present in the project; no new market session is required while the market is closed.

Aggregate sensitivity evidence across 35 records:

| Block | Mean Top-15 overlap | Mean rank changes | Mean max score delta | Mean score delta |
|---|---:|---:|---:|---:|
| Liquidity | 6.400000 | 449.142857 | 11.132857 | 3.603773 |
| Valuation | 10.000000 | 445.285714 | 9.042000 | 2.614506 |
| Payoff | 11.228571 | 442.485714 | 8.500000 | 2.127964 |
| Time | 11.514286 | 442.371429 | 7.409714 | 1.988990 |
| Greeks | 13.085714 | 432.000000 | 4.170286 | 1.151357 |
| Market | 12.600000 | 443.114286 | 6.042000 | 1.755308 |

Ranges retained from the same run:

- Liquidity: overlap 5–9; rank changes 237–472; max delta 10.26–12.22; mean delta 3.412690–4.033709.
- Valuation: overlap 8–13; rank changes 228–472; max delta 8.13–9.93; mean delta 2.347813–2.953458.
- Payoff: overlap 10–13; rank changes 227–466; max delta 8.14–9.36; mean delta 2.058977–2.550192.
- Time: overlap 8–12; rank changes 232–468; max delta 6.57–9.00; mean delta 1.725427–2.273042.
- Greeks: overlap 11–14; rank changes 215–461; max delta 3.52–4.31; mean delta 1.088222–1.216261.
- Market: overlap 11–13; rank changes 229–470; max delta 5.24–6.43; mean delta 1.709147–2.068159.

Interpretation boundary: these are sensitivity/ablation measurements only. They do not establish that any block, weight or economic direction is correct, optimal, predictive, or causally important.

Closure evidence has now been reconciled with the Termux run. The two generated evidence artifacts have verified SHA-256 values recorded below. The underlying run retained the real historical source files, source SHA-256 values, deterministic sensitivity measurements and unresolved-case accounting.

Artifact SHA-256:
- `g7_2_historical_sensitivity_evidence.json`: `702ed0de3a68abd2fc86be51165c29a64c9b02241857abcd1ba95d7059fe02fc`
- `g7_2_optionschool24_historical_evidence.json`: `d669d721de052c58a7b65b621759fe714fce1743553d99fb14123b4582fa3a5d`

The golden Gate 3 fixture is an output-regression baseline only; it is not historical economic validation.

### G7-3 — Market timestamp / freshness
Status: OPEN — SOURCE TIMESTAMP CAPTURE IMPLEMENTED, LIVE EVIDENCE PENDING

The TSETMC adapter now preserves an explicit source observation timestamp from `closingPriceInfo.dEven` + `hEven` when both fields are present and valid. This timestamp is explicitly treated as source observation time, not adapter retrieval time and not an inferred session-close time.

- Implementation commit: `c633fa9f04fd386cf8a7d35c5f86ebf748a9b526`
- Regression fixture/test commit: `eab12bcab93db3ff164ab86fe33a5a444191f9c0`
- Output fields: `source_market_timestamp`, `source_market_timestamp_status`.
- Missing/invalid source fields remain `UNAVAILABLE`; no timestamp is synthesized.
- External TSETMC references document `dEven` as YYYYMMDD and `hEven` as HHMMSS and identify `GetClosingPriceInfo/{InsCode}` as the current closing-price information endpoint. citeturn1search0turn1search3
- No freshness threshold has been introduced because no approved threshold/provenance exists yet.
- G7-3 therefore remains OPEN until a real runtime response demonstrates the field on the deployed data path and the stale/fresh policy is separately evidenced.


The current OptionSchool24 workbook path does not establish an authoritative market timestamp. Download time must not be treated as market time.

Required: source market timestamp or authoritative endpoint timestamp, with explicit unknown/stale handling.

Market-closure note: the absence of a new trading session does not itself create a market timestamp; it only means no new traded-market observation is expected during the closure interval.

### G7-4 — Exact TSETMC identity
Status: OPEN

The mapping implementation already enforces four states:
- EXACT_INSTRUMENT_ID
- SYMBOL_ONLY_CANDIDATE
- AMBIGUOUS
- NO_MATCH

Only EXACT_INSTRUMENT_ID may enter the canonical merged snapshot.

Current live OptionSchool24 evidence does not expose the explicit option instrument ID required for exact promotion. Symbol-prefix inference remains prohibited.

Required evidence: exact option identifier, exact underlying identifier, endpoint/source, retrieval time, payload hash, normalized mapping.

### G7-5 — Economic Opportunity validation
Status: OPEN

Opportunity Shadow is technically executable and provenance-hardened, but technical execution is not economic validation.

Required: frozen case definitions, independent-vs-derived evidence separation, historical/observed validation, false-positive and unresolved-case retention.

### G7-6 — Final Gate 7 decision
Status: BLOCKED BY G7-1 through G7-5

No production Signal/Buy/Sell behavior is enabled by this ledger.

## Release boundary

The current operational product remains:

OptionSchool24
→ Validation / Schema Audit
→ Six-Block Scoring
→ Ranking / Top-N
→ Report
→ Audit
→ Bale

No scoring weights, Overlay constants, eligibility thresholds, ranking rules, TSETMC activation, or Bale logic are changed by this ledger.

## Evidence rule

Code existence, CI success, and Bale delivery are necessary operational evidence but do not substitute for economic/historical validation.

## Current conclusion

The operational reporter is deployed and verified. G7-2 now has real multi-workbook sensitivity evidence, but its closure remains pending artifact SHA/provenance reconciliation. The full OptimusAI intelligence cutover remains evidence-gated at Gate 7.
