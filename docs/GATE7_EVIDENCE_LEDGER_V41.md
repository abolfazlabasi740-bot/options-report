# Gate 7 Evidence Ledger — V4.1

Date: 2026-09-22

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
Status: OPEN — IMPLEMENTATION READY

An evidence-only implementation now exists in historical_sensitivity_audit.py with regression coverage. It reuses the canonical V4.1.1 shadow scorer and measures one-block-at-a-time Top-N overlap, rank changes and score deltas without changing Production FinalScore, eligibility, ranking, report or Bale output.

Required for closure: real historical source files, SHA-256, deterministic reruns, block/overlay sensitivity measurements, and retained unresolved cases.

The golden Gate 3 fixture is an output-regression baseline only; it is not historical economic validation.

### G7-3 — Market timestamp / freshness
Status: OPEN

The current OptionSchool24 workbook path does not establish an authoritative market timestamp. Download time must not be treated as market time.

Required: source market timestamp or authoritative endpoint timestamp, with explicit unknown/stale handling.

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

The operational reporter is deployed and verified. The full OptimusAI intelligence cutover remains evidence-gated at Gate 7.
