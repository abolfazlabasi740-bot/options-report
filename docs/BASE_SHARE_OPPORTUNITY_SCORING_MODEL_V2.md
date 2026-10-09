# Base Share Opportunity Scoring Model V2

## Status
- Version: BASE-SHARE-OPPORTUNITY-ENGINE-V2.0
- Source of truth: TSETMC only
- Purpose: rank evidence for an emerging/continuing move while separately penalizing poor entry quality
- Output is descriptive ranking only; it does not create a buy/sell instruction or enable automated trading.

## Weighted evidence families
| Family | Weight | Available evidence used |
|---|---:|---|
| Trend structure | 20% | trend state, last price vs SMA20/SMA50, SMA20 vs SMA50 |
| Price momentum | 15% | 5/20-session return, 1/3-session change |
| Technical quality | 15% | RSI14 with non-monotonic treatment, MACD12/26 sign, SMA5/SMA10 alignment |
| Volume/value confirmation | 15% | volume and traded-value ratios (5 sessions vs 20 sessions) |
| Early-move evidence | 15% | early-move change score, prior-20-session breakout, session-sequence state |
| Board/client-type | 10% | individual buyer power, buyer/seller counts and volume where available |
| Entry quality | 10% | RSI overbought penalty, recent price extension, price-rise/volume divergence, correction state |

## Important safeguards
- Missing values are omitted from the component denominator; no zero-filling, imputation, or guessed indicator values.
- Component coverage is reported separately from the score. Coverage is not a probability of success.
- RSI above 70 reduces entry quality; above 80 is flagged as extreme overbought. A strong existing trend cannot erase this entry-risk warning.
- A strong 5-session price run without supporting volume lowers entry quality.
- Current order-book/BestLimits fields are excluded until the independent semantic-evidence gate is passed. The existence of raw fields alone is not enough.
- Live board/client-type collection runs only during the TSETMC market window (Saturday–Wednesday, 09:00–12:30 Tehran time). Outside that window the report uses retained daily history and does not refresh live board data.
- Fundamental/industry context and historical Strategy Fit are explicitly marked unavailable/not scored in this version because they are not yet joined to this report with validated, comparable evidence.
- The report universe is currently limited to underlying shares explicitly linked to the current TSETMC options universe. It does not claim to rank the entire stock market.
- The score is a relative evidence score, not an expected return, calibrated probability, or trading signal.

## Output
Script: `base_share_opportunity_v2_report.py`
Engine: `base_share_opportunity_engine_v2.py`
Files: `output/base_share/latest_opportunity_v2_report.txt` and `output/base_share/latest_opportunity_v2_report.json`

## Release notes
- V2 adds separate component scores, evidence coverage, warning flags and missing-family disclosure.
- V2 prevents overbought RSI from automatically receiving a higher technical score.
- V2 keeps BestLimits quarantined and prevents after-hours live-board refresh.
