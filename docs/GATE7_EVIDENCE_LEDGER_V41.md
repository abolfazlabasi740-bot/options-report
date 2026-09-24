# Gate 7 Evidence Ledger — V4.1

Date: 2026-09-23

## Verified evidence

| Gate | Evidence | Status |
|---|---|---|
| Gate 2 | Regression CI on main | VERIFIED |
| Gate 3 | Fresh OptionSchool24 source + Audit PASS + Replay MATCH | VERIFIED |
| Gate 6 | Physical Termux execution + Bale receipts | CLOSED |
| Gate 7 Control | Release-boundary CI + secret tracking check | VERIFIED |

## Open evidence

### G7-1 — Parameter provenance
Status: OPEN

The active V4 Overlay constants are observed from production code but do not yet have an authoritative protocol/decision or reproducible historical baseline recorded in the repository.

Required: evidence source for each affected numeric parameter family. No guessed replacement values.

### G7-2 — Historical sensitivity / ablation
Status: VERIFIED — EVIDENCE ARTIFACT HASH/PROVENANCE RECONCILED

The evidence-only implementation reuses the canonical V4.1.1 shadow scorer and performs one-block-at-a-time ablation. It does not modify Production FinalScore, eligibility, ranking, report or Bale output.

Termux evidence run:
- Files: 35
- Sheets: 35
- Sensitivity OK: 35
- Unresolved: 0
- Top-N: 15
- Source period: historical OptionSchool24 workbooks already present in the project; no new market session is required while the market is closed.

Aggregate sensitivity evidence across 35 records:

| Block | Mean Top-15 overlap | Mean rank changes | Mean max score delta | Mean score delta |
|---|---:|---:|---:|---:|
| Liquidity | 6.400000 | 449.142857 | 11.132857 | 3.603773 |
| Valuation | 10.000000 | 445.285714 | 9.042000 | 2.614506 |
| Payoff | 11.228571 | 442.485714 | 8.500000 | 2.127964 |
| Time | 11.514286 | 442.371429 | 7.409714 | 1.988990 |
| Greeks | 13.085714 | 432.000000 | 4.170286 | 1.151357 |
| Market | 12.600000 | 443.114286 | 6.042000 | 1.755308 |

Ranges retained from the same run:

- Liquidity: overlap 5–9; rank changes 237–472; max delta 10.26–12.22; mean delta 3.412690–4.033709.
- Valuation: overlap 8–13; rank changes 228–472; max delta 8.13–9.93; mean delta 2.347813–2.953458.
- Payoff: overlap 10–13; rank changes 227–466; max delta 8.14–9.36; mean delta 2.058977–2.550192.
- Time: overlap 8–12; rank changes 232–468; max delta 6.57–9.00; mean delta 1.725427–2.273042.
- Greeks: overlap 11–14; rank changes 215–461; max delta 3.52–4.31; mean delta 1.088222–1.216261.
- Market: overlap 11–13; rank changes 229–470; max delta 5.24–6.43; mean delta 1.709147–2.068159.

Interpretation boundary: these are sensitivity/ablation measurements only. They do not establish that any block, weight or economic direction is correct, optimal, predictive, or causally important.

Closure evidence has now been reconciled with the Termux run. The two generated evidence artifacts have verified SHA-256 values recorded below. The underlying run retained the real historical source files, source SHA-256 values, deterministic sensitivity measurements and unresolved-case accounting.

Artifact SHA-256:
- `g7_2_historical_sensitivity_evidence.json`: `702ed0de3a68abd2fc86be51165c29a64c9b02241857abcd1ba95d7059fe02fc`
- `g7_2_optionschool24_historical_evidence.json`: `d669d721de052c58a7b65b621759fe714fce1743553d99fb14123b4582fa3a5d`

The golden Gate 3 fixture is an output-regression baseline only; it is not historical economic validation.

### G7-3 — Market timestamp / freshness
Status: OPEN — SOURCE TIMESTAMP CAPTURE IMPLEMENTED, LIVE EVIDENCE PENDING

The TSETMC adapter now preserves an explicit source observation timestamp from `closingPriceInfo.dEven` + `hEven` when both fields are present and valid. This timestamp is explicitly treated as source observation time, not adapter retrieval time and not an inferred session-close time.

