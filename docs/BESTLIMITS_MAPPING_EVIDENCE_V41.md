# BestLimits Semantic Mapping Evidence — V4.1

Status: SEMANTIC_MAPPING_FROZEN
Production use: ADAPTER_ONLY / SCORING_BLOCKED
Last reviewed: 2026-09-29

## Scope

This document records the evidence state for the six raw BestLimits fields exposed by TSETMC-compatible feeds:

`zo`, `zd`, `pd`, `po`, `qd`, `qo`.

Raw capture is already supported by the TSETMC-first source layer. This document does not authorize semantic translation into Bid/Ask price, quantity, or order-count fields.

## Frozen mapping contract

The reviewed evidence now freezes the following level-1 semantic contract:

| Raw field | Candidate meaning |
|---|---|
| `pd` | Bid price |
| `po` | Ask price |
| `qd` | Bid quantity |
| `qo` | Ask quantity |
| `zd` | Bid order count |
| `zo` | Ask order count |

This table is now the reviewed adapter contract for TSETMC BestLimits level 1. The contract is implemented in `tsetmc_bestlimits_mapping.py` as mapping version `TSETMC-BESTLIMITS-MAPPING-1.0`. This freeze does not unlock canonical scoring.

## Evidence currently available

### Semantic cross-reference found — candidate mapping strongly corroborated

A published TSETMC filter-variable reference explicitly defines the level-1 fields as:
- `pd1`: purchase/buy price
- `zd1`: number of buyers
- `qd1`: buy volume
- `po1`: sell price
- `zo1`: number of sellers
- `qo1`: sell volume

The same six-field definitions are independently reproduced by another TSETMC/PyTse reference. This is materially stronger than the earlier wire-schema evidence because the variables are tied to explicit market semantics, not merely their raw names.

The evidence therefore supports the candidate mapping:
`pd -> Bid Price`, `po -> Ask Price`, `qd -> Bid Quantity`, `qo -> Ask Quantity`, `zd -> Bid Order Count`, `zo -> Ask Order Count`.

However, these are third-party published references rather than an official TSETMC field-definition document. They therefore move the hypothesis from "unsubstantiated" to "independently corroborated", but do not by themselves authorize production freeze. A live time-locked TSETMC regression remains required.



A public implementation of TSETMC MarketWatch parsing exposes the six fields with the schema `zo, zd, pd, po, qd, qo` and preserves them as numeric raw fields. Its documentation also points to TSETMC pages for field-name meaning, but the implementation itself does not establish the semantic translation required by this project. Therefore it is evidence of wire format, not sufficient evidence of meaning. citeturn0search0turn0search1

A separate implementation exposes a reconstructed order-book representation using semantic names such as BidPrice, BidVolume, AskPrice, and AskVolume, but this is an independent implementation and is not treated as authoritative proof for the raw six-field mapping. It can be used only as a candidate cross-reference during the evidence phase.

## Required Evidence Chain

1. Raw payload
   - instrument ID
   - source endpoint
   - retrieval timestamp
   - payload SHA-256
   - raw six-field values
2. Independent semantic evidence
   - authoritative TSETMC/API documentation, or
   - reproducible same-timestamp cross-reference whose semantics can be independently established.
3. Time-locked validation
   - same instrument
   - same market timestamp
   - multiple levels where available
   - at least 3 option instruments
   - at least 1 underlying equity
   - multiple intraday timestamps
4. Regression
   - normal two-sided book
   - one-sided book
   - zero-depth level
   - repeated levels / updates
   - price ordering and type constraints
5. Freeze
   - explicit adapter contract
   - semantic mapping test
   - FIELD_MATRIX status changed to MAPPED only after evidence review.

## Important limitation

The invariant `AskPrice >= BidPrice` can reject an incorrect candidate mapping, but it cannot by itself prove which raw field is BidPrice or AskPrice. Likewise, positivity/non-negativity checks validate data shape, not field identity.

Therefore a 100% pass rate on the invariant harness is necessary evidence but is not sufficient evidence for Mapping Freeze.

## Reviewed live evidence — 2026-09-29

The live package `output/bestlimits_live_evidence.json` was reviewed after execution and numeric inspection.

Evidence package SHA-256:
`072d98da80b2ea68c5ea6c5212296686afdf7ac59f7e31213e392ca089de0b21`

Observed:
- 8 independent semantic evidence records.
- 3 option instruments and 1 underlying instrument.
- Two captures per instrument.
- All eight observations contain all six required semantic correspondences.
- All numeric correspondences matched exactly.
- Evidence timing deltas were 0.721736 to 0.797407 seconds, below the 2-second correlation limit.
- No gate errors were reported.
- Raw BestLimits payloads and SHA-256 values were preserved.

The live observations included both normal two-sided and one-sided/zero-depth cases. In particular, zero values on the offer side were preserved as zero and matched exactly; they were not treated as missing or estimated.

An independent technical reference also documents the same TSETMC field semantics at the raw-field level: `pMeDem` as best buy price, `pMeOf` as best sell price, `qTitMeDem` as best buy quantity, `qTitMeOf` as best sell quantity, `zOrdMeDem` as number of orders at the best buy limit, and `zOrdMeOf` as number of orders at the best sell limit. citeturn0search13

## Current gate decision

Semantic mapping is now frozen at the adapter-contract level.

Canonical scoring remains BLOCKED. No scoring weight, ranking rule, signal rule, or trading decision is enabled by this mapping freeze.

The next gate is regression validation of the adapter against the preserved live evidence and the existing test suite. Only after that gate passes can a separate governance decision be made about exposing BestLimits-derived fields to the scoring dataset.

OptionSchool is not a permitted reconciliation source. Historical OptionSchool material is archive/evidence only and cannot close this gate.
