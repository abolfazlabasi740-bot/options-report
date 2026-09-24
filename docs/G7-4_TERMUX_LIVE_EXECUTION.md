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

An explicit option instrument ID is only the first identity requirement.

The accepted path is:

`explicit option ID`
→ exact TSETMC instrument evidence
→ explicit `underlying_id`
→ exact underlying quote
→ normalized mapping evidence

Symbol-only matches remain `SYMBOL_ONLY_CANDIDATE` and are never promoted.

## G7-3 timestamp rule

A market timestamp is accepted only when the source explicitly provides it. The adapter currently preserves `closingPriceInfo.dEven + hEven` as `source_market_timestamp` when valid.

Download/retrieval time is not treated as market time.

No stale/fresh threshold is invented by this runner.

## Acceptance

A successful smoke request alone does not close G7-3 or G7-4.

G7-3 requires real source timestamp evidence plus an approved freshness policy.

G7-4 requires retained exact option identity and explicit underlying identity/quote evidence with source endpoint, retrieval time and payload hash.

No production behavior changes are made by this evidence collection.


## OptionSchool explicit-identity readiness check — 2026-09-24

Before any exact cross-source promotion, the deployed runtime can now verify whether the actual OptionSchool24 workbook contains a populated accepted explicit TSETMC option-ID field, without inferring identity from the symbol.

Command:

    python3 scripts/verify_optionschool_identity_readiness.py data/<actual_optionschool_workbook>.xlsx

The check records the workbook SHA-256, row/column counts, accepted ID aliases present, populated ID counts, and an explicit NO_EXPLICIT_OPTION_ID / EXPLICIT_ID_AVAILABLE state. It does not perform symbol-based matching and does not activate TSETMC.

Implementation commit: f8b017c306990443f9e71423b4bec8b6e6c404e3
Test commit: 975e251d73c2b5fdeae4ba3dc70640d2d4a7e7e0

If the result is NO_EXPLICIT_OPTION_ID, G7-4 remains blocked at the source boundary; no synthetic ID may be created from symbol, strike, expiry or CALL/PUT prefix.
