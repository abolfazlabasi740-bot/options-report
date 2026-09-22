# OptimusAI V4.1 — Master Engine Control Matrix

## Purpose

این سند مرجع عملیاتی واحد برای مدیریت Engineهای OptimusAI است. برای هر واحد، مالکیت عملیاتی، ورودی مجاز، خروجی، Gate، Evidence، رفتار خطا، Recovery و سطح اختیار مشخص می‌شود.

این Matrix جایگزین Engine Contract، Gate Document یا Runtime Evidence نیست؛ آنها منابع تفصیلی و اثباتی این سند هستند.

## Master Control Matrix

| Engine / Unit | Owner / Control | Input | Output | Gate | Evidence | Failure | Recovery | Authority |
|---|---|---|---|---|---|---|---|---|
| Orchestrator / Project Management | Central control | approved artifacts + gate state | execution/release state | A4 | project status, commits, gate evidence | STOP release | resolve blocking gate | A4 |
| Data | Data control | real external workbook/source | immutable source + SHA | Gate 3 | source file, SHA, schema | STOP data path | acquire valid source | A0/A1 |
| Parsing / Validation | Validation control | raw source | validated universe + rejects | Gate 2/3 | tests, schema/count evidence | REJECT / STOP affected path | correct source/schema; never invent value | A1 |
| Feature / Analytics | Analytics control | validated observed fields | derived features | Gate 2/3 | deterministic artifacts/tests | DEGRADE affected factor/block | restore valid input | A1 |
| Opportunity Intelligence | Intelligence control | validated/scored evidence | Shadow cases/evidence graph | Gate 5 | shadow artifact, replay, hashes | SHADOW / CONTINUE | isolate failed case/engine | A2 |
| Risk | Risk/Governance | validated features + approved policy | risk artifact | policy gate | approved policy + tests | BLOCK transition | approve/document policy | Transitional |
| Six-Block Scoring | Scoring control | validated features + approved parameters | BaseScore/FinalScore | Gate 2/3 + provenance | regression + parameter record + audit | STOP FinalScore | restore approved parameter/input | A3 |
| Ranking / Top-N | Ranking control | valid FinalScore + eligibility | deterministic ranking | scoring gate | ranking audit/tie-break evidence | STOP ranking | upstream correction only | A3 |
| Strategy | Strategy/Governance | approved evidence + policy | strategy-state artifact | policy closure | documented policy + regression | CONTROLLED/BLOCKED | policy closure | Architecture |
| Decision | Orchestrator/Governance | permitted production evidence | decision trace/gate result | Gate 7 | decision trace + gate state | BLOCK | resolve gate | Controlled |
| Signal Gate | Governance | decision trace + release policy | authorized signal artifact | Gate 7 | release evidence | BLOCKED | policy/release closure | Pending |
| Reporting | Reporting control | approved ranking + audit artifacts | report/cards | Gate 6 prerequisites | report SHA + audit | STOP release | restore audit linkage | A3 |
| Audit | Independent control | artifacts from all stages | integrity/evidence record | Gates 2–6 | hashes, replay, runtime evidence | FAIL release | repair evidence, rerun | A3 |
| Bale Distribution | Distribution control | approved report + Audit PASS | delivery receipt | Gate 6 | actual Bale receipt | STOP delivery | retry same approved report path | A3 |
| TSETMC Identity | Data/Governance | explicit option + underlying IDs | exact identity mapping | Gate 4 | source endpoint, time, payload SHA | DISABLED/DEFERRED | obtain explicit identity evidence | Pending |
| Memory / Learning | Knowledge control | historical evidence | memory/baseline artifact | Gate 5/7 as applicable | historical hashes/replay | SHADOW | isolate memory artifact | Developing |
| Red Team | Independent challenge | case/evidence artifacts | challenge/rejection evidence | Gate 5 | challenge trace | SHADOW | revise evidence path, not source silently | Shadow |
| Knowledge / Governance | Governance | protocols + evidence | controlled specification | A4 | versioned docs + regression | BLOCK change | provenance/approval | A4 |
| Replay / Golden Dataset | Audit/Governance | known fixture + production artifact | deterministic comparison | Gate 2/5 | fixture/hash/result | BLOCK relevant release | reconcile regression | Evidence-only |

## Authority Rules

1. A0 observes.
2. A1 transforms validated evidence deterministically.
3. A2 recommends or creates Shadow evidence.
4. A3 can affect production output only within a closed Gate and documented contract.
5. A4 controls release, provenance and governance.

No lower authority may self-promote.

## Single-Source-of-Truth Rules

- Data Engine owns source identity.
- Validation owns acceptance/rejection of source rows.
- Feature Engine owns deterministic feature derivation.
- Scoring owns FinalScore calculation.
- Ranking owns ordering/Top-N only.
- Reporting owns presentation only.
- Audit owns integrity evidence.
- Bale owns delivery only.
- Orchestrator owns release state.
- Governance owns parameter/protocol change control.

No Engine may create a parallel production interpretation of another Engine's output.

## Failure Policy

### Blocking failures

These stop the affected production path:

- invalid required source;
- failed mandatory validation;
- unavailable complete scoring block;
- unapproved active scoring parameter;
- invalid ranking input;
- required Audit failure;
- failed mandatory Gate;
- missing evidence required for release.

### Non-blocking Shadow failures

These remain isolated unless the Gate explicitly makes their integrity evidence release-critical:

- Opportunity Shadow analytical case failure;
- Chain/Relative-Value Shadow case failure;
- Red Team challenge;
- exploratory Memory/Learning output.

### Deferred integrations

The system deliberately defers an integration when its objective prerequisite is absent.

Current example: TSETMC exact option identity.

## Recovery Principle

Recovery must occur upstream.

A downstream Engine must not compensate for an upstream failure by inventing, repairing or silently replacing data.

Example:

Bad source → Validation rejection → Data correction

not:

Bad source → Scoring guesses missing value

## Gate 7 Readiness Rule

Gate 7 cannot be closed merely because the software path executes successfully.

The following evidence classes must remain distinguishable:

1. Repository / code evidence.
2. CI / regression evidence.
3. Real source evidence.
4. Deployed runtime evidence.
5. Distribution evidence.
6. Economic / historical validation evidence.

Current Gate 6 closure is runtime/distribution evidence only; it is not full V4.1 production cutover.

## Current Project Control State

- Gate 2: VERIFIED.
- Gate 3: VERIFIED.
- Gate 4: PENDING.
- Gate 5: technical Shadow/Replay/Audit verification present; economic validation separate.
- Gate 6: CLOSED.
- Gate 7: NOT CLOSED.
- Scoring parameter provenance: OPEN.
- Source market-time freshness: UNVERIFIED where unavailable in source.
- Exact TSETMC identity: PENDING.
- Economic validation of Opportunity Intelligence: OPEN.

## Change-Control Boundary

This Matrix does not authorize changes to:

- Six-Block weights;
- V4 Overlay constants;
- eligibility thresholds;
- Ranking logic;
- TSETMC activation;
- Signal policy;
- Bale delivery logic.

Any such change requires its own documented decision, version, regression evidence and updated Project Status / Master Project Book entry.
