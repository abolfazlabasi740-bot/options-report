# GO-LIVE GATE — OptimusAI V4.1

## Purpose

این سند معیار عبور پروژه از «توسعه Shadow» به «بهره‌برداری عملیاتی» را مشخص می‌کند. هیچ‌کدام از معیارها با حدس یا صرفاً وجود فایل در GitHub قابل PASS شدن نیستند.

## Gate 1 — Repository Integrity

- Six-Block V4.1 unchanged.
- Shadow analytical failures remain non-blocking; Replay/Integrity failures remain blocking.
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

Status: CURRENT CODE VERIFIED — regression run 35734232609 (run 349) on code commit 12265117de44da096f9caa854ef51704b57334d4 completed SUCCESS.

## Gate 3 — TSETMC-Only Active Source

Required:
- TSETMC is the only active market-data source.
- OptionSchool24 is historical/archive evidence only and is not a runtime fallback or reconciliation source.
- explicit option instrument ID and explicit underlying ID.
- source endpoint and retrieval timestamp.
- payload/raw evidence integrity.
- missing data is represented as «داده موجود نیست».

Status: **ACTIVE ARCHITECTURE — RUNTIME EVIDENCE CONTINUOUSLY REQUIRED.** No OptionSchool-derived data is permitted to unlock production scoring.

## Gate 4 — TSETMC Evidence


Required only when TSETMC enrichment is enabled:
- explicit option instrument ID
- explicit underlying ID returned by source
- exact underlying quote
- source endpoint
- retrieval timestamp
- payload SHA-256

Symbol inference is prohibited.

Status: **OPEN — LIVE VALIDATION PENDING.** Repository CI has verified the TSETMC source boundary and generated a live-source artifact, but the latest artifact is explicitly allowed to report NETWORK_UNAVAILABLE; therefore it is not claimed as live market evidence. BestLimits semantic mapping remains independently corroborated but not frozen.

## Gate 5 — Shadow Intelligence

Required evidence:
- Opportunity Shadow artifact
- Evidence Graph
- Multi-Factor Cluster
- Historical lifecycle artifact when persistence is enabled
- Historical confirmation/memory
- Historical Red-Team fusion
- deterministic hashes

Status: CURRENT CODE VERIFIED for analytical Shadow/Replay/Audit on live input. Replay reproduces the same Shadow-scored input artifact; TSETMC remains disabled until exact option identity is available. Deployed runtime execution is separately verified by Gate 6.

## Gate 6 — Bale Delivery

Required:
- same Report Engine output reaches Bale
- delivered report SHA equals the report SHA recorded and PASS-checked by Audit
- source SHA is reverified from the deployed source file before delivery
- no second analysis engine
- report timestamp/source identity preserved
- successful delivery log

Status: **HISTORICAL EVIDENCE — CURRENT DEPLOYMENT REVERIFICATION PENDING.**

The recorded Gate 6 evidence proves a prior deployed Termux → Bale delivery path, including:
- bale_delivery_status=SUCCESS
- bale_chunks=2
- non-secret Bale receipts
- TERMUX_GATE6_OK on commit e73168b5...

That evidence is retained as historical deployment evidence. It is not treated as proof that the current TSETMC-only commit is deployed and delivering.

## Gate 7 — Cutover

Production cutover is allowed only after Gates 2–6 have current evidence on the same deployed commit/runtime.

Until then:
- production Six-Block ranking remains the reference path
- Shadow analytical failures remain non-blocking; Shadow integrity/replay failures remain blocking
- no Buy/Sell signal is emitted
- no ranking is modified by historical memory or Red-Team evidence

Status: **NOT YET CLOSED.** Current blockers are:
- live TSETMC market evidence on the deployed runtime;
- time-locked BestLimits evidence package;
- semantic mapping review and Adapter Contract freeze;
- market-data freshness validation;
- economic/financial validation of opportunity quality;
- current deployed Termux → Bale evidence on the same TSETMC-only commit.

Six-Block production scoring remains OFF until these gates close.

## Current Assessment

Gate 6 is now operationally closed based on actual deployed Termux execution and real Bale receipts. This does not by itself constitute full V4.1 production cutover.

The remaining work is focused on:
1. live TSETMC capture on explicitly identified option instruments;
2. BestLimits time-locked evidence package and semantic review;
3. market-data timestamp/freshness validation;
4. economic/financial validation of Opportunity Intelligence;
5. current Termux deployment and Bale delivery verification on the same TSETMC-only commit;
6. only then final production validation of Six-Block ranking and V4.1 overlay on live data.

The Six-Block model is not being redesigned as part of the Gate 6 remediation.
