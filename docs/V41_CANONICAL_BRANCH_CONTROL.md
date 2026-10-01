# V4.1 Canonical Branch Control

## Canonical project branch

The only active development and production-reference branch is:

- `main`

Current canonical commit at the time of this control update:

`b95000c5b07a29f207781599de3758a2fb931f3f`

## Operational branches that remain active

These branches are transport/runtime infrastructure and are intentionally retained:

- `bridge-commands` — Termux command queue
- `bridge-results` — Termux command results
- `runtime-evidence` — retained runtime evidence history

They are not alternative project-version branches.

## Inactive feature branches

The following historical feature branches are no longer active development branches. Their historical state was preserved under `archive/2026-10-01/` and the original branch refs were moved to the canonical `main` commit:

- `economic-scoring-v41`
- `g7-5-economic-validation-v41`
- `integrate-g7-5-economic-validation-v41`
- `runtime-evidence-publisher`

Archived counterparts:

- `archive/2026-10-01/economic-scoring-v41`
- `archive/2026-10-01/g7-5-economic-validation-v41`
- `archive/2026-10-01/integrate-g7-5-economic-validation-v41`
- `archive/2026-10-01/runtime-evidence-publisher`

## Active V4.1 code boundary

The active report path is TSETMC-only and uses the V4.1 engines currently referenced by `report_engine.py`.

Historical `scoring_engine.py` remains retained as audit/history material and is not part of the active runtime compile gate.

The runtime verification gate now compiles the canonical V4.1 runtime surface rather than the historical scoring path.

## Preservation rule

Historical evidence, snapshots, audit artifacts, and archived branch state must not be deleted merely to simplify the active project tree.

No historical artifact is treated as an active production dependency unless it is explicitly referenced by the canonical V4.1 runtime path.
