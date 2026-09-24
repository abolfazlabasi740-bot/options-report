# BestLimits Semantic Mapping Evidence — V4.1

Status: SEMANTIC_MAPPING_OPEN
Production use: BLOCKED
Last reviewed: 2026-09-24

## Scope

This document records the evidence state for the six raw BestLimits fields exposed by TSETMC-compatible feeds:

`zo`, `zd`, `pd`, `po`, `qd`, `qo`.

Raw capture is already supported by the TSETMC-first source layer. This document does not authorize semantic translation into Bid/Ask price, quantity, or order-count fields.

## Candidate hypothesis — quarantined

The current engineering hypothesis is:

| Raw field | Candidate meaning |
|---|---|
| `pd` | Bid price |
| `po` | Ask price |
| `qd` | Bid quantity |
| `qo` | Ask quantity |
| `zd` | Bid order count |
| `zo` | Ask order count |

This table is a TEST HYPOTHESIS ONLY. It is not an adapter contract and must not be used by production scoring.

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

## Current gate decision

BestLimits remains quarantined from canonical scoring.

No production field named Bid Price, Ask Price, Bid Quantity, Ask Quantity, Bid Order Count, or Ask Order Count may be synthesized from `zo/zd/pd/po/qd/qo` until the evidence chain is complete.

OptionSchool is not a permitted reconciliation source. Historical OptionSchool material is archive/evidence only and cannot close this gate.
