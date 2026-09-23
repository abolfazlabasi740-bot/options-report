# TSETMC Adapter — V4.1

## Scope

This is the first implementation step of the multi-source architecture. It is a source boundary only; it does not modify Six-Block scoring, ranking, Opportunity Shadow, or Bale output.

The adapter uses the TSETMC CDN JSON surface and preserves the raw response hash alongside normalized data. TSETMC instrument code is the canonical instrument key.

Implemented methods:

- instrument search
- instrument info
- instrument identity
- current quote
- order book
- client type
- daily price history
- market overview
- explicit canonical-instrument normalization

The endpoint inventory is based on independently documented/reverse-engineered TSETMC API references and may change at the source. Network/API failure is unavailable data, not a reason to synthesize values.

## Identity rule

These fields remain null unless explicitly returned by a validated source mapping:

- underlying_id
- underlying_symbol
- contract_type
- strike
- expiry

Persian option-symbol prefixes are not converted into CALL/PUT evidence.

## Evidence rule

Every successful response carries source, endpoint, retrieval timestamp and SHA-256 of the JSON payload.

## Deployment gate

Code in GitHub is not live verification. A real Termux execution must capture a successful response, endpoint, payload hash and normalized row before TSETMC is marked live-active.

## Next step

Build the TSETMC-to-OptionSchool24 mapping layer with four explicit outcomes:

- exact instrument identity match
- symbol-only candidate match
- ambiguous match
- no match

Only exact evidence-backed matches may enter the canonical merged snapshot.


## Option Market-Watch Evidence Boundary — 2026-09-23

- Added `TSETMCAdapter.option_market_watch(flow=1)` as a raw, evidence-preserving source method.
- Endpoint: `Instrument/GetInstrumentOptionMarketWatch/{flow}`.
- The method retains source, endpoint, retrieval timestamp, payload SHA-256 and the unmodified response payload.
- No option-side field is normalized from this endpoint yet; explicit field mapping remains a separate evidence task.
- A regression test verifies URL construction, payload preservation and deterministic evidence-hash presence.
- This method is non-blocking and does not modify scoring, ranking, eligibility or Bale output.
