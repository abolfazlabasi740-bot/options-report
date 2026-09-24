# TSETMC-First 38-Field Audit — V4.1.1

Date: 2026-09-24
Scope: Historical 38-field reference versus the currently implemented TSETMC-only evidence boundary.
Authority: evidence-only. This document does not activate TSETMC in production scoring/ranking.

## Executive conclusion

The current repository proves that TSETMC can supply the exact option/underlying identity boundary and the core market-watch/quote/order-book evidence required for a TSETMC-first architecture.

It does NOT prove that all historical 38 fields are raw TSETMC fields. The active architecture is therefore:

TSETMC raw source -> OptimusAI canonical evidence layer -> derived calculations -> Intelligence/Scoring

Historical OptionSchool24 files are archive/evidence only. They are not an active source, fallback, reconciliation dependency, or mapping authority.

No production ranking, scoring, eligibility, Signal or Bale behavior is changed by this audit.

## Evidence already verified

1. TSETMC Option Market-Watch live payload contains explicit:
   - insCode_P
   - insCode_C
   - uaInsCode
   - lVal18AFC_P / lVal18AFC_C
   - lval30_UA
   - strikePrice
   - beginDate
   - endDate
   - remainedDay
2. The adapter normalizes these fields without inference.
3. Exact option instrument records preserve instrument_id, symbol, contract_type, underlying_id, underlying_symbol, strike, begin_date, end_date and remaining_days.
4. Quote boundary preserves pDrCotVal/pl, pClosing/pc, qTotTran5J/zTotTran, qTotCap and source observation timestamp when dEven/hEven are present.
5. BestLimits is implemented as an explicit TSETMC order-book boundary.
6. Historical OptionSchool24 material is outside the active runtime and cannot be used to promote or validate TSETMC rows.

## 38-field mapping

