# G7-4 Unmatched OptionSchool Symbol Analysis

## Purpose

Analyze OptionSchool24 symbols that do not have an exact match in the retained TSETMC Option Market-Watch snapshot.

## Hard identity rule

Only exact string equality is accepted:

OptionSchool24 `نماد` == TSETMC `lVal18AFC_P` or `lVal18AFC_C`

Uniqueness must hold in both snapshots. No matching by prefix, strike, expiry, CALL/PUT, or other similarity is permitted.

## Lifecycle rule

A symbol absent from the current TSETMC Option Market-Watch snapshot is classified only as:

`NOT_IN_CURRENT_TSETMC_SNAPSHOT`

It is NOT classified as closed or expired merely because it is absent.

To prove `CLOSED_OR_EXPIRED`, the project needs authoritative historical/inactive evidence or an explicit lifecycle record. The current snapshot alone cannot establish that conclusion.

## Termux execution

```bash
cd ~/OptimusAI_V41_LIVE
git pull --ff-only origin main

python3 scripts/reconcile_tsetmc_optionschool_38.py \
  --optionschool data/optionschool_20260922_174818_730899.xlsx \
  --tsetmc output/g7_tsetmc/option_market_watch.raw.json \
  --output output/g7_tsetmc/reconciliation_38.json

python3 scripts/analyze_unmatched_optionschool_symbols.py \
  --optionschool data/optionschool_20260922_174818_730899.xlsx \
  --tsetmc output/g7_tsetmc/option_market_watch.raw.json \
  --output output/g7_tsetmc/unmatched_symbols.json
```

The second command produces row-level evidence for every unmatched symbol. It does not modify scoring, ranking, eligibility, Signal, or Bale behavior.

## Current known live evidence

Workbook SHA:
`78ef5ffe945138748076ee81694e8b1d0319dd5d79d8e50ff99c238934931693`

Workbook:
478 rows × 38 columns.

The prior real Termux reconciliation found:
- 369 exact unique symbol matches
- 109 symbols absent from the retained TSETMC snapshot
- 0 ambiguous symbol matches
- OptionSchool symbol uniqueness: true
- TSETMC symbol uniqueness: true

Those 109 are not yet proven to be closed/expired.

## Next gate

After the updated reconciliation is executed on the retained raw snapshot, use the 369 exact row mappings for field-by-field comparison. Derived fields remain OPEN until their formulas, source inputs, conventions, and tolerances are independently evidenced.