- Implementation commit: `c633fa9f04fd386cf8a7d35c5f86ebf748a9b526`
- Regression fixture/test commit: `eab12bcab93db3ff164ab86fe33a5a444191f9c0`
- Output fields: `source_market_timestamp`, `source_market_timestamp_status`.
- Missing/invalid source fields remain `UNAVAILABLE`; no timestamp is synthesized.
- External TSETMC references document `dEven` as YYYYMMDD and `hEven` as HHMMSS and identify `GetClosingPriceInfo/{InsCode}` as the current closing-price information endpoint.
- No freshness threshold has been introduced because no approved threshold/provenance exists yet.
- G7-3 therefore remains OPEN until a real runtime response demonstrates the field on the deployed data path and the stale/fresh policy is separately evidenced.


The current OptionSchool24 workbook path does not establish an authoritative market timestamp. Download time must not be treated as market time.

Required: source market timestamp or authoritative endpoint timestamp, with explicit unknown/stale handling.

Market-closure note: the absence of a new trading session does not itself create a market timestamp; it only means no new traded-market observation is expected during the closure interval.

### G7-4 — Exact TSETMC identity
Status: OPEN

The mapping implementation already enforces four states:
- EXACT_INSTRUMENT_ID
- SYMBOL_ONLY_CANDIDATE
- AMBIGUOUS
- NO_MATCH

Only EXACT_INSTRUMENT_ID may enter the canonical merged snapshot.

Current live OptionSchool24 evidence does not expose the explicit option instrument ID required for exact promotion. Symbol-prefix inference remains prohibited.

Required evidence: exact option identifier, exact underlying identifier, endpoint/source, retrieval time, payload hash, normalized mapping.

### G7-5 — Economic Opportunity validation
Status: OPEN — VALIDATION PROTOCOL FROZEN

A dedicated validation protocol has been added without introducing synthetic labels, new production thresholds, or ranking mutations.

- Protocol: `docs/G7-5_OPPORTUNITY_VALIDATION_PROTOCOL.md`
- Commit: `14aafd7ace775790a51f456c62f0e86783edd6bc`
- The protocol freezes case-family definitions, independence requirements, unresolved-case handling, false-positive/false-negative retention, and the evidence package required for closure.
- Current Opportunity Shadow `CONFIRMED/WATCH` statuses are explicitly not accepted as independent economic labels because they are derived from the same scored dataset under evaluation.

Required for closure: at least one real retained dataset with independently sourced outcome labels and reproducible provenance. No synthetic validation labels will be created.

Opportunity Shadow is technically executable and provenance-hardened, but technical execution is not economic validation.

Required: frozen case definitions, independent-vs-derived evidence separation, historical/observed validation, false-positive and unresolved-case retention.

### G7-6 — Final Gate 7 decision
Status: BLOCKED BY G7-1 through G7-5

No production Signal/Buy/Sell behavior is enabled by this ledger.

## Release boundary

The current operational product remains:

OptionSchool24
→ Validation / Schema Audit
→ Six-Block Scoring
→ Ranking / Top-N
→ Report
→ Audit
→ Bale

No scoring weights, Overlay constants, eligibility thresholds, ranking rules, TSETMC activation, or Bale logic are changed by this ledger.

## Evidence rule

Code existence, CI success, and Bale delivery are necessary operational evidence but do not substitute for economic/historical validation.

## Current conclusion

The operational reporter is deployed and verified. G7-2 is VERIFIED/CLOSED with reconciled artifact SHA/provenance evidence. The full OptimusAI intelligence cutover remains evidence-gated at Gate 7.

## Continuation Audit — 2026-09-23

A continuous repository/runtime audit was performed after the G7-5 protocol freeze.

- Current main head observed: `baddccde7f91f8730f1a43ecaeebc0584e4e78a8`.
- The TSETMC live-smoke workflow is present but intentionally `workflow_dispatch` only.
- The available GitHub integration does not expose a workflow-dispatch action, so no live TSETMC workflow execution is claimed from this audit.
- Direct TSETMC access from the current execution environment failed at DNS resolution; this is recorded as source-unavailable evidence, not as a market-data result.
- `tsetmc_evidence_collector.py` was inspected and confirmed to require an explicit option instrument ID and an explicit `underlying_id`; it does not infer identity from symbol naming.
- No TSETMC identity, market timestamp, or economic outcome label was fabricated from this limitation.
- G7-3, G7-4 and G7-5 therefore remain OPEN.
- G7-2 remains VERIFIED; its artifact hashes are already reconciled above.
- G7-1 remains OPEN because no authoritative provenance record for the active Overlay numeric constants has been found.
- G7-6 remains BLOCKED by the unresolved evidence gates.

