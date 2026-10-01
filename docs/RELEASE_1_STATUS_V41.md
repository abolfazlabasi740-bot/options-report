# V4.1 Release 1 Status

## Scope

Release 1 is the operational TSETMC-only reporting layer. Its purpose is to provide a reproducible market-universe snapshot, evidence-backed opportunity ranking, report generation, Bale delivery, and runtime evidence publication.

Release 1 does not claim an economically validated Buy/Sell signal.

## Verified operational components

- TSETMC is the operational source of truth.
- Full option-universe discovery is performed before the report display limit is applied.
- TSETMC eligibility and opportunity-candidate classification are implemented.
- TSETMC evidence ranking is implemented and produces a deterministic Top-N report.
- Explicit source market timestamps are preserved when available; retrieval time is not substituted for market time.
- The report distinguishes LIVE_TSETMC_REFRESH from last-known/off-market state.
- Bale delivery has been physically verified with message receipts.
- Runtime evidence publisher architecture is integrated and nonblocking for Bale delivery.
- Full universe snapshots and audit artifacts are retained for runtime evidence.
- BestLimits semantic mapping has been independently evidenced and recorded.
- G7.2 historical sensitivity is closed as evidence-only validation.
- Historical OptionSchool artifacts remain audit evidence only and are not part of the operational TSETMC path.
- The project-control rule requiring GitHub/history review before any Termux command is recorded in `docs/PROJECT_CONTROL_RULES_V41.md`.

## Current scoring boundary

The production report uses `tsetmc_scoring_engine.build_evidence_ranking()`.

It is explicitly an evidence ranking, not the historical `scoring_engine.py` FinalScore path.

The evidence-ranking layer does not fabricate IV, Greeks, Open Interest, Theta, or other unavailable fields. Missing information remains unavailable.

The historical six-block `scoring_engine.py` path exists and has been audited, but it must not be connected directly to the TSETMC report until its required inputs and economic policy are actually evidenced.

## Current production claim

Allowed claim:

**TSETMC Evidence Ranking / Top-N operational report**

Not allowed:

- validated economic score;
- predictive score;
- Buy/Sell signal;
- expected return;
- probability of profit;
- economically validated "best opportunity".

## Remaining evidence gaps

1. G7.1 — authoritative provenance for active economic scoring parameters.
2. G7.3 — approved freshness/staleness policy.
3. G7.4 — remaining exact identity evidence where required.
4. G7.5 — independent economic outcome labels and reproducible validation.

These gaps must not be filled with guessed parameters or synthetic outcomes.

## Release decision boundary

Release 1 operational reporting can be developed and used as an evidence/reporting product without enabling Buy/Sell behavior.

Any transition from evidence ranking to economic scoring or Buy/Sell signaling requires a separately evidenced implementation, test, and GitHub record.

## Control rule

Before any future Termux command, GitHub history, implementation, documentation, and prior evidence must be reviewed. If the requested item is already implemented and evidenced, no duplicate command is issued.
