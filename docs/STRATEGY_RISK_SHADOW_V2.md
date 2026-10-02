# OptimusAI V4.1 — Strategy/Risk Shadow V2

Status: SHADOW_VALIDATED
Production authorization: false

## Strategy
Long-option CALL/PUT candidates only. Entry eligibility requires at least 4 of 6 evidence-derived controls:
- breakeven distance <= training P50;
- trade value >= training P50;
- volume >= training P50;
- calendar days within training P25-P75;
- time-value ratio <= training P75;
- last-vs-close deviation <= training P75.

Thresholds are derived only from the chronological training portion of retained TSETMC replay data. The final 30% is independent OOS validation.

Mandatory runtime controls:
- exact instrument and CALL/PUT identity;
- valid underlying, strike, option price and expiry;
- explicit TSETMC source timestamp;
- freshness compatible with the run;
- spread evidence must be available; otherwise fail closed.

## Risk
- Short options remain blocked.
- Shadow maximum loss is limited to the premium committed to the shadow position.
- Shadow sizing is formula-based from an externally supplied risk budget and observed option premium; no capital amount is assumed.
- Exit/block conditions: expiry breach, freshness breach, mandatory evidence loss, liquidity failure or risk-limit breach.
- No averaging down is authorized.

The validation artifact is output/strategy_risk_shadow_validation.json. It contains train/OOS statistics and the evidence hash.

Production BUY/SELL remains disabled.