This continuation audit changes no scoring, ranking, eligibility, TSETMC activation, or Bale behavior.


## TSETMC Option Market-Watch Expansion — 2026-09-23

A raw option-market-watch source boundary was added to improve the path toward G7-4 without making identity assumptions.

- Adapter commit: `a60c02fe354ae6bf5022b7c69422044a5412a8fb`
- Test commit: `eef540ee34ea96194add77c08a124ac240c38063`
- Documentation commit: `4027dc04fea9ee8649439d1f4bc2f03d6f8b8121`
- Endpoint: `Instrument/GetInstrumentOptionMarketWatch/{flow}`
- Behavior: preserve raw payload + endpoint + retrieval timestamp + SHA-256; no symbol-prefix inference and no unvalidated field mapping.
- The new path is evidence-only and does not modify production scoring, ranking, eligibility, TSETMC activation, or Bale output.
- No live response has been claimed from this environment. G7-4 therefore remains OPEN pending real source evidence and exact identity validation.


## Option Market-Watch Smoke Expansion — 2026-09-23

- `tsetmc_live_smoke.py` now supports `--option-market-watch --flow 1` and preserves the raw evidence metadata.
- Workflow commit: `f3b8278bf4456b98240fa5bcb16adaaa9e10cdfc`.
- Smoke script commit: `d9802ded14c37bb34117dcb096778c95b28b96dc`.
- Documentation commit: `a4b96d23317006681fe8e71df5ea70b47c420706`.
- No live workflow execution is claimed; the available GitHub integration does not expose workflow dispatch.
- G7-4 remains OPEN pending an actual source response and exact identity evidence.


## G7-4 Identity Boundary Audit — 2026-09-23

- Repository-wide identity search confirmed that accepted explicit option-ID aliases include `insCode`, `InsCode`, `instrument_id`, `InstrumentID`, `کد نماد` and `کد معاملاتی` at the mapping boundary.
- The Shadow TSETMC integration was aligned to the same alias set by adding `کد نماد`; this is a consistency fix only and does not infer identity from symbol text.
- Code/test commits: `a04a6b064f9c907d492de910722dd8a2b02b37cb`, `72ce36451af89f47426c1750940d685eb943e7fa`.
- Regression/workflow lookup for the latest test commit returned no associated workflow runs or commit statuses from the available GitHub integration; CI success is therefore not claimed for these commits.
- Repository evidence still shows the live OptionSchool24 report path uses source-local symbol identity because no explicit TSETMC option instrument ID has been recorded in the live path.
- The Option Market-Watch adapter preserves raw `insCode` when present, but no real live response has been obtained and retained in this audit.
- G7-4 remains OPEN. No option or underlying identity was inferred or promoted.


## G7-4 Live Evidence Capture Hardening — 2026-09-23

- The TSETMC live smoke utility was hardened to retain the raw Option Market-Watch response as a sibling evidence artifact and to count/list only explicitly returned `insCode`/instrument-ID fields.
- No symbol, prefix, strike, expiry, CALL/PUT, or underlying identity is inferred by this utility.
- Code commit: `83c6b987a05f473293e5f44795ad17629a219053`.
- Test commit: `e7e9def5a1961639e0531e82dd6a346bed79329a`.
- Current GitHub combined-status lookup for both commits returned an empty status list; CI success is not claimed.
- This hardening makes the next real Termux smoke execution capable of producing the raw evidence required to advance G7-4 and potentially G7-3, without activating TSETMC in production scoring.


## Continuation CI Verification — 2026-09-23

The latest main head `b59e1b526e4796f92a86175d456cd5233e8a9e07` was rechecked through GitHub Actions.

- `regression-tests`: run `35892765390` — completed `success`.
- `gate7-control`: run `35892765197` — completed `success`.
- The main branch now points to `b59e1b526e4796f92a86175d456cd5233e8a9e07`.
- These CI results validate repository regression/control boundaries only; they do not constitute Termux live TSETMC evidence.
- The controlled Termux command remains the only pending runtime action for collecting the raw Option Market-Watch evidence needed for G7-3/G7-4.
- No scoring, ranking, eligibility, TSETMC activation or Bale behavior was changed by this verification.


## G7-3/G7-4 Termux Live Smoke Evidence — 2026-09-23

