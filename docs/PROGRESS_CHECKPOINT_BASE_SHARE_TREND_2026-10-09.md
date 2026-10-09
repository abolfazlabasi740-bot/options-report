# OptimusAI Base-Share Trend Report — Progress Checkpoint

**Checkpoint date:** 2026-10-09  
**Project:** `OptimusAI_V41_LIVE`  
**Repository:** `abolfazlabasi740-bot/options-report`  
**Branch:** `main`

## Verified state

- The Termux run completed with `STATUS = PLAIN_SYMBOL_TREND_REPORT_COMPLETE`.
- Source report rows: **2,062**.
- Eligible symbols after the rule “symbol must not end with an ASCII, Persian, or Arabic-Indic digit”: **753**.
- The full ranking is now stored in JSON: **753 rows**, and the check returned `STATUS: PASS`.
- Last ranked symbol printed by the verification: `مبین` (rank 753).
- Latest available historical market date: **2026-10-07 / 1405/07/15**.
- Buy/sell signal remains **OFF**.
- The terminal output displays only the top 15; JSON and TXT reports contain the full ranking.
- The fix was committed to `main` as commit `15b9ea8c4e9144051cf647432c9de976c9c8ceed`.

## Local report paths

- `output/base_share/latest_plain_symbol_trend_report.json`
- `output/base_share/latest_plain_symbol_trend_report.txt`

These report outputs were verified in the user's Termux environment. This checkpoint documents their state; it does not claim the generated output files themselves were committed to GitHub.

## Top 15 from the verified run

| Rank | Symbol | Score | Class | R5 % | R20 % | RSI14 |
|---:|---|---:|:---:|---:|---:|---:|
| 1 | سغدیر | 93.12 | A | 3.0949 | 0.4073 | 61.04 |
| 2 | غصینو | 93.07 | A | 2.2400 | 3.9024 | 60.87 |
| 3 | ثاخت | 92.22 | A | 0.5656 | 17.7483 | 67.89 |
| 4 | حپترو | 91.91 | A | 4.7114 | -4.4600 | 57.23 |
| 5 | وحافظ | 91.17 | A | 4.6363 | 2.6711 | 61.65 |
| 6 | دقاضی | 90.85 | A | 1.6479 | 13.7140 | 66.83 |
| 7 | خودرو | 90.74 | A | 6.3953 | -2.0080 | 60.32 |
| 8 | وتوکا | 90.44 | B | 6.8783 | 11.6022 | 69.57 |
| 9 | ولکار | 89.79 | A | 1.6636 | 2.4209 | 61.12 |
| 10 | دسبحا | 89.12 | A | 2.0862 | 4.2614 | 65.71 |
| 11 | غگل | 89.04 | B | 12.8843 | 15.7658 | 69.83 |
| 12 | کایتـا | 89.03 | A | 0.1212 | -0.6615 | 56.99 |
| 13 | غدیس | 88.85 | A | 14.8710 | 21.5088 | 67.61 |
| 14 | دسینا | 88.81 | A | 1.1310 | 12.7942 | 65.50 |
| 15 | شمس | 88.59 | A | -0.1609 | 10.8036 | 58.57 |

## Important limitations

- This is a historical trend ranking, not a buy/sell signal.
- Board/BestLimits live evidence, fundamentals, and news are not included in this report.
- Latest history date is 2026-10-07; this run does not establish live market conditions on 2026-10-09.
- No production buy/sell authorization has been made.

## Next step

Continue with the next phase: use valid TSETMC data in the next market session to assess board/volume and early-move evidence for the eligible base symbols, while preserving the fail-closed evidence rules. Do not repeat connection tests already completed.
