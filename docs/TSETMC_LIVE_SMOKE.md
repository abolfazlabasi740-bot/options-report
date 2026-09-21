# TSETMC Live Smoke Evidence

tsetmc_live_smoke.py exercises only the TSETMC market-overview source boundary.

It records:
- source
- endpoint
- retrieval timestamp
- response payload SHA-256
- whether data was present

This is source-connectivity evidence only. It is not Termux runtime evidence, and it does not activate TSETMC fields in scoring or ranking.

The workflow is manual (workflow_dispatch) so external-source availability never makes the regression suite flaky.