User-provided Termux execution produced a real TSETMC Option Market-Watch response.

- Status: `SUCCESS`
- Test: `TSETMC_OPTION_MARKET_WATCH`
- Adapter version: `1.0`
- Retrieved at UTC: `2026-09-23T17:17:58.479447+00:00`
- Source: `TSETMC`
- Endpoint: `https://cdn.tsetmc.com/api/Instrument/GetInstrumentOptionMarketWatch/1`
- Snapshot SHA-256: `8a1bf7720c812a3f80af1b3df8b0eeaa79db57e77701000174a4ed66d8435d65`
- Data present: `true`
- Raw evidence file: `option_market_watch.raw.json`
- Explicit option `insCode` count: `0`

Interpretation: the live source path is reachable and returned data, but this particular response exposed no explicit option instrument IDs under the accepted evidence fields. Therefore G7-4 exact identity is NOT closed and no identity inference is permitted. The retrieval timestamp proves live observation of the endpoint, but does not by itself prove a market observation timestamp (`dEven/hEven`); G7-3 therefore remains open for source-market timestamp evidence.


## G7-4 Exact Identity Evidence — 2026-09-23

The real Termux raw Option Market-Watch payload has now been inspected. The response contains an explicit structured option record under `instrumentOptMarketWatch` with separate fields `insCode_P`, `insCode_C`, and `uaInsCode`, plus explicit option/underlying metadata.

Observed live evidence includes:
- `instrumentOptMarketWatch` list length: 541.
- First record explicit option identifiers: `insCode_P=68991773475135927`, `insCode_C=62444611500832644`.
- First record explicit underlying identifier: `uaInsCode=17914401175772326`.
- First record explicit source symbols: `lVal18AFC_P=طهرم7050`, `lVal18AFC_C=ضهرم7050`, `lval30_UA=اهرم`.
- First record explicit strike: `strikePrice=20000`.
- First record explicit expiry fields: `beginDate=20260725`, `endDate=20261021`, `remainedDay=28`.
- No symbol-prefix inference was used to obtain these identifiers; they are directly returned fields.

The smoke utility was updated to capture `insCode_P`, `insCode_C`, and `uaInsCode` as explicit identity evidence and to retain the complete raw response. The production scoring/ranking path remains unchanged.

- Smoke implementation commit: `6cfd4d40c962dfee4777eab3e60979892054349e`.
- Regression test commit: `f28c87a63db2d2e9933cc0bb53f92827f21162b4`.

Boundary: this evidence establishes that TSETMC returns explicit option and underlying identifiers in the live Option Market-Watch response. It does not by itself authorize production TSETMC activation, nor does it establish a market observation timestamp or economic outcome label. G7-3 remains OPEN pending explicit source-market timestamp/freshness evidence; G7-5 and G7-1 remain OPEN.


## External Audit Reconciliation — 2026-09-23

The external Optionschool V4 audit was reconciled with the current repository before applying remediation.

- G7 evidence gates were not altered by the audit reconciliation.
- The confirmed production defect was symbol-scoped percentile population: symbol filtering occurred after the scoring call. This is corrected in code commit b1864e0dadfabd01c8ec519a45d5780976d76f00.
- Regression coverage was added in commit 5eb37f3b05c3272f23e3a78657f81fbc55b65dc4.
- The audit request to replace source-local symbol filtering with TSETMC identity is not applied because the current OptionSchool production source does not expose an explicit TSETMC option ID. Exact TSETMC identity remains governed by the no-inference boundary and Gate 7 evidence path.
- The audit's described 0/5/10/20 RiskPenalty is stale for current main. The active scoring engine keeps RiskPenalty at 0.0 and marks KNOWN_GAP_THRESHOLDS_NOT_AVAILABLE; no thresholds were invented.
- Status mapping remains unapproved and unchanged.
- TSETMC remains non-production and Gate 7 status is unchanged by this remediation.
- Detailed reconciliation: docs/AUDIT_RECONCILIATION_2026-09-23.md.

## Scoped-Report History Integrity Correction — 2026-09-23

The audit remediation exposed a secondary integrity issue: historical snapshot records must remain source-wide even when the user requests a symbol-scoped report. Otherwise the same source SHA can generate conflicting record hashes.

