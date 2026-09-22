# Audit Remediation — OptimusAI V4.1

## Scope

این سند یافته‌های بررسی حسابرسی اولیه کد و شواهد CI را به کنترل قابل آزمون تبدیل می‌کند. این سند تأیید بهره‌برداری Termux/Bale یا تأیید کیفیت اقتصادی فرصت‌ها نیست.

## Findings

### AUD-01 — Shadow analytical failure isolation

Production report generation must not stop because an experimental Shadow analytical stage raises an exception.

Policy:
- Shadow runtime failure is recorded as `status=FAILED`.
- Production scoring/report path continues.
- Replay/Integrity failures remain blocking.
- A Shadow failure is never relabeled as Shadow success.

Acceptance:
- Regression test proves a synthetic Shadow exception still produces a Production report object.
- Audit explicitly records the nonblocking Shadow failure state.

### AUD-02 — Replay baseline binding

Replay must be compared with the actual Shadow analytical case artifact generated for the same snapshot.

Implementation:
- Baseline hash is calculated from the persisted analytical case artifact scope.
- Two fresh replay executions are compared to each other and to the baseline.
- Stateful memory/lifecycle wrappers are excluded from the deterministic analytical artifact and remain separately auditable.
- Replay scope is explicitly declared as `ANALYTICAL_CASE_ARTIFACT`.

Acceptance:
- Baseline mismatch produces `REPLAY_MISMATCH`.
- Deterministic match requires baseline/first/second hashes to agree.

### AUD-03 — Audit integrity

Audit now fails closed when:
- source hash and recomputed source hash differ;
- report hash is absent;
- selected_count differs from the selected artifact length;
- replay baseline/hash evidence is missing when Shadow replay is applicable.

### AUD-04 — Atomic report/audit publication

Report, Shadow, Replay, Historical Diff and Audit artifacts are staged as temporary files.

Publication occurs only after Audit Integrity returns PASS.

Therefore a failed final integrity check cannot leave a newly published report beside an older Audit artifact.

### AUD-05 — Bale provenance binding

Bale runtime verification now requires:
- report SHA in the Audit;
- report file SHA equals Audit report SHA;
- source file exists under the deployed data directory;
- source file SHA equals Audit source SHA;
- recorded/recomputed source hashes agree;
- Audit Integrity is PASS;
- Bale receipts contain message ID and the configured destination chat ID.

The delivery evidence records the verified source/report relationship without recording secrets.

### AUD-06 — Durable Bale update offset

The listener persists `next_offset` atomically after successful processing.

Rules:
- successful report delivery commits the offset;
- successfully delivered fallback error response commits the offset;
- failed processing/delivery does not advance the offset;
- restart loads the last committed offset.

This gives at-least-once processing semantics and prevents an uncommitted update from being silently skipped.

## Non-go-live items

The following remain independent gates:
1. Physical Termux execution with real environment variables and real Bale receipts.
2. Exact TSETMC option instrument identity in the live OptionSchool24 source.
3. Market-data timestamp/freshness validation.
4. Economic/financial validation of opportunity quality.

## Scoring protection

No Six-Block V4.1 scoring weight, production threshold, or ranking rule is changed by this remediation.

## Evidence rule

A remediation is considered closed only after:
- code is committed;
- regression workflow passes on that exact commit;
- live schema workflow passes where applicable;
- the relevant test/evidence is traceable to that commit.
