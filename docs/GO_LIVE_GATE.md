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

Status: VERIFIED — latest main regression run 35686797029 (run 271) on commit 56c99b866ab1aea96731c56221e7805a30a04912 completed SUCCESS.

## Gate 3 — Real OptionSchool24 Input

Required:
- fresh workbook captured
- source SHA-256 recorded
- schema captured
- row/eligibility counts recorded
- Report Engine completes without fabricated values

Status: VERIFIED — live run 35684027740 on commit f9a42f041d61db8a97e58f28cbc208463e585d4b captured a fresh workbook, source SHA-256, schema, 457-row universe, eligibility counts, successful Report Engine completion, Opportunity Shadow, replay and Audit PASS.

## Gate 4 — TSETMC Evidence

Required only when TSETMC enrichment is enabled:
- explicit option instrument ID
- explicit underlying ID returned by source
- exact underlying quote
- source endpoint
- retrieval timestamp
- payload SHA-256

Symbol inference is prohibited.

Status: architecture ready; live evidence pending.

## Gate 5 — Shadow Intelligence

Required evidence:
- Opportunity Shadow artifact
- Evidence Graph
- Multi-Factor Cluster
- Historical lifecycle artifact when persistence is enabled
- Historical confirmation/memory
- Historical Red-Team fusion
- deterministic hashes

Status: PARTIALLY VERIFIED — live run captured Opportunity Shadow, multi-factor clusters, deterministic replay and Audit PASS; TSETMC was disabled and historical persistence/Termux runtime remain separate gates.

## Gate 6 — Bale Delivery

Required:
- same Report Engine output reaches Bale
- no second analysis engine
- report timestamp/source identity preserved
- successful delivery log

Status: CURRENT CODE/CI HARDENING VERIFIED; deployed runtime still pending. Regression run 35704668186 on commit 822b30a8908d955ccacb3815901414e4c3ff9b3f completed SUCCESS. Live OptionSchool24 workflow 35704668179 on the same commit also completed SUCCESS and uploaded Gate 3 artifact 10683887197. `bale_runtime_verification.py` now records non-secret Bale message receipts (`message_id`/`chat_id`) and fails closed if a receipt is absent. This still does not substitute for executing the verifier on the deployed Termux instance.

## Gate 7 — Cutover

Production cutover is allowed only after Gates 2–6 have current evidence on the same deployed commit/runtime.

Until then:
- production Six-Block ranking remains the reference path
- Shadow intelligence remains non-blocking
- no Buy/Sell signal is emitted
- no ranking is modified by historical memory or Red-Team evidence

## Current Assessment

The project is structurally close to the operational gate, but repository completeness is not equivalent to live deployment. The remaining critical work is evidence collection and end-to-end runtime validation, not redesign of the Six-Block model.
