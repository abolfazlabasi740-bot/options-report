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

## Corrected lifecycle result — 2026-09-24

The corrected Termux run on the same retained evidence produced:

- TOTAL unmatched: 109
- NOT_EXPIRED_BEFORE_SNAPSHOT: 109
- EXPIRED_BEFORE_SNAPSHOT: 0
- NOT_PROVABLE_FROM_CURRENT_EVIDENCE: 0

Snapshot retrieval time used: 2026-09-23T17:17:58.479447+00:00

Therefore all 109 unmatched symbols had an OptionSchool expiry date after the retained TSETMC snapshot time. This does not prove that the contracts were active, tradable, or omitted from the snapshot for one particular reason. It proves only that expiry-before-snapshot is not an explanation supported by the current evidence.

The previous 109/109 expired result is invalid and must not be used.

## Next evidence boundary

Because the unmatched set is future-dated relative to the retained snapshot, the next investigation is an authoritative TSETMC InstrumentSearch lookup for each exact unmatched symbol. The new evidence-only runner is scripts/investigate_unmatched_tsetmc_search.py.

Termux command:

    cd ~/OptimusAI_V41_LIVE
    git pull --ff-only origin main
    python3 scripts/investigate_unmatched_tsetmc_search.py --unmatched output/g7_tsetmc/unmatched_symbols_v3.json --output output/g7_tsetmc/unmatched_tsetmc_search.json

Then summarize status counts and print exact returned symbol matches. The runner accepts only exact returned symbol equality and records the TSETMC endpoint, response hash, retrieval time, exact match count, and returned records. It does not infer identity and does not modify production behavior.

Next G7-4 evidence requirement: execute this lookup on Termux and retain the output artifact. No production activation is permitted from this investigation alone.

## Raw-field reconciliation stage — 2026-09-24

A separate evidence-only runner has been added for the 369 exact unique symbol mappings. It compares only fields directly represented in the retained TSETMC Option Market-Watch snapshot and refuses to invent formulas or tolerances.

- Script: scripts/reconcile_tsetmc_optionschool_fields.py
- Commit: 1f31b6fed3436c6bd31c21d050bcde80d63c5f72
- Test: 6f19faec687eee67dc0bab807362cf2cba80c9d2
- Production scoring/ranking/eligibility/TSETMC activation/Bale behavior: unchanged.

The first pass is deliberately conservative:
- Symbol: exact identity match.
- Strike: direct source-value comparison.
- Expiry: retained as source values; no Jalali/Gregorian conversion is used to manufacture equality in this stage.
- Calendar days: TSETMC remainedDay is recorded against OptionSchool روزهای تقویمی, but equality is not declared until the source convention is proven.
- Underlying quote, BestLimits, IV, HV, Greeks, Black-Scholes, leverage and other derived fields require additional source evidence and/or formula reconciliation.

Termux command after pulling main:

    python3 scripts/reconcile_tsetmc_optionschool_fields.py \\
      --optionschool data/optionschool_20260922_174818_730899.xlsx \\
      --reconciliation output/g7_tsetmc/reconciliation_38.json \\
      --tsetmc output/g7_tsetmc/option_market_watch.raw.json \\
      --output output/g7_tsetmc/field_reconciliation.json

No field is promoted to production from this evidence-only stage.
