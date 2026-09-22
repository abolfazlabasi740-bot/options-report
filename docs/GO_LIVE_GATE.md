# GO-LIVE GATE — OptimusAI V4.1

## Purpose

این سند معیار عبور پروژه از «توسعه Shadow» به «بهره‌برداری عملیاتی» را مشخص می‌کند. هیچ‌کدام از معیارها با حدس یا صرفاً وجود فایل در GitHub قابل PASS شدن نیستند.

## Gate 1 — Repository Integrity

- Six-Block V4.1 unchanged.
- Shadow layers remain non-blocking.
- No secret/token committed.
- Regression workflow exists.
- Project status documents every material engine and limitation.

Status: READY FOR EXECUTION, not runtime-verified by repository inspection alone.

## Gate 2 — Automated Regression

Required command:

`python -m unittest discover -s tests -v`

Required evidence:
- workflow run ID
- commit SHA
- job ID
- final job status
- relevant test log or artifact

A code commit without workflow evidence is not a test PASS claim.

Status: VERIFIED — latest verified code/test run 35729976616 (run 318) on commit 70a8df16cb0c627d919c078849c9abb6851fd1d6 completed SUCCESS; job 106752837223; 150 tests passed.

## Gate 3 — Real OptionSchool24 Input

Required:
- fresh workbook captured
- source SHA-256 recorded
- schema captured
- row/eligibility counts recorded
- Report Engine completes without fabricated values

Status: VERIFIED — latest live run 35729976632 (run 54) on commit 70a8df16cb0c627d919c078849c9abb6851fd1d6 completed SUCCESS; job 106752837066; fresh source SHA-256 a4e80a58bd2c752de724806adbc514f858331f48109ce9df24c1eb9412318850; Audit PASS; selected_count=15; Opportunity Shadow SUCCESS; Replay MATCH; deterministic=true.

## Gate 4 — TSETMC Evidence

Required only when TSETMC enrichment is enabled:
- explicit option instrument ID
- explicit underlying ID returned by source
- exact underlying quote
- source endpoint
- retrieval timestamp
- payload SHA-256

Symbol inference is prohibited.

Status: architecture ready; live evidence pending. Current live OptionSchool24 data does not expose the explicit option instrument ID required by the integration, so TSETMC enrichment remains disabled by design.

## Gate 5 — Shadow Intelligence

Required evidence:
- Opportunity Shadow artifact
- Evidence Graph
- Multi-Factor Cluster
- Historical lifecycle artifact when persistence is enabled
- Historical confirmation/memory
- Historical Red-Team fusion
- deterministic hashes

Status: PARTIALLY VERIFIED — latest live execution demonstrated Opportunity Shadow, deterministic replay and Audit PASS. TSETMC enrichment remains disabled; historical persistence and deployed runtime execution remain separate validation dimensions.

## Gate 6 — Bale Delivery

Required:
- same Report Engine output reaches Bale
- no second analysis engine
- report timestamp/source identity preserved
- successful delivery log

Status: CODE/CI HARDENING VERIFIED; DEPLOYED RUNTIME PENDING. Latest verified code/test run 35729976616 on commit 70a8df16cb0c627d919c078849c9abb6851fd1d6 passed 150 tests, including Gate 6 runtime-verification hardening, repository-HEAD binding and the safe Termux deployment launcher.

Verified repository-side evidence:
- Regression run 35706552463 on commit 9572ffbd1816d81a9156b068e1ca768714cee72a completed SUCCESS.
- Live OptionSchool24 workflow 35706552454 on the same commit completed SUCCESS.
- `bale_runtime_verification.py` requests non-secret Bale receipts and fails closed when `message_id` is absent or `chat_id` does not match the configured destination.
- `gate6_runtime_verification.py` orchestrates Report Engine → Runtime Verification → Bale Delivery Verification and cross-checks report/source SHA-256 plus Bale receipts.

Gate 6 is NOT considered operationally closed until the orchestrator is actually executed on the deployed Termux runtime and its `output/gate6_runtime_evidence.json` shows PASS with real Bale receipts.

## Gate 7 — Cutover

Production cutover is allowed only after Gates 2–6 have current evidence on the same deployed commit/runtime.

Until then:
- production Six-Block ranking remains the reference path
- Shadow intelligence remains non-blocking
- no Buy/Sell signal is emitted
- no ranking is modified by historical memory or Red-Team evidence

## Current Assessment

The repository and CI gates are substantially verified. The remaining hard gate is physical/runtime evidence from the deployed Termux instance for Bale delivery. Gate 4 also remains pending because exact option instrument identity is not present in the current live OptionSchool24 source.

The project is therefore at the final runtime-evidence stage rather than requiring redesign of the Six-Block model.
