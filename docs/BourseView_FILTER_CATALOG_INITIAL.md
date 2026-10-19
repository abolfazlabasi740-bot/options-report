# BourseView Filter Research — Initial Catalog

**Research date:** 2026-10-19  
**Status:** Public-source reconnaissance; not yet implemented in the trading pipeline.  
**Purpose:** Identify BourseView filter families that can be reproduced independently in OptimusAI, with explicit source/data requirements and no invented formulas.

## Evidence standard

- "Documented example" means BourseView has publicly described the example.
- "Reproducible in principle" means the logic can be implemented if the underlying fields are available; it does not mean current OptimusAI data already supplies those fields.
- No filter should issue a trade recommendation until input freshness, field units, missing data, and historical performance are tested.
- Do not scrape authenticated/private endpoints or bypass access controls. Prefer public documentation and data sources with permitted access.

## Publicly documented filter examples

| Priority | Filter family | Publicly documented rule/capability | Implementation status | Data needed / caveat |
|---|---|---|---|---|
| P0 | Unusual trading value | BourseView's public example: today's trading value > 5 × the 30-day average trading value, while the 30-day average exceeds 1 billion tomans. | Formula is reproducible in principle; not implemented by this research note. | Daily value history, consistent currency/unit, completed-session treatment, corporate-action/calendar handling. |
| P0 | Investment companies below NAV | BourseView public example: investment companies trading below NAV and traded today, sorted by P/NAV. | Reproducible in principle. | Reliable current NAV and price; NAV timestamp; instrument classification; P/NAV calculation convention. |
| P1 | Advanced technical price fields | BourseView says its advanced screener includes weekly/monthly open, low, high, last trade and average closing price. | Field availability must be checked in OptimusAI before implementing filters. | OHLC/history by weekly/monthly timeframe; precise definition of average closing price. |
| P1 | Saved/custom advanced filters | BourseView publicly documents saving filters and selectable default columns. | Product feature, not itself a trading rule. | User-defined filter expressions and field dictionary; access/format must be verified. |
| P1 | Technical and fundamental screening | BourseView advertises advanced technical/fundamental screening and additional financial ratios. | Catalog needs exact field names/formulas before faithful reproduction. | Published formula guide and financial statement data; reporting period and restatement conventions. |
| P2 | Export revenue / monthly sales | Public product descriptions mention domestic/export split in monthly production and sales for relevant issuers. | Candidate for a separate fundamental/FX exposure module; not a confirmed screener formula. | Monthly Codal reports, export split, currency/settlement and realization evidence. |

## First implementation candidates

### BV-F01 — Unusual trading value
Proposed rule, matching the public example:
1. Calculate current session trading value in tomans.
2. Calculate the mean daily trading value for the previous 30 eligible sessions.
3. Select when current value > 5 × that mean AND the 30-session mean > 1,000,000,000 tomans.
4. Return both ratios and raw values, data timestamp, and missing-data status.
5. Do not evaluate a partial session as if it were a completed day; if intraday use is later desired, compare against time-of-day-normalized historical values as a separately validated variant.

### BV-F02 — Investment company P/NAV
1. Restrict to verified investment-company instruments.
2. Require a current price and timestamped NAV.
3. Calculate P/NAV using a documented convention.
4. Select P/NAV < 1 and traded-today, then sort ascending.
5. Mark stale/missing NAV as unavailable; never substitute an estimated NAV silently.

### BV-F03 — Weekly/monthly price structure
Expose weekly/monthly OHLC and closing-price-derived fields only after their definitions and source coverage are confirmed. Candidate derived checks include close above prior-period high and last price near the period high, but these are OptimusAI proposals, not claims about BourseView's proprietary preset filters.

## Integration plan

1. Inventory the existing OptimusAI data schemas and identify which fields are already available.
2. Add a field-mapping table: BourseView concept → exact definition → OptimusAI source → unit → timestamp → validation.
3. Implement BV-F01 and BV-F02 as pure, independently testable functions only when required fields exist.
4. Add fixtures for boundary cases, missing/stale data, units, zero denominator, and partial session.
5. Backtest with point-in-time data before allowing rankings to affect reports.
6. Preserve provenance: label each rule as "publicly documented reproduction", "independently designed proxy", or "requires proprietary access".

