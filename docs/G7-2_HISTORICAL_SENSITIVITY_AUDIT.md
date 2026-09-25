# G7-2 Historical Sensitivity / Ablation Audit

Status: IMPLEMENTED AS EVIDENCE-ONLY TOOL — NOT CLOSED.

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

## Closure requirement

G7-2 remains OPEN until real TSETMC snapshots from more than one observation
period are available and successfully replayed. A single current snapshot can
validate the harness, but cannot establish historical stability.
