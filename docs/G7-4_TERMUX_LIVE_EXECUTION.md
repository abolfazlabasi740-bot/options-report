# G7-3 / G7-4 Termux Live Evidence Execution

Date: 2026-09-23

## Purpose

This is the single controlled runtime step for collecting the live TSETMC evidence still required by G7-3 (market timestamp/freshness) and G7-4 (exact option identity).

It is evidence-only. It does not activate TSETMC in production scoring, ranking, eligibility, Top-N or Bale.

## Deployed Termux command

Run on the deployed project:

```bash
cd ~/OptimusAI_V41_LIVE
git pull --ff-only origin main
mkdir -p output/g7_tsetmc
python3 tsetmc_live_smoke.py --option-market-watch --flow 1 --output output/g7_tsetmc/option_market_watch.json
```

The command must be executed against the deployed runtime after the repository has been updated to the current `main`.

## Evidence produced

The smoke utility writes two artifacts:

- `output/g7_tsetmc/option_market_watch.json`
- `output/g7_tsetmc/option_market_watch.raw.json`

The JSON summary records:

- source
- endpoint
- retrieval timestamp
- payload SHA-256
- explicit instrument-ID count
- explicit instrument IDs returned by the source

The raw sibling file preserves the returned payload. No symbol, prefix, strike, expiry, CALL/PUT or underlying identity is inferred.

## G7-4 promotion rule

OptionSchool24 does not expose the numeric TSETMC instrument ID. Its explicit `نماد` field is the option's source identity key. Therefore the accepted cross-source path is:

`OptionSchool نماد`
→ exact unique TSETMC `lVal18AFC_P/C`
→ TSETMC `insCode_P/C`
→ explicit `uaInsCode`
→ exact underlying quote
→ normalized mapping evidence

Symbol matching is accepted only when the OptionSchool symbol set is unique, the TSETMC option-symbol set is unique, and every required OptionSchool symbol has exactly one TSETMC match. Prefix, strike, expiry and CALL/PUT are not used to manufacture identity.

## G7-3 timestamp rule

A market timestamp is accepted only when the source explicitly provides it. The adapter currently preserves `closingPriceInfo.dEven + hEven` as `source_market_timestamp` when valid.

Download/retrieval time is not treated as market time.

No stale/fresh threshold is invented by this runner.

## Acceptance

A successful smoke request alone does not close G7-3 or G7-4.

G7-3 requires real source timestamp evidence plus an approved freshness policy.

G7-4 requires retained exact option identity and explicit underlying identity/quote evidence with source endpoint, retrieval time and payload hash.

No production behavior changes are made by this evidence collection.


## OptionSchool identity reconciliation — 2026-09-24

The deployed workbook has no numeric TSETMC option ID, but it does contain the explicit unique option symbol. The evidence-only reconciliation runner now supports `EXPLICIT_SYMBOL_MATCH` after uniqueness validation.

Runner: `scripts/reconcile_tsetmc_optionschool_38.py`
Implementation commit: `76457fc860ffea36264b63046a08781057dc7cb6`
Completeness hardening: `f8c20da772117c621dcad201b69b079ebfff80d8`
Regression tests: `907f62679d9b4eec93c97c8aebc5edf464944fe3`

The older numeric-ID readiness utility remains available as an optional check, but `NO_EXPLICIT_OPTION_ID` is no longer a blocker when exact unique symbol mapping is available.
