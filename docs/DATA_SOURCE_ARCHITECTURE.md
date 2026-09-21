# OptimusAI V4.1 — Multi-Source Data Architecture

## Decision

OptionSchool24 is not sufficient as the sole data source for the target FindChart-style opportunity intelligence model.

The production architecture will therefore be multi-source:

- TSETMC/TSE: canonical market-state, instrument identity, price history, intraday/market-watch and order-book evidence.
- OptionSchool24: option-specific calculated analytics already present in its export, including Black-Scholes-related fields, IV/HV, Greeks, breakeven and option-market fields.
- FindChart-style Feature/Pattern Layer: derived features, filters, pattern detection, persistence/novelty and opportunity cases built from the canonical multi-source dataset.
- Optional contextual sources: only after explicit validation and only when a feature cannot be sourced reliably from TSE/OptionSchool24.

## Why

The target model is broader than a static option ranking. Public FindChart material shows option filters, combination filters, underlying-based option analysis, technical/tableau filters, and strategy outputs. The model therefore needs historical and market-structure information in addition to the OptionSchool24 workbook snapshot.

## Source Responsibilities

### TSETMC/TSE

Use as the market reference for:

- canonical instrument identity / instrument code
- option market-watch records
- paired call/put contract information where explicitly supplied
- strike and expiry where explicitly supplied
- last/close/trade volume/trade value/trade count
- best bid/ask and order-book depth
- daily and available intraday history
- market status / state changes
- client-type / حقیقی-حقوقی information where available
- base-share market data and history

TSETMC data must be keyed by instrument identifiers where available. Symbol text is never the canonical primary key.

### OptionSchool24

Use as the analytics enrichment layer for:

- Black-Scholes-related values
- IV and HV
- breakeven
- Greeks
- option-specific liquidity and contract fields
- fields that have no verified TSETMC equivalent

No OptionSchool24-only field is treated as a market-truth replacement for raw TSE market data.

### FindChart-style Derived Layer

Build from the canonical merged dataset:

- technical indicators
- price/volume/order-flow patterns
- option-chain structure
- relative value evidence
- market/base-share divergence
- persistence and recurrence
- multi-factor filters
- opportunity cases
- explanation and Red-Team evidence

The derived layer may reproduce observable behavior for validation, but it must not claim access to proprietary FindChart internals.

## Canonical Data Model

A future canonical record should support at least:

instrument_id
symbol
underlying_id
underlying_symbol
contract_type
strike
expiry
market_timestamp
last_price
close_price
volume
trade_value
trade_count
best_bid
best_ask
order_book_depth
open_interest
iv
hv
delta
gamma
theta
vega
rho
breakeven
black_scholes
client_type_flow
source_refs
snapshot_id

Fields are populated only from evidence-backed sources. Missing fields remain missing.

## Historical Requirement

FindChart-style pattern detection cannot be based only on the latest workbook.

OptimusAI must retain timestamped snapshots so that features can distinguish:

- new anomaly
- persistent anomaly
- strengthening anomaly
- weakening anomaly
- resolved anomaly
- recurring pattern

The history layer must not silently modify today's score. Historical information is an explicit feature/evidence input.

## Safety of Inference

The following are prohibited unless explicitly validated:

- inferring CALL/PUT solely from symbol prefix
- inventing underlying from symbol text
- generating IV/rate/dividend assumptions when required inputs are absent
- declaring parity/mispricing without validated economic inputs
- treating a FindChart-style pattern as a trade signal without the underlying evidence chain

## Implementation Sequence

1. Build and test a TSE source adapter.
2. Map TSE instrument identifiers to the OptionSchool24 export.
3. Construct the canonical multi-source snapshot.
4. Add base-share historical data and technical feature generation.
5. Add option-chain and market-structure features.
6. Run FindChart-style filters/patterns in Shadow mode.
7. Add persistence/novelty and Case Memory.
8. Validate against Golden datasets and observed FindChart outputs.
9. Only then consider controlled promotion of derived features into scoring/ranking.

## Current State

As of 2026-09-21:

- OptionSchool24 schema has been directly inspected for an archived real workbook.
- That archived workbook does not contain explicit Underlying or Contract Type fields.
- TSETMC integration is not yet production-active in the repository.
- Six-Block scoring remains unchanged.
- No TSETMC field should be treated as live-verified from this environment until a real runtime response is captured and hashed.