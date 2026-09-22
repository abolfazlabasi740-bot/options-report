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

Status: VERIFIED — latest verified main regression run 35720706997 (run 307) on commit ea7f4618dfb3596fc5d1749c03551a2570bcf770 completed SUCCESS; job 106722691428; 148 tests passed.

## Gate 3 — Real OptionSchool24 Input

Required:
- fresh workbook captured
- source SHA-256 recorded
- schema captured
- row/eligibility counts recorded
- Report Engine completes without fabricated values

Status: VERIFIED — latest live run 35720706945 (run 43) on commit ea7f4618dfb3596fc5d1749c03551a2570bcf770 completed SUCCESS; job 106722690022. Fresh source SHA-256 0909c3bea9c8e868f636c24166eefea31a8bec954ee5a37628dddb9a3fccdb08; Audit PASS; selected_count=15; Opportunity Shadow SUCCESS; Replay MATCH.

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

Status: CODE/CI HARDENING VERIFIED; DEPLOYED RUNTIME PENDING. Latest repository regression run 35720706997 on commit ea7f4618dfb3596fc5d1749c03551a2570bcf770 passed 148 tests, including Gate 6 runtime-verification hardening.

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

The project is therefore at the evidence-collection stage rather than requiring redesign of the Six-Block model.
