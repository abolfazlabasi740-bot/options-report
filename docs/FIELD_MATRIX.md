# TSETMC Field Availability Matrix — v0.2

| Feature | Endpoint | Raw field | Derived | Status |
|---|---|---|---|---|
| Open | ClosingPriceInfo | pf | No | MAPPED |
| Last | ClosingPriceInfo | pl / pDrCotVal | No | MAPPED |
| Close | ClosingPriceInfo | pc / pClosing | No | MAPPED |
| Previous close | ClosingPriceInfo | py / priceYesterday | No | MAPPED |
| Low/High | ClosingPriceInfo | pmin/pmax | No | MAPPED |
| Trades | ClosingPriceInfo | zTotTran | No | MAPPED |
| Volume | ClosingPriceInfo | qTotTran5J | No | MAPPED |
| Value | ClosingPriceInfo | qTotCap | No | MAPPED |
| Order book | BestLimits | bestLimits (raw only) | No | SEMANTIC_MAPPING_OPEN |
| Real buy volume | ClientType | buy_I_Volume | No | MAPPED |
| Real sell volume | ClientType | sell_I_Volume | No | MAPPED |
| Real buy count | ClientType | buy_CountI | No | MAPPED |
| Real sell count | ClientType | sell_CountI | No | MAPPED |
| Real buyer per-capita | ClientType | derived | Yes | DERIVABLE |
| Real seller per-capita | ClientType | derived | Yes | DERIVABLE |
| Buyer power | ClientType | derived | Yes | DERIVABLE |
| Real volume flow | ClientType | derived | Yes | DERIVABLE |
| Real value flow | ClientType | derived | Yes | DERIVABLE |
| OI | Option source | TBD | Yes | NOT_VERIFIED |
| IV | Option source / model | TBD | Yes | NOT_VERIFIED |
| Greeks | Model | TBD | Yes | NOT_VERIFIED |
| Black-Scholes | Model | inputs required | Yes | MODEL |
| Break-even | Model | inputs required | Yes | MODEL |
| Leverage | Option source/model | TBD | Yes | NOT_VERIFIED |

## BestLimits governance note

Semantic mapping of the raw BestLimits fields zo, zd, pd, po, qd, and qo is unverified. Raw capture does not constitute semantic mapping. Proof is required before any field can enter the canonical scoring dataset.

Required evidence chain:

1. Capture the raw BestLimits payload with instrument ID, retrieval timestamp and payload hash.
2. Obtain an independently documented field interpretation from an authoritative TSETMC/API specification or reproducible same-timestamp cross-reference.
3. Validate the interpretation against multiple deterministic regression fixtures, including zero-depth/one-sided-book cases where available.
4. Freeze the mapping in an explicit adapter contract and test it.

Until this gate closes, BestLimits fields remain quarantined from scoring and no Bid/Ask/quantity/order-count semantic fields may be synthesized from them.