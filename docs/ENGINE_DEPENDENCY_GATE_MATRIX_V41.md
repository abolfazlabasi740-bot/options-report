# OptimusAI V4.1 — Engine Dependency & Gate Matrix

## Purpose

این سند سازمان Engineها را به یک نقشه عملیاتی تبدیل می‌کند: وابستگی هر Engine، رفتار در خطا، Gate موردنیاز، خروجی مصرف‌کننده و Evidence لازم.

این سند «نقشه کنترل» است و به‌تنهایی هیچ Engine یا پارامتر اقتصادی را Production نمی‌کند.

## 1. Architectural Dependency Map

### Control plane

Orchestrator / Project Management
→ Gate ownership, sequencing, provenance, release control

Knowledge / Governance
→ protocol, parameter provenance, change control

Audit
→ evidence integrity, hashes, replay, release evidence

### Production data path

Data
→ Parsing / Validation
→ Feature / Analytics
→ Risk / approved overlays
→ Six-Block Scoring
→ Ranking / Top-N
→ Strategy
→ Decision
→ Signal Gate
→ Reporting
→ Audit
→ Bale Distribution

### Analytical sidecars

Validated / scored universe
→ Opportunity Intelligence (Shadow)

Historical artifacts
→ Memory / Learning (Developing)

Production/Shadow artifacts
→ Red Team (Shadow)

Golden / Replay
→ regression and determinism evidence

TSETMC Identity
→ exact identity enrichment only after explicit instrument identity evidence

## 2. Runtime vs Organizational Dependency

The organizational chart is a control architecture. It must not be confused with the exact current runtime call order.

Current repository evidence establishes that the active report path uses the central Report Engine and that Opportunity Shadow is non-blocking. Therefore:

- Organizational dependency = authority and gate relationship.
- Runtime dependency = actual code invocation order.
- No claim is made here that every organizational arrow is a literal function-call sequence.

Where runtime order is not directly evidenced, the matrix marks the dependency as CONTROL rather than a runtime-call assertion.

## 3. Dependency / Failure Matrix

| Unit | Mandatory upstream evidence | Optional / Shadow inputs | Failure behavior | Production gate | Main consumer |
|---|---|---|---|---|---|
| Orchestrator | repository/project state + gate evidence | all engine artifacts | STOP release control on unresolved mandatory gate | A4 / Gate authority | all units |
| Data | real source artifact | alternate source evidence | STOP production data path | Gate 3 | Validation |
| Validation | source artifact + schema checks | schema-audit evidence | REJECT invalid rows; STOP if required production universe is not valid | Gate 2/3 | Analytics/Scoring |
| Feature / Analytics | validated fields | derived Shadow features | STOP affected feature/block; no invented values | Gate 2/3 | Risk/Scoring/Shadow |
| Opportunity Intelligence | validated/scored evidence | chain/cross-chain/relative-value/explanation | SHADOW failure is NON-BLOCKING; integrity/replay failure remains blocking where required | Gate 5 | Memory/Red Team/Audit |
| Risk | validated features + approved policy | Shadow risk evidence | TRANSITIONAL; cannot silently introduce thresholds | policy/Governance | Scoring/Decision |
| Six-Block Scoring | validated features + approved parameters | historical sensitivity evidence | STOP FinalScore if an entire block is unavailable or parameters are unapproved | Gate 2/3 + parameter provenance | Ranking/Reporting |
| Ranking / Top-N | valid FinalScore + eligibility | tie-break evidence | STOP ranking if required score/eligibility is invalid; never repair scores | scoring gate | Reporting |
| Strategy | approved evidence + documented policy | Opportunity/Red-Team evidence | CONTROLLED; no undocumented economic rule enters production | policy closure | Decision |
| Decision | permitted production evidence + gate state | Shadow evidence | BLOCK on failed mandatory gate; no independent ranking | Gate 7 / policy | Signal |
| Signal Gate | Decision trace + release policy | Red Team challenge | PENDING/BLOCKED until policy closure | Gate 7 | Reporting/authorized downstream |
| Reporting | approved ranked output + audit-linked artifacts | explanation/Shadow summaries | STOP report release if required audit linkage fails | Gate 6 prerequisites | Bale |
| Audit | stage artifacts + hashes + replay results | runtime receipts | FAIL release when integrity evidence is missing/failed | Gate 2–6 evidence | Orchestrator/Bale |
| Bale Distribution | approved report + Audit PASS + delivery config | delivery receipts | STOP delivery; never generate alternate analysis | Gate 6 | user |
| TSETMC Identity | explicit option instrument ID + underlying ID + exact source evidence | none until identity exists | DISABLED/DEFERRED; no symbol inference | Gate 4 | enrichment/analytics |
| Memory / Learning | historical evidence | replay/Golden artifacts | SHADOW/DEVELOPING; cannot mutate current scoring silently | Gate 5/7 as applicable | Intelligence/Governance |
| Red Team | case/evidence artifact | historical/market evidence | SHADOW; challenge only, no silent source mutation | Gate 5 | Decision/Audit |
| Knowledge / Governance | approved protocols + evidence | review artifacts | BLOCK parameter/cutover change until provenance is documented | A4 | Orchestrator/all |

