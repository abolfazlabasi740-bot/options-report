# PROJECT CONTROL RULES V4.1

## Rule: History-First Before Any Termux Command

Before issuing any new Termux command for this project, the current GitHub project history and relevant repository evidence must be reviewed.

The review must cover, as applicable:
- relevant commits and their messages;
- current implementation files;
- project documents and protocols;
- successful runtime evidence and test evidence;
- previously solved items and known limitations.

### Decision rule

1. If the requested item is already implemented, tested successfully, and recorded in GitHub/evidence, do not issue another Termux command for the same item.
2. Issue a new Termux command only when a concrete implementation, verification, or evidence gap remains.
3. Do not repeat a previously successful test merely to rediscover an already established result.
4. After a new implementation or runtime test succeeds, record the result in GitHub with an identifiable commit/evidence trail before treating the item as part of the official project state.
5. Do not claim completion without corresponding evidence.
6. Do not introduce new gates, parameters, thresholds, formulas, data sources, or scope merely to delay an already defined release objective.
7. OptionSchool historical artifacts must not be reintroduced into the TSETMC-only operational path unless a separately documented project decision explicitly requires it.
8. Missing evidence must be reported as missing evidence; it must not be replaced by inference or guessed values.

This document is a project-control rule and applies to subsequent implementation and runtime work on V4.1.
