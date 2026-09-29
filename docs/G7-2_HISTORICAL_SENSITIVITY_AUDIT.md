# G7-2 Historical Sensitivity / Ablation Audit

Status: CLOSED — REAL TSETMC HISTORICAL EVIDENCE REPLAYED.

## Active architecture

G7-2 now uses the active `tsetmc_scoring_engine.py` only. The legacy
`scoring_engine.py` is not an input to this audit.

The audit consumes real saved TSETMC JSON snapshots containing:

- `source_of_truth = TSETMC`
- a non-empty `snapshot_sha256`
- full `rows` (preferably `latest_universe_snapshot.json` or equivalent)
- explicit `eligibility.candidate_instrument_ids`

No OptionSchool24 workbook is accepted by the active runner.

## Analysis

For each real snapshot:

1. Baseline active TSETMC ranking is calculated over Opportunity Candidates.
2. Each of the six blocks is removed one at a time.
3. Each active factor is removed one at a time.
4. Top-N overlap is measured.
5. Common-universe rank changes are measured.
6. Spearman rank correlation is measured where at least two common ranked rows exist.
7. CALL and PUT are also audited separately.
8. Snapshot SHA and retrieval/generation evidence are retained.

Across multiple snapshots, adjacent baseline Top-N overlap is recorded as a
stability measure.

## Safety boundary

- `production_mutation = false`.
- Production report, eligibility, scoring weights, ranking and Bale output are
  not changed by the audit.
- Audit ablations are explicit parameters of the active scorer and default to
  no ablation, so normal production behavior is unchanged.
- No profitability, predictive, or buy/sell conclusion is produced.
- No synthetic or test fixture may be represented as historical market evidence.

## Closure evidence

The historical dataset runner was executed against the retained real TSETMC
snapshot set.

- files_processed: 2
- files_unresolved: 0
- pair_count: 1
- rejected_pair_count: 0
- historical_closure_eligible: True
- top_n: 15
- production_mutation: False
- source_of_truth: TSETMC

Independent observations:

- snapshot: `eb42c66b5ef0f0545f59dd192ff59fedda1f2a27124a806b181d1afddd40d65f`
- snapshot: `3be9bc165e97750f8971936ef569f96517c5c143c5c43a576b87c03f043cc819`
- pair status: `INDEPENDENT_OBSERVATIONS`
- rejected pairs: 0

Current evidence artifact:

`output/g7_2_historical_sensitivity_evidence.json`

SHA-256:

`8b5f62f9ea943a5b1b7ed1efd91ed1ffd423cdbca3ccb5c7bfa27d56ba2c9b2f`

The measured Top-N overlap was 0/15 (0.0%). This is retained as a measured
historical sensitivity result and is not treated as an execution or evidence
failure.

## Closure decision

G7-2 is CLOSED as an evidence-only historical sensitivity / ablation gate.

This closure does not close G7-1, G7-3, G7-4 or G7-5 and does not unblock G7-6.

No production scoring, ranking, eligibility, TSETMC activation or Bale
behavior is changed by this closure.