| # | OptionSchool24 field | Classification | TSETMC evidence / derivation | State |
|---|---|---|---|---|
| 1 | نماد | Raw | lVal18AFC_P / lVal18AFC_C | VERIFIED at option market-watch boundary |
| 2 | قیمت اعمال | Raw | strikePrice | VERIFIED at option market-watch boundary |
| 3 | قیمت سهم پایه | Raw via underlying | underlying_id -> quote pDrCotVal/pl | VERIFIED architecture; live row-level promotion pending |
| 4 | اختلاف تا اعمال | Derived | underlying price and strike | DERIVED |
| 5 | تاریخ سررسید | Raw | endDate | VERIFIED at option market-watch boundary |
| 6 | روزهای تقویمی | Raw/Derived | remainedDay or explicit date calculation | SOURCE AVAILABLE; convention to be frozen |
| 7 | روزهای معاملاتی | Derived | trading-calendar calculation | OPEN formula/source policy |
| 8 | موقعیت های باز | Raw/Source-specific | requires an explicit live TSETMC option field/source confirmation | OPEN |
| 9 | حجم معاملات | Raw | qTotTran5J / zTotTran boundary | VERIFIED |
| 10 | ارزش معاملات | Raw | qTotCap | VERIFIED |
| 11 | آخرین قیمت | Raw | pDrCotVal / pl | VERIFIED |
| 12 | درصد آخرین قیمت | Derived | last versus reference close/base convention | DERIVED; reference convention OPEN |
| 13 | قیمت پایانی | Raw | pClosing / pc | VERIFIED |
| 14 | درصد قیمت پایانی | Derived | close versus reference convention | DERIVED; reference convention OPEN |
| 15 | ارزش ذاتی | Derived | underlying, strike, contract type | DERIVED; contract-side convention must be explicit |
| 16 | ارزش زمانی | Derived | option price minus intrinsic value | DERIVED |
| 17 | سر به سر | Derived | option economics + contract type | DERIVED; formula must be frozen |
| 18 | اختلاف تا سر به سر | Derived | underlying versus breakeven | DERIVED |
| 19 | بلک شولز | Derived | BS model inputs from source + frozen assumptions | DERIVED; assumptions/provenance OPEN |
| 20 | اختلاف تا بلک شولز | Derived | market value versus BS output | DERIVED |
| 21 | وضعیت | Derived/Policy | requires explicit mapping from moneyness/status convention | OPEN — mapping not approved |
| 22 | اهرم | Derived | price/underlying relationship; exact OptionSchool formula not yet proven | OPEN formula reconciliation |
| 23 | نوسان ضمنی | Derived | implied-volatility solve from option price/model | OPEN formula/model reconciliation |
| 24 | نوسان تاریخی | Derived | historical underlying returns/volatility window | OPEN window/source reconciliation |
| 25 | اندازه قرارداد | Raw/Source-specific | option contract specification; exact live field not yet captured in current adapter | OPEN |
| 26 | حجم بهترین تقاضا | Raw | BestLimits raw field exists; semantic mapping to demand quantity is not yet proven | OPEN — semantic mapping gate |
| 27 | قیمت بهترین تقاضا | Raw | BestLimits raw field exists; semantic mapping to demand price is not yet proven | OPEN — semantic mapping gate |
| 28 | حجم بهترین عرضه | Raw | BestLimits raw field exists; semantic mapping to offer quantity is not yet proven | OPEN — semantic mapping gate |
| 29 | قیمت بهترین عرضه | Raw | BestLimits raw field exists; semantic mapping to offer price is not yet proven | OPEN — semantic mapping gate |
| 30 | کمترین قیمت | Raw | quote priceMin | VERIFIED boundary |
| 31 | بیشترین قیمت | Raw | quote priceMax | VERIFIED boundary |
| 32 | شکاف قیمتی | Derived | best ask - best bid / frozen spread convention | DERIVED |
| 33 | وجه تضمین | Source-specific/Derived | exact TSETMC option collateral field or authoritative formula not yet captured | OPEN |
| 34 | دلتا | Derived | option model + explicit contract side | OPEN formula/model reconciliation |
| 35 | تتا | Derived | option model + time convention | OPEN formula/model reconciliation |
| 36 | گاما | Derived | option model + explicit contract side | OPEN formula/model reconciliation |
| 37 | وگا | Derived | option model + explicit contract side | OPEN formula/model reconciliation |
| 38 | رو | Derived | option model + interest-rate assumption | OPEN formula/model reconciliation |

## Hard rules

- No numeric option ID is inferred from symbol, prefix, strike, expiry or CALL/PUT.
- TSETMC numeric option instrument ID is the active identity boundary. Symbol text is not an identity resolver and is not used to manufacture or promote a TSETMC instrument ID.
- TSETMC retrieval time is not treated as market observation time.
- Unknown fields remain UNKNOWN/OPEN; they are not filled with guessed formulas.
- Historical OptionSchool24 values are archive/evidence only and are not used for active reconciliation or production mapping.
- Production scoring/ranking remains unchanged until the field-level reconciliation is completed and independently evidenced.

## Current release impact

This audit records the TSETMC-only boundary: a TSETMC-first raw-data layer is technically feasible and the explicit option identity is available from TSETMC Option Market-Watch.

It does not close the remaining evidence gates. In particular, BestLimits semantic mapping remains open and historical OptionSchool material cannot close that gate.

## Next implementation gate

The next technical gate is direct TSETMC evidence, not cross-source reconciliation:

1. TSETMC explicit option identity and underlying identity.
2. Raw BestLimits payload with instrument ID, timestamp, endpoint and hash.
3. Independent semantic evidence for zo/zd/pd/po/qd/qo.
4. Time-locked validation across multiple instruments and timestamps.
5. Regression fixtures including one-sided/zero-depth cases.
6. Explicit adapter contract and mapping freeze only after the evidence chain is complete.

Historical OptionSchool24 material cannot close this gate.
