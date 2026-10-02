# OptimusAI V4.1 — Project Completion Contract V2

Status: IN_PROGRESS. This document defines what "project complete" means. A successful report run alone is not completion.

## Release tracks

### Track A — TSETMC market scanner and option shortlist
Required:
- live/last-known source state is explicit;
- exact instrument identity and CALL/PUT semantics;
- deterministic economic ranking with missing data preserved as unavailable;
- retained snapshot and report hashes;
- audit-integrity PASS;
- runtime verification PASS;
- Bale delivery with a real message receipt;
- no unsupported buy/sell, expected-return, or probability-of-profit claims.

Current evidence: report/ranking PASS; expired and expiry-unknown contracts are excluded; underlying daily technical indicators and TSETMC order-book/client-type diagnostics are integrated for displayed candidates; runtime and audit PASS on 2026-10-02; Bale test delivery PASS with message receipt 1335. This is a working screening milestone, not the full project.

### Track B — Historical case-family validation
Required:
- reproducible case definitions;
- independent forward outcomes matched by exact instrument ID;
- confusion counts and unresolved counts per supported family;
- separate unsupported families, with no invented substitute fields;
- walk-forward and out-of-sample evidence;
- costs/slippage assumptions explicitly sourced or left unavailable.

Current evidence: latest captured run had 59 retained snapshots, 88,344 exact-ID transitions, 0 unresolved feature matches, and 6,270 walk-forward results. Three TSETMC proxy families have diagnostic confusion counts. Two families are coverage-only. RELATIVE_VALUE_ANOMALY and CHAIN_STRUCTURE_ANOMALY remain unsupported; global G7-5 remains OPEN.

### Track C — Underlying-stock trend and pre-limit-up screening
Required:
- underlying price/volume/market-depth history;
- technical indicators computed from retained, timestamped underlying observations;
- explicit board-reading features;
- label definition for "pre-limit-up" based on observable market events;
- chronological out-of-sample evaluation and false-positive reporting;
- no claims that a pattern predicts a limit-up unless validated.

Status: PARTIAL. Daily SMA/RSI/MACD/momentum/volume features and order-book/client-type diagnostics are now included for underlying stocks linked to the displayed option shortlist. A historically validated pre-limit-up event classifier and current-session limit-up alert rule are NOT RELEASED. The current report is not a pre-limit-up predictor.

### Track D — TSETMC market-context validation
Required:
- TSETMC-supported underlying trend and market-context features only;
- timestamped source evidence and reproducible calculations;
- explicit separation between descriptive market context and predictive claims;
- no dependency on news, Codal disclosures, or external issuer-event enrichment for project completion.

Status: IN_SCOPE. News review and Codal review are explicitly excluded from the approved completion scope and cannot block project completion.

### Track E — Strategy and risk release
Required:
- versioned CALL/PUT decision rules;
- evidence-derived thresholds;
- expiry/liquidity/spread/freshness controls;
- position sizing, max loss, and exit policy;
- independent validation before any production BUY/SELL authorization.

Status: SHADOW_ONLY. Production BUY/SELL remains disabled.

### Track F — Automation and delivery
Required:
- Finisher worker with singleton/process health evidence;
- automatic report, audit, evidence, and retry workflow;
- Bale notifications deduplicated by state change and verified by receipts;
- human intervention only for credentials, external account permissions, or explicit risk-policy authorization.

Status: PARTIAL. Bridge and a Bale test receipt exist. A rebase-safe state-push fix has been deployed and the Finisher worker restarted; successful completion of its next full cycle and Bale receipt remains to be verified.

## Completion rule

The full project is COMPLETE only when all tracks required by the approved scope have reproducible PASS evidence. Track A may be released independently as a screening product. A partial G7-5 diagnostic, a report PASS, a compile PASS, or a Bale test receipt alone never means the full project is complete.
