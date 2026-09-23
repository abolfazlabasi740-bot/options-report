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

## Option Market-Watch Smoke — 2026-09-23

The manual smoke workflow now exercises both the existing market-overview boundary and the raw TSETMC option market-watch boundary. The option path writes `output/tsetmc_option_market_watch.json` and preserves the source endpoint, retrieval timestamp, payload SHA-256 and data-presence result. This remains source-connectivity/evidence collection only; it does not promote any option identity into the production canonical snapshot.