## 4. Failure Propagation Rules

### STOP
Used when production output would otherwise be unverifiable or fabricated.

Examples:
- invalid/missing required production source;
- entire scoring block unavailable;
- unapproved scoring parameter;
- failed Audit required for release;
- failed mandatory Gate.

### REJECT / DEGRADE
Used where individual rows or non-essential fields can be excluded without inventing data.

Examples:
- invalid individual contract row;
- unavailable optional factor redistributed only within its own approved block;
- unsupported optional enrichment.

### SHADOW / CONTINUE
Used for analytical experiments whose failure must not corrupt the production path.

Examples:
- Opportunity Shadow failure;
- Chain Shadow failure;
- Relative Value Shadow failure;
- Red Team challenge.

Exception: Shadow integrity/replay controls that are explicitly release-critical remain blocking according to Gate policy.

### DISABLED / DEFERRED
Used when an integration prerequisite is objectively absent.

Current example:
- TSETMC exact option identity is unavailable from the live OptionSchool24 source; TSETMC enrichment remains disabled rather than inferred.

## 5. Gate Ownership Matrix

| Gate | Scope | Required evidence | Current state | Control owner |
|---|---|---|---|---|
| Gate 2 | Regression | workflow/run/job/status + relevant evidence | VERIFIED | Orchestrator + Audit |
| Gate 3 | Real OptionSchool24 | workbook + SHA + schema + counts + successful report | VERIFIED | Data + Validation + Audit |
| Gate 4 | TSETMC identity | explicit option/underlying IDs + quote/source/time/payload hash | PENDING | TSETMC Identity + Governance |
| Gate 5 | Shadow Intelligence | Shadow artifacts + Evidence Graph/Cluster + replay/determinism + lifecycle evidence where enabled | Architecture/analytical verification present; economic opportunity validation separate | Intelligence + Audit |
| Gate 6 | Bale delivery | same report path + report/source hashes + Audit PASS + real delivery receipt | CLOSED | Reporting + Audit + Bale |
| Gate 7 | Production cutover | current Gates 2–6 + policy/economic/freshness closure | NOT CLOSED | Orchestrator/Governance |

Gate status is not promoted merely because repository files exist.

## 6. Current Known Blocking Items

1. Scoring Overlay parameter provenance is OPEN.
2. Exact TSETMC option instrument identity is PENDING.
3. Market-data timestamp/freshness remains UNVERIFIED where the source workbook lacks a market timestamp.
4. Historical sensitivity / ablation evidence remains required for economic policy validation.
5. Opportunity Intelligence economic/financial validation remains separate from technical Shadow verification.
6. Gate 7 is NOT CLOSED.

## 7. Non-Bypass Rules

No downstream unit may:
- manufacture an upstream missing value;
- repair another Engine's score;
- create a second production ranking;
- infer CALL/PUT from symbol prefixes;
- bypass a mandatory Gate;
- activate Shadow output without cutover evidence;
- change scoring constants without provenance and regression evidence;
- make Bale perform analysis.

## 8. Evidence Standard

A status claim must identify the evidence class:

- Repository evidence: file/commit.
- CI evidence: workflow/run/job.
- Source evidence: workbook identity and SHA.
- Runtime evidence: actual deployed execution.
- Distribution evidence: Bale receipt.
- Economic evidence: historical/ablation/financial validation.

One evidence class does not substitute for another.

## 9. Change Control

This matrix does not change:
- Six-Block weights;
- V4 Overlay constants;
- eligibility thresholds;
- TSETMC activation;
- Ranking logic;
- Bale delivery logic.

Any future production change must be separately versioned, regression-tested and recorded in Project Status / Master Project Book.
