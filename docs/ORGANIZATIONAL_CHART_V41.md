# OptimusAI V4.1 — Organizational Architecture & Engine Charter

## 1. Purpose

This document defines the operational organization of OptimusAI V4.1 as a controlled system of specialized engines under a central Orchestrator. It is an organizational control model, not merely a software pipeline.

Each Engine has:
- a single primary responsibility;
- defined inputs and outputs;
- explicit dependencies;
- a defined production/Shadow/Transitional/Pending state;
- an evidence boundary;
- no authority to create an independent production analysis outside the canonical path.

## 2. Executive Control

Orchestrator / Project Management
→ controls execution order, gates, provenance, versioning, evidence, failure handling and release status.

The Orchestrator does not calculate market scores itself. It coordinates the Engines and prevents unverified Engines from affecting production output.

## 3. Canonical Production Chain

Data Engine
→ Parsing & Validation Engine
→ Feature / Analytics Engine
→ Opportunity Intelligence
→ Risk Engine
→ Six-Block Scoring Engine
→ Ranking / Top-N
→ Strategy Engine
→ Decision / Decision Trace
→ Signal Gate
→ Reporting Engine
→ Audit Engine
→ Distribution / Bale

Cross-cutting control layers:
- Intelligence / Brain
- Memory / Learning
- Knowledge / Governance
- Red Team / Devil's Advocate
- Replay / Golden Dataset

Shadow engines may inspect the same validated source, but cannot mutate FinalScore, ranking, Top-N or Bale output unless a formal cutover gate is closed.

## 4. Engine Charter

| Unit | Primary responsibility | Current state |
|---|---|---|
| Orchestrator / Project Management | sequence, gates, evidence, release control | ACTIVE |
| Data Engine | acquire and preserve real source data | ACTIVE |
| Parsing / Validation | schema, finite values, eligibility and data integrity | ACTIVE |
| Feature / Analytics | derive only supported observed features | ACTIVE |
| Opportunity Intelligence | discover evidence-backed opportunity cases | SHADOW ACTIVE |
| Risk Engine | risk overlays and approved thresholds | TRANSITIONAL |
| Six-Block Scoring | deterministic FinalScore calculation | ACTIVE V4.1.1 |
| Ranking / Top-N | deterministic ordering and selection | ACTIVE / VERIFIED |
| Strategy Engine | strategy-policy contract; no unapproved economic rules | ARCHITECTURE ACTIVE |
| Decision Engine | decision-support trace and gate evaluation | CONTROLLED / NON-INDEPENDENT |
| Signal Gate | production signal authorization | PENDING POLICY CLOSURE |
| Reporting | Card report and audit-linked output | ACTIVE |
| Audit | hashes, manifests, replay and integrity checks | ACTIVE |
| Bale Distribution | controlled delivery of existing report | ACTIVE; Gate 6 CLOSED |
| TSETMC Identity | exact instrument identity and enrichment | PENDING |
| Memory / Learning | historical evidence and lifecycle memory | DEVELOPING |
| Red Team | challenge/contradiction layer | SHADOW |
| Knowledge / Governance | protocol, provenance and change control | ACTIVE |

## 5. Non-Independent Engine Rule

No Engine may:
1. create a second production ranking;
2. bypass Validation;
3. infer option type from symbol prefixes;
4. invent missing market/economic inputs;
5. alter Six-Block weights or Overlay constants without approved provenance;
6. send an independent Bale analysis;
7. convert Shadow evidence into production status without a gate.

## 6. Current Control Gates

- Gate 2: VERIFIED
- Gate 3: VERIFIED
- Gate 4: PENDING — exact option instrument identity
- Gate 5: Shadow / Replay / Audit architecture verified; economic opportunity-quality validation remains separate
- Gate 6: CLOSED — deployed Termux + real Bale receipts
- Gate 7: NOT CLOSED

## 7. Current Bottleneck Order

1. Scoring Overlay parameter provenance
2. Exact TSETMC option identity
3. Source freshness evidence
4. Historical Sensitivity / Ablation Audit
5. Economic validation of Opportunity Intelligence
6. Gate 7 cutover decision

No item above authorizes guessed parameters or premature production activation.

## 8. Evidence Policy

Repository state, CI results, Termux runtime evidence and Bale receipts are distinct evidence classes.

A repository/CI PASS does not substitute for physical runtime evidence.

Current deployed-runtime closure is evidenced by Gate 6:
- Bale delivery: SUCCESS
- 2 delivered messages
- receipts: message_id 1143 and 1144
- chat_id 770429773
- secrets_recorded=false
- launcher result: TERMUX_GATE6_OK COMMIT=e73168b5d3496fa14d388cddb5aa3ecd5e5278fc

## 9. Architectural Principle

OptimusAI is treated as an organization of specialized analytical units:
- Orchestrator = management and control
- Engines = specialized departments
- Brain / Intelligence = analytical interpretation
- Memory = institutional experience
- Red Team = challenge and error detection
- Audit = independent evidence and integrity
- Bale = distribution channel, not an analytical department

Production authority flows through the controlled chain; evidence flows back to Audit and Memory.
