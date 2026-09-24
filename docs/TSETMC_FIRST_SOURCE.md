# TSETMC First Source — Evidence Contract

## Source boundary
The active option universe is obtained from the TSETMC option market-watch endpoint. The option-market-watch payload explicitly supplies put/call instrument IDs, underlying instrument ID, symbols, strike and expiry-related fields. The adapter expands only those explicit IDs into instrument records.

No external workbook is consulted by the active runtime.

## Quote evidence
For each selected instrument the runtime captures the raw TSETMC closing-price response and its SHA-256 evidence hash. Last price, close, volume, value, low and high are mapped only when the corresponding TSETMC field is present.

The TSETMC observation date/time fields are retained as source-market timestamp evidence. Adapter retrieval time is kept separately and is not substituted for the market observation time.

## BestLimits evidence
The runtime retrieves the TSETMC BestLimits response for every selected instrument and preserves:
- raw BestLimits payload
- endpoint
- retrieval timestamp
- payload SHA-256
- level count
- request status

At this stage the individual BestLimits fields are deliberately not translated into bid/ask semantic fields in the scoring layer. Public TSETMC-compatible implementations expose fields such as zo, zd, pd, po, qd and qo, but their semantic mapping must be frozen against the project's adapter contract before these fields can affect scoring.

## Missing-data rule
Missing or failed source evidence is never replaced with a value from another source and is never estimated. The canonical layer records the absence.

## Scoring gate
Six-Block scoring, ranking and trading signals remain disabled until the TSETMC field-evidence contract is complete and regression-tested.

## External technical evidence
The TSETMC-compatible implementation inspected during this gate documents the MarketWatch price columns and the BestLimits raw schema, including the eight BestLimits columns and the heven last-trade time field. These external references are technical evidence only and are not runtime data sources.

The active application remains dependent on its own TSETMC adapter and its captured raw evidence.