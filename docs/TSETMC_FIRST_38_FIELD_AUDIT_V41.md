# TSETMC-First 38-Field Audit — V4.1.1

Date: 2026-09-24
Scope: OptionSchool24 38-column live schema versus the currently implemented TSETMC evidence boundary.
Authority: evidence-only. This document does not activate TSETMC in production scoring/ranking.

## Executive conclusion

The current repository proves that TSETMC can supply the exact option/underlying identity boundary and the core market-watch/quote/order-book evidence required for a TSETMC-first architecture.

It does NOT prove that all 38 OptionSchool24 columns are raw TSETMC fields. The safe architecture is therefore:

TSETMC raw source -> OptimusAI canonical raw layer -> derived calculations -> Intelligence/Scoring

OptionSchool24 remains a benchmark/cross-check until the derived formulas are independently reconciled.

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
6. The active OptionSchool24 workbook boundary currently contains no accepted explicit TSETMC option-ID column in the inspected live workbook; therefore end-to-end row promotion remains blocked.

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
| 26 | حجم بهترین تقاضا | Raw | BestLimits demand quantity | VERIFIED boundary; live option-row capture pending |
| 27 | قیمت بهترین تقاضا | Raw | BestLimits demand price | VERIFIED boundary; live option-row capture pending |
| 28 | حجم بهترین عرضه | Raw | BestLimits offer quantity | VERIFIED boundary; live option-row capture pending |
| 29 | قیمت بهترین عرضه | Raw | BestLimits offer price | VERIFIED boundary; live option-row capture pending |
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

- No option ID is inferred from symbol, prefix, strike, expiry or CALL/PUT.
- No production TSETMC promotion occurs without an explicit option instrument ID and explicit underlying ID.
- TSETMC retrieval time is not treated as market observation time.
- Unknown fields remain UNKNOWN/OPEN; they are not filled with guessed formulas.
- OptionSchool24 values may be used for reconciliation, not as proof that a field is a raw TSETMC field.
- Production scoring/ranking remains unchanged until the field-level reconciliation is completed and independently evidenced.

## Current release impact

This audit closes the architectural question at the boundary level: a TSETMC-first raw-data layer is technically feasible and the exact option identity is available from TSETMC Option Market-Watch.

It does not close G7-1, G7-3, G7-4 or G7-5 by itself. In particular, G7-4 still requires an actual OptionSchool24 source row carrying an accepted explicit option ID, or a formally approved source replacement path that supplies that identity.

## Next implementation gate

The next technical gate is not more guessing. It is a real-source reconciliation run that captures, for the same option instruments:

1. TSETMC explicit option identity and underlying identity.
2. TSETMC quote and BestLimits payloads.
3. OptionSchool24 38 columns.
4. Field-by-field equality/tolerance results.
5. Formula/provenance evidence for every Derived/OPEN field.

Only after that evidence exists should the project consider replacing OptionSchool24 as a production dependency.
