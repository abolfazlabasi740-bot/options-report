# V4.1 Release 1 Status

## Scope

Release 1 is the operational TSETMC-only reporting layer. Its purpose is to provide a reproducible market-universe snapshot, eligibility/candidate classification, economic-efficiency ranking from available TSETMC fields, report generation, Bale delivery, and runtime evidence publication.

Release 1 does not claim an economically validated Buy/Sell signal.

## Verified operational components

- TSETMC is the operational source of truth.
- Full option-universe discovery is performed before the report display limit is applied.
- TSETMC eligibility and opportunity-candidate classification are implemented.
- The report uses the V4.1 economic scoring engine on eligible opportunity candidates.
- The report preserves explicit source market timestamps when available; retrieval time is not substituted for market time.
- The report distinguishes LIVE_TSETMC_REFRESH from last-known/off-market state.
- Bale delivery has been physically verified with message receipts.
- Runtime evidence publisher architecture is integrated and nonblocking for Bale delivery.
- Full universe snapshots and audit artifacts are retained for runtime evidence.
- BestLimits semantic mapping has been independently evidenced and recorded.
- G7.2 historical sensitivity is closed as evidence-only validation.
- Historical OptionSchool artifacts remain audit evidence only and are not part of the operational TSETMC path.
- The project-control rule requiring GitHub/history review before any Termux command is recorded in docs/PROJECT_CONTROL_RULES_V41.md.

## Current scoring boundary

The production report invokes economic_scoring_engine.build_economic_ranking() after TSETMC eligibility/candidate classification.

The economic score is a deterministic cross-sectional efficiency/ranking measure based only on currently available TSETMC inputs. It is not a predictive return model, probability-of-profit model, or Buy/Sell decision.

The engine does not fabricate IV, Greeks, risk-free rate, theoretical value, or unavailable inputs. Missing information remains unavailable.

The historical scoring_engine.py six-block FinalScore path is retained for audit/history only and is not part of the active runtime compile gate.

## Current production claim

Allowed claim:

**TSETMC economic-efficiency ranking / Top-N operational report**

Not allowed:

- economically validated predictive score;
- expected return;
- probability of profit;
- Buy/Sell signal;
- economically validated best opportunity.

## Remaining evidence gaps

1. G7.1 — authoritative provenance for active economic scoring parameters.
2. G7.3 — approved freshness/staleness policy.
3. G7.4 — remaining exact identity evidence where required.
4. G7.5 — independent economic outcome labels and reproducible validation.

These gaps must not be filled with guessed parameters or synthetic outcomes.

## Release decision boundary

V4.1 operational reporting can be developed and used as a TSETMC evidence/reporting product while economic validation and production Buy/Sell authorization remain open.

Any transition from economic ranking to predictive or Buy/Sell signaling requires a separately evidenced implementation, test, validation package, and GitHub record.

## Control rule

Before any future Termux command, GitHub history, implementation, documentation, and prior evidence must be reviewed. If the requested item is already implemented and evidenced, no duplicate command is issued.