- Corrected in code commit: 18fd26be90199c4e1f28dd3aa980d2220c9519dc.
- Regression coverage: 7884db3eac7a147cdd641ce805495195f0928bd7.
- The intermediate regression run 35896620856 failed before this correction because the existing test invoked two scopes against the same fallback source ID and historical record. The failure was inspected from the actual job log; it was not a scoring assertion failure.
- No Gate 7 status is changed by this correction. No CI success is claimed yet for the corrected head.

## Audit Remediation CI Verification — 2026-09-23

Corrected head `94c8800c76a592b62b384d4880e379a32b1c8993` passed all three validation workflows:

- Regression Tests: run `35896794682` — `success`.
- Gate 7 Control: run `35896794557` — `success`.
- Live Schema Audit: run `35896794677` — `success`.

This verifies the repository-level implementation/control boundary after the audit remediation. It does not by itself constitute live Termux evidence or close any open Gate 7 evidence requirement.


## G7-4 Adapter Normalization and CI Verification — 2026-09-23

The TSETMC adapter now provides an evidence-only normalized record layer preserving explicit Option Market-Watch identity fields (insCode_P, insCode_C, uaInsCode) together with explicit source metadata. This layer does not infer identity and is not connected to production scoring/ranking.

- Adapter implementation: ef5151c9b3b9ca160c9e37606123812eca798317.
- The first added regression test was rejected by CI because it referenced a nonexistent _adapter helper. The failure was inspected from the actual run logs.
- Corrected test/removal commit: 4d0027a3ba38dcf258c6b4294f58d74feedd702e.
- Regression Tests: 35902280979 — success.
- Gate 7 Control: 35902280876 — success.
- Live Schema Audit: 35902280821 — success.

The repository control boundary is green on the corrected head. This does not close G7-4: exact OptionSchool-row to TSETMC option ID to explicit uaInsCode to exact underlying quote remains to be proven on the deployed/live path. G7-3 freshness and G7-5 economic validation remain open.


## G7-4 Exact Identity CI Verification — 2026-09-24

The explicit-identity preservation fix at commit `e4700a7776ae99abaa0658aed9077a18ee53c5df` completed the required GitHub Actions checks successfully:
- regression-tests run `35904888387`: completed / success.
- gate7-control run `35904888382`: completed / success.
- live-schema-audit run `35904888379`: completed / success.
- Corresponding check-runs for the commit also completed successfully.

The fix preserves the explicitly returned TSETMC `underlying_symbol` field in mapping records and closes the regression failure found in the canonical exact-promotion test. This is CI evidence only; it does not constitute Termux deployment evidence and does not close G7-4 end-to-end because the active OptionSchool24 production workbook still does not retain an accepted explicit TSETMC option instrument ID.

Current boundary: exact TSETMC identifiers are proven in the live Option Market-Watch source, and the repository mapping/canonical layers preserve them correctly. End-to-end OptionSchool24-to-TSETMC exact promotion on the deployed runtime still requires a real OptionSchool source row carrying an accepted explicit option ID. Symbol/prefix/strike/expiry inference remains prohibited.


## G7-4 OptionSchool Explicit-Identity Readiness Control — 2026-09-24

An evidence-only readiness utility now checks the actual OptionSchool24 workbook for a populated accepted explicit TSETMC option-ID field before any cross-source promotion.

- Implementation: `f8b017c306990443f9e71423b4bec8b6e6c404e3`.
- Test: `975e251d73c2b5fdeae4ba3dc70640d2d4a7e7e0`.
- Runtime documentation: `ae35c1bdfa9aca2d3d047c4c653c24e5b24c5808`.
- Accepted aliases: `insCode`, `InsCode`, `instrument_id`, `InstrumentID`, `کد نماد`, `کد معاملاتی`.
- The utility distinguishes `NO_EXPLICIT_OPTION_ID` from `EXPLICIT_ID_AVAILABLE`, records the workbook SHA-256 and populated counts, and keeps identity inference disabled.
- Current GitHub workflow/status lookup returns no associated runs/statuses for these commits; therefore no CI success is claimed for this new control.

Acceptance remains unchanged: G7-4 cannot close until the deployed OptionSchool24 runtime produces a real source row carrying an accepted explicit option ID and the exact option→underlying evidence path is validated end-to-end. Symbol/prefix/strike/expiry inference remains prohibited.


## G7-4 Identity Key Clarification — 2026-09-24

The active OptionSchool24 schema does not expose the numeric TSETMC `insCode`, but `نماد` is an explicit source field and is the unique option name used by the source. TSETMC Option Market-Watch returns the same option symbol in `lVal18AFC_P` / `lVal18AFC_C`, together with explicit `insCode_P` / `insCode_C` and `uaInsCode`.

