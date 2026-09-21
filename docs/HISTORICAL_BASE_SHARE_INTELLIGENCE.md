# Historical Snapshot & Base-Share Intelligence

## Scope

This phase adds an append-only, deterministic historical evidence layer and an evidence-only base-share intelligence layer.

It does not modify Six-Block scoring, FinalScore, Top-N ranking, or Bale message content.

## Historical Snapshot

\`historical_snapshot.py\` stores timestamped snapshots with:

- source snapshot identifier
- deterministic record hash
- source metadata
- explicit identity mode
- normalized records
- field-level change detection between adjacent snapshots

The history store is append-only. Re-submitting an identical snapshot ID with the same record hash is \`DUPLICATE\`. Reusing a snapshot ID with different records is rejected.

No economic threshold is used in the diff engine. Numeric fields expose actual delta, direction, and percent change when mathematically defined.

## Case Historical Context

For Shadow cases, the history layer can attach current-sequence context such as:

- \`NEW_IN_CURRENT_SNAPSHOT\`
- \`PERSISTENT_IN_CURRENT_SEQUENCE\`
- \`NO_CURRENT_RECORD\`
- FinalScore change
- DataConfidence change
- RemainingDays change

These are evidence descriptors only. They do not alter case status or scoring.

## Base-Share Intelligence

\`base_share_intelligence.py\` operates only on explicit \`instrument_id\` records.

It reports:

- current vs previous last-price direction
- volume direction
- trade-value direction
- mathematically defined percentage changes
- last-vs-close percentage
- explicit option-context aggregation when \`underlying_id\` is present

No symbol-prefix parsing is used to identify an underlying instrument.

## Current Runtime Gate

The repository now contains the historical and base-share engines and regression tests.

TSETMC/base-share fields remain non-live until a real runtime response is captured, normalized and hashed.

The active Six-Block engine is unchanged.


## Case Lifecycle & Replay

`case_lifecycle_shadow.py` adds an append-only case event stream. Stable case identity is `type::symbol`, while each event retains the source snapshot and case ID.

Lifecycle states are descriptive: `NEW`, `PERSISTENT`, `STRENGTHENING`, `WEAKENING`, `RESOLVED`, and `RECURRING`. A lifecycle transition is evidence history only; it does not alter the current score or ranking.

`replay_engine.py` executes the Shadow pipeline twice against the same deterministic inputs and compares canonical fingerprints after removing only volatile generation time. A mismatch is an integrity failure rather than a scoring adjustment.


## Audit Integrity Gate

`audit_integrity.py` verifies the minimum audit chain before `latest_audit.json` is published. The gate checks source evidence, historical snapshot identity/hash, Opportunity snapshot consistency and deterministic replay.

A failed integrity gate stops report publication. It does not modify FinalScore or ranking and does not convert missing evidence into a score.
