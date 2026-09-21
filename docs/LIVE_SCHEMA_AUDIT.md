# Live Schema Audit

## Purpose

live_schema_audit.py downloads the current OptionSchool24 export and records schema metadata only.

The tool records:
- retrieval timestamp
- workbook SHA-256
- row/column counts
- explicit source columns
- Underlying readiness
- Contract Type readiness
- expiry/strike readiness

It does not:
- infer CALL/PUT from symbols
- calculate parity
- alter Six-Block scoring
- persist the raw workbook as a Git-tracked artifact

## Execution

Local:

    python live_schema_audit.py

GitHub Actions:

.github/workflows/live-schema-audit.yml is workflow_dispatch only.

The live workflow is intentionally separate from the regression gate because external source availability should not make deterministic unit tests flaky.

## Interpretation

A live result of identity_readiness=INSUFFICIENT_DATA means the source does not expose the explicit fields required by Chain Identity. The system must keep Chain/Parity logic non-operative rather than infer identity from symbol text.

A live result is authoritative schema evidence for that retrieval snapshot; archived workbook evidence is historical context only.