The evidence-only reconciliation rule is therefore deterministic exact symbol matching, not inference: both source snapshots must prove symbol uniqueness, the symbol must match exactly, and TSETMC's numeric option/underlying IDs are retained as authoritative metadata. Duplicate or missing symbols are blocked. Prefix, strike, expiry and CALL/PUT are never used to manufacture identity.

- Runner update: `76457fc860ffea36264b63046a08781057dc7cb6`.
- Regression coverage: `913526d95eb68008ee2b5a9c9635932809e6eb2d`.
- New identity state: `EXPLICIT_SYMBOL_MATCH`.
- Existing numeric-ID state remains `EXACT_ID_MATCH`.
- Production scoring/ranking/eligibility/Bale behavior is unchanged.

G7-4 is not closed by this code change alone. Closure still requires a real retained TSETMC snapshot reconciled with the actual OptionSchool workbook, with row-level field evidence and the explicit underlying linkage preserved.


## G7-4 Real Termux Unique-Symbol Reconciliation — 2026-09-24

User-provided Termux execution of the evidence-only reconciliation runner against a real OptionSchool24 workbook and retained TSETMC Option Market-Watch raw response produced:

- Workbook: `optionschool_20260922_174818_730899.xlsx`
- Workbook SHA-256: `78ef5ffe945138748076ee81694e8b1d0319dd5d79d8e50ff99c238934931693`
- Workbook dimensions: 478 rows × 38 columns
- Explicit OptionSchool numeric TSETMC ID: none
- TSETMC normalized instrument records: 1,082
- OptionSchool `نماد` unique: true
- TSETMC option symbols unique: true
- Exact unique symbol matches: 369
- Unmatched symbols: 109
- Ambiguous symbol matches: 0
- Match rate: 0.7719665271966527
- Identity inference: disabled

The initial runner returned `NO_SAFE_IDENTITY_MATCH` because its acceptance condition required complete 478/478 coverage. That result did not mean that the 369 exact matches were invalid; it meant full-snapshot promotion was withheld.

The runner has now been hardened to preserve the partial deterministic evidence:
- Implementation: `a79e2d9424ef57538910e9d6962b47da173f1bf1`
- Test: `e8d18d5aa597d2b719681b20ee4b574b051abc53`
- State for partial coverage: `PARTIAL_EXPLICIT_SYMBOL_MATCH`
- Unmatched rows remain blocked.
- Row-level evidence retains the exact OptionSchool symbol and corresponding explicit TSETMC option/underlying identifiers and source metadata.

GitHub combined-status lookup for both commits returned no associated status checks; CI PASS is not claimed.

Boundary: this evidence advances G7-4 identity readiness for 369 rows but does not close full G7-4. The remaining 109 symbols require source-level reconciliation before promotion. No prefix, strike, expiry or CALL/PUT inference is used.


## G7-4 lifecycle-analysis correction — 2026-09-24

The first Termux lifecycle summary for `output/g7_tsetmc/unmatched_symbols_v2.json` reported all 109 unmatched OptionSchool symbols as `EXPIRED_BEFORE_SNAPSHOT`. Repository audit identified a parsing defect in `scripts/analyze_unmatched_optionschool_symbols.py`: OptionSchool expiry values such as `1405/09/29` are Jalali dates, but the prior parser treated the year `1405` as Gregorian. Therefore that 109/109 lifecycle classification is invalid evidence and must not be used for Gate 7 closure or production filtering.

The analyzer has now been hardened to explicitly parse 13xx/14xx Jalali expiry values before Gregorian forms, and a regression test was added for `1405/09/29` against the retained TSETMC snapshot time `2026-09-23T17:17:58.479447+00:00`. The corrected implementation is committed in `a02bec0457901b727a0dcbe1be2b7fe3b213f176` and the regex correction in `976bc54b5c22de6ffff99361e961940cd183a5db`; the regression test is in `7a248860d628f65698da67d5e992bbf68e653a46`. No production scoring, ranking, eligibility, TSETMC activation, or Bale behavior was changed.

**Required next evidence:** rerun the corrected analyzer on the same retained workbook/snapshot and replace the invalid lifecycle result with the new exact status counts. Until that rerun is evidenced, G7-4 lifecycle analysis remains open.
