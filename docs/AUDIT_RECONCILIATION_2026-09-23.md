# Audit Reconciliation — Optionschool V4.1
Date: 2026-09-23

## Audit disposition

The submitted audit report was reviewed against the current main branch and the current V4.1 architecture. It is accepted as a useful audit input, but it is not accepted verbatim: several findings are stale or describe a previous implementation.

### Finding-by-finding disposition

| Finding | Disposition | Action |
|---|---|---|
| 1 — symbol filter after Top-N / percentiles | CONFIRMED | Fixed. For a symbol-scoped report, the validated symbol population is now selected before score_dataframe(), so cross-sectional percentiles are calculated only on that requested population. |
| 2 — text symbol matching must be replaced by TSETMC identity | PARTIALLY REJECTED AS STATED | Production OptionSchool input still does not provide an explicit TSETMC option ID. Exact TSETMC identity remains evidence-gated. No symbol/prefix/strike/expiry inference is introduced. Symbol filtering is a report-scope filter, not an identity promotion mechanism. |
| 3 — Status mapping ambiguous | CONFIRMED | Remains an explicit STATUS_MAPPING_NOT_APPROVED data/score flag. No numeric Status mapping has been invented. |
| 4 — Risk model is 0/5/10/20 Transitional | STALE / INCORRECT FOR CURRENT MAIN | Current canonical scoring path does not apply the described stepwise RiskPenalty. RiskPenalty remains 0.0 with KNOWN_GAP_THRESHOLDS_NOT_AVAILABLE. No undocumented risk thresholds will be introduced. |
| 5 — local/remote drift | OPERATIONAL CONTROL CONFIRMED | git pull --ff-only origin main remains the required deployed-runtime synchronization rule. G7-3/G7-4 evidence remains separately governed by the Gate 7 ledger. |
| 6 — terminal/environment hygiene | OPERATIONAL | Valid as a runtime procedure. No Bale token or chat identifier is changed by this remediation. |

## Implemented correction

report_engine.build_report() previously called score_dataframe(df) before applying symbol_prefix. That meant a symbol-scoped report inherited the full-market percentile population.

The production path now:
1. reads and schema-validates the source;
2. normalizes the source schema;
3. applies the requested symbol-scope filter;
4. calls the canonical score_dataframe() on that scoped population;
5. applies production eligibility;
6. ranks and selects Top-N.

The Shadow Opportunity path remains full-universe/evidence-only and does not mutate production FinalScore or ranking.

### Evidence

- Code commit: b1864e0dadfabd01c8ec519a45d5780976d76f00
- Regression-test commit: 5eb37f3b05c3272f23e3a78657f81fbc55b65dc4

A regression test now verifies both:
- the symbol-scoped score equals the canonical scorer applied to the scoped population; and
- the scoped score differs from the same contract's score when the full market is used, demonstrating that the percentile population is actually scoped before scoring.

## Identity boundary

The audit recommendation to replace text matching with insCode cannot be applied to the current OptionSchool production input without violating the project's no-inference rule. Exact TSETMC identity may only be promoted when an explicit option identifier and explicit underlying identifier are supplied and validated by the TSETMC evidence path.

The live Option Market-Watch evidence already demonstrates that TSETMC can return explicit insCode_P, insCode_C, and uaInsCode, but that evidence does not authorize inference for an OptionSchool row that lacks an explicit identifier.

## Governance boundaries retained

- No new Risk thresholds were invented.
- No Status mapping was invented.
- No TSETMC identity was inferred.
- No production TSETMC activation was introduced.
- No Bale secret values were modified.
- Gate 7 status remains controlled by the existing evidence ledger.