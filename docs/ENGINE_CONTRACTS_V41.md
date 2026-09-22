# OptimusAI V4.1 — Engine Contracts & Authority Matrix

## Purpose

This document converts the organizational chart into operational contracts. It defines what each Engine is allowed to consume, produce and authorize.

## Authority Levels

- A0 — Observe: may inspect and record evidence.
- A1 — Transform: may calculate deterministic derived fields from validated inputs.
- A2 — Recommend: may create Shadow cases or analytical hypotheses.
- A3 — Production: may affect production output only after its Gate is closed.
- A4 — Release: reserved for Orchestrator/Governance and final release control.

No Engine may self-promote from a lower authority level.

## Contracts

| Engine | Input authority | Output | Current authority |
|---|---|---|---|
| Orchestrator | all approved artifacts | execution plan, gate status, release control | A4 |
| Data | external source | immutable source artifact + hash | A0/A1 |
| Validation | raw source | validated dataset + rejection reasons | A1 |
| Feature/Analytics | validated dataset | derived observed features | A1 |
| Opportunity Intelligence | validated/scored universe | evidence-backed Shadow cases | A2 |
| Risk | validated features + approved policy | risk overlay/artifact | Transitional |
| Scoring | validated features + approved parameters | BaseScore/FinalScore | A3 |
| Ranking | scored eligible universe | deterministic rank/Top-N | A3 |
| Strategy | validated evidence + approved policy | strategy-state artifact | Architecture |
| Decision | all permitted evidence | decision trace/gate result | Controlled |
| Signal | decision + release policy | authorized signal artifact | Pending |
| Reporting | approved production artifacts | report/cards | A3 |
| Audit | artifacts from every stage | integrity/evidence record | A3 |
| Bale Distribution | approved report + audit PASS | delivery receipt | A3 |
| TSETMC Identity | exact identity evidence | identity mapping/enrichment | Pending |
| Memory/Learning | historical evidence | memory profile/baseline | Developing |
| Red Team | case/evidence artifact | challenge/rejection evidence | Shadow |
| Knowledge/Governance | protocols + evidence | controlled specification | A4 |

## Hard Boundaries

1. Data may not manufacture missing fields.
2. Validation may reject but may not invent economic values.
3. Analytics may derive only from observed/approved inputs.
4. Opportunity Intelligence may discover cases but cannot alter FinalScore.
5. Red Team may challenge a case but cannot silently rewrite source data.
6. Scoring may use only documented parameters.
7. Ranking may not create or repair scores.
8. Strategy may not introduce undocumented economic thresholds.
9. Decision may not bypass a failed mandatory Gate.
10. Signal remains blocked until its policy and release conditions are explicitly closed.
11. Reporting may format approved outputs but may not recalculate an alternate ranking.
12. Bale is distribution only; it is not an analysis engine.
13. TSETMC promotion to exact identity requires explicit accepted instrument identity; symbol-prefix inference remains prohibited.
14. Memory may preserve historical evidence but may not silently change current scoring.
15. Governance changes require versioned documentation and regression evidence.

## Failure Propagation

A mandatory upstream failure blocks dependent production output.

Examples:
- invalid source → no production scoring;
- missing entire scoring block → no FinalScore;
- unapproved scoring parameter → no parameter cutover;
- missing exact option identity → no exact TSETMC enrichment;
- Audit failure → no Bale release;
- missing Bale receipt → delivery status is not PASS.

Shadow failure must not corrupt the production path.

## Cutover Rule

A Shadow Engine can become production-active only when:

1. its contract is documented;
2. its inputs are proven available;
3. its output is deterministic where required;
4. Golden/Regression comparison is completed;
5. economic policy is explicitly approved where applicable;
6. the relevant Gate is closed;
7. Orchestrator records the cutover.

## Current Priority

The next production-authority work remains:
- scoring parameter provenance;
- exact TSETMC identity;
- source freshness evidence;
- historical sensitivity/ablation;
- economic validation of Opportunity Intelligence.

No authority is granted to change active scoring constants merely to close a Gate.