## Public sources checked

- BourseView public Telegram channel, example for unusual trading volume/value and P/NAV investment-company screening: https://t.me/s/bvhelp?before=152
- BourseView public channel, advanced screener weekly/monthly price fields and saved-filter capability: https://t.me/s/bvhelp/157
- BourseView public channel, overview of technical/fundamental screening and export/domestic monthly sales split: https://t.me/s/bvhelp?before=157

## Explicit limitations

- This is an initial public-source catalog, not a complete inventory of every filter shown behind a BourseView account.
- No authenticated BourseView session or proprietary API response was accessed.
- No live data values or filter performance are claimed.
- The rules in this document are not yet connected to the live OptimusAI ranking/report pipeline.


## Expanded public filter formulas — verified from BourseView's public channel

The following are exact expressions or close faithful transcriptions published by BourseView. They are reference rules, not validated trading signals. Field names are shown in BourseView's published English syntax.

### BV-F04 — Strong monthly revenue performance
```
Revenue Growth Rate 1M > Revenue Arithmetic Average Growth Rate 3M
and Revenue Growth Rate 1M > Revenue Growth Rate 1Y
and Average Value 30D > 30000000000
and Revenue Arithmetic Average Growth Rate 3M > 0%
```
The published example uses an average 30-day value threshold of 30 billion rials (3 billion tomans). Other posts show 10 billion rials (1 billion tomans), so thresholds must be versioned rather than treated as a universal preset.

### BV-F05 — Strong quarterly revenue growth
```
Revenue Growthrate QoQ > 10%
and Revenue Growth Rate YoY > 100%
and Average Value 30D > 30000000000
```

### BV-F06 — Improving operating profit margin
```
Operating Profit Margin MRQ Growth Rate QoQ > 0%
and Operating Profit Margin MRQ Growth Rate YoY > 0%
and Average Value 30D > 30000000000
and Operating Profit Margin TTM > 30%
```
A separate published example uses Net Profit Margin TTM > 20% with the first three conditions. Keep these as distinct variants.

### BV-F07 — Monthly sales growth with low monthly P/S
```
Revenue Year to Year Growth Rate 1m > 40%
and Revenue Growth Rate 1M > Revenue Growth Rate 3M
and Revenue Growth Rate 1M > Revenue Growth Rate 1Y
and P to S Monthly < 2.5
and Average Value 30D > 10000000000
```
Another published version compares monthly revenue growth with the arithmetic average growth rate over three months and uses a liquidity threshold. Preserve the exact variant and date/source.

### BV-F08 — Oversold RSI with a liquidity floor
```
Average Value 30D > 30000000000
and Relative Strength Index < 30
```
This is an oversold screen, not automatically a buy signal. In a falling market, RSI can remain below 30.

### BV-F09 — Large drawdown from the 200-day high
```
High Percent 200D < 0.5
and Average Value 30D > 10000000000
```
This identifies instruments trading below half of their 200-day high, with a liquidity filter; it can select distressed or structurally impaired instruments and needs a separate risk screen.

### BV-F10 — Unusual trading value
The public example describes today's trading value greater than five times the average trading value over the last 30 sessions, while that average exceeds 1 billion tomans. Convert units carefully: 1 billion tomans = 10 billion rials. This example should not be confused with other public screens that use 10 or 30 billion rials.

### BV-F11 — Investment companies below NAV
Select verified investment companies that traded today and have P/NAV < 1; sort by P/NAV ascending. Exact field formula and NAV freshness still require confirmation.

### Source references
- BourseView official public channel, unusual trading value and P/NAV examples: https://t.me/s/bvhelp?before=152
- Strong monthly/quarterly revenue, operating margin and technical filters: https://t.me/s/bvhelp
- Monthly P/S and 200-day drawdown examples: https://t.me/s/bvhelp?after=212
- RSI < 30 example: https://t.me/s/bvhelp/274

