# OptimusAI V4.1 — Risk Policy V1

## Policy identity
- risk_policy_id: OPTIMUSAI-RISK-V1
- version: 1.0.0
- status: SHADOW_ONLY
- production_authorized: false

## Fail-closed mandatory blockers

A candidate is BLOCKED when any mandatory source/risk evidence required for the eventual strategy is unavailable or invalid.

Mandatory checks include:

1. explicit instrument identity;
2. explicit contract type;
3. underlying price;
4. option price reference;
5. strike;
6. expiry;
7. source market timestamp;
8. opportunity-candidate activity evidence;
9. deterministic ranking evidence;
10. freshness state compatible with the strategy run.

## Economic risk thresholds

The following values are intentionally NOT SET in V1:

- maximum premium burden;
- maximum breakeven distance;
- maximum leverage;
- minimum liquidity;
- minimum trade value;
- maximum intraday range;
- minimum time-to-expiry;
- maximum time-to-expiry;
- acceptable spread/depth threshold;
- position size;
- loss limit;
- exit threshold.

No numeric value may be inserted without replay/calibration evidence and policy versioning.

## Short-option risk

SELL_CALL and SELL_PUT remain blocked until collateral/margin, assignment, exercise, adverse-movement, position-size and exit controls are separately validated.

## Freshness

The runtime must distinguish:
- LIVE_TSETMC_REFRESH
- LAST_KNOWN_TSETMC_SNAPSHOT
- stale/unusable evidence

The production freshness threshold is NOT SET in V1 and therefore cannot authorize a production signal.

## Release rule

risk_policy V1 is SHADOW_ONLY and cannot authorize production BUY/SELL.