## Actual source-coverage check against current repository file

Reviewed `data/tsetmc.py` on `main`. This module currently extracts instrument identifiers and labels (`ins_code`, `isin`, `symbol`, `title`) from MarketWatchPlus and writes classified instrument lists. It does **not** currently calculate or store price history, daily traded value, 30-day averages, RSI, 200-day highs, revenue growth, operating margins, P/S, NAV, or buyer/seller cash-flow metrics. This is a module-level finding, not a claim that no other project file could contain related data.

Therefore, none of the filters above can responsibly be declared production-ready from this module alone. The immediate blocker is the field/data layer: identify existing historical and fundamental data modules first, then source missing fields. No live filter execution or live market data is claimed.

## Revised execution order

1. **P0 — Source inventory:** search all repository modules for existing price/history/fundamental inputs; do not duplicate existing work.
2. **P0 — Field map:** for each filter, record exact field definition, unit (rial/toman/percent), source, timestamp, missing-data policy and history depth.
3. **P1 — Market-data filters:** implement unusual value, RSI and 200-day drawdown only after valid historical price/value data exists.
4. **P1 — Fundamental filters:** implement monthly/quarterly revenue, margins and P/S only after point-in-time Codal data or an authorized API feed is available.
5. **P1 — P/NAV:** require verified instrument type and timestamped NAV; stale NAV must fail closed.
6. **P2 — Backtest:** validate early-warning lead time and false-positive rate using point-in-time snapshots before ranking integration.


## Cross-repository audit — existing reusable components

The initial file-level note above was intentionally scoped to `data/tsetmc.py`. A follow-up search of the wider repository found reusable components, so these filters should not be rebuilt from scratch:

- `tsetmc_adapter.py`: explicit TSETMC source adapter methods for instrument quotes, order book, client type and daily history; raw payloads retain endpoint, retrieval timestamp and SHA-256.
- `underlying_trend_engine.py`: calculates daily-history features including SMA 5/10/20/50, RSI-14 (Wilder), MACD 12/26, ATR-14, 5/20-session return, volume and traded-value ratios, 20-day breakout evidence and data freshness. This is descriptive/shadow evidence, not a production signal.
- `filter_engine_shadow.py`: reusable rule evaluator with ALL/ANY logic, explicit operators and fail-closed handling of missing values.
- `historical_snapshot.py` / `historical_pattern_shadow.py`: append-only snapshots and descriptive change/price-volume sequence analysis.
- `codal_export_engine.py`: a Codal monthly-activity evidence parser for disclosed export sales and currency details. This does not, by itself, establish that all monthly-revenue growth fields needed by the BourseView formulas are available.
- `docs/DATA_SOURCE_ARCHITECTURE.md` and `docs/TSETMC_DATA_SOURCE_REFERENCE.md`: canonical architecture and endpoint reference.

### Consequence for filter implementation

1. **RSI filter:** likely reusable from `underlying_trend_engine.py` after confirming the output schema, freshness and market-universe coverage. The 30-day average traded-value condition still needs a matching value-history feature; existing 5/20 value ratio is not equivalent.
2. **Unusual value:** the existing 5-session/20-session value ratio is not equivalent to today's value > 5 × the 30-session average. Reuse the history input and add a separately named exact 30-session calculation only after inspecting history coverage.
3. **200-day drawdown:** the existing trend engine computes a prior 20-day high, not the BourseView 200-day-high percentage. Do not substitute one for the other.
4. **Monthly/quarterly fundamentals:** use the existing Codal parser where its disclosed export data fits, but do not treat export parsing as a complete monthly revenue / quarterly financial-statement dataset.
5. **Rule evaluation:** reuse `filter_engine_shadow.py`; do not create a second generic filter engine. Add only a thin, tested mapping layer after the canonical input field definitions are agreed.

This narrows the next task from “build filters” to “inspect existing output schemas and prove field-by-field compatibility.” No production ranking or score has been changed.
