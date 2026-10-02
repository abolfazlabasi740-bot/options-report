# G7-5 TSETMC Case-Family Mapping V1

Status: DIAGNOSTIC / PARTIAL. This mapping supplements but does not silently amend the frozen OptionSchool-derived G7-5 protocol.

## Evidence basis

The retained TSETMC archives are the only operational source. In the two inspected snapshots (2026-10-01T19:01:05Z and 2026-10-02T00:57:32Z), each had 1,684 rows. The following TSETMC fields were populated in both: remaining calendar days, best bid/ask prices and sizes, trade value, volume, underlying price, closing price, strike, and expiry. The inspected snapshots had zero populated values for Black-Scholes difference/value, implied volatility, delta, gamma, vega, rho, theta, and direct breakeven fields. Therefore no Black-Scholes or Greeks proxy is invented.

## Supported diagnostic families

All thresholds are calculated cross-sectionally from the entry snapshot only. Forward labels come from the next retained TSETMC snapshot matched by exact instrument ID. The forward label is positive option last-price change (OBSERVED_CONFIRMED) or non-positive change (OBSERVED_NOT_CONFIRMED); missing prices remain UNRESOLVED.

- BREAKEVEN_COMPRESSION_TSETMC_PROXY: option-derived breakeven distance in the entry-snapshot lowest quartile.
- LIQUIDITY_CONFIRMED_TSETMC_PROXY: both trade value and volume are at or above their entry-snapshot 75th percentile.
- NEAR_EXPIRY_RISK_TSETMC: remaining calendar days in the entry-snapshot lowest quartile; risk flag only.

Confusion counts are descriptive diagnostics comparing case membership with the independent next-snapshot option-return label. They do not prove causality, expected return, probability of profit, or a profitable strategy.

## Coverage-only families

- BASE_BREAKEVEN_CONTEXT_TSETMC: reports whether underlying price, strike, and option last price are all present.
- CALL_PUT_STRUCTURE_AVAILABLE_TSETMC: reports whether both CALL and PUT exist for the same underlying ID, expiry, and strike.

These are structural coverage measures, not performance predictions.

## Unsupported families

- RELATIVE_VALUE_ANOMALY: unsupported in these archives because Black-Scholes difference/value and IV fields are missing.
- CHAIN_STRUCTURE_ANOMALY: unsupported until a reproducible anomaly rule and member-score definition are independently frozen.

## Release boundary

This mapping produces partial research evidence only. Global G7-5 remains OPEN. No production signal, BUY/SELL action, or strategy authorization follows from these diagnostics. The original frozen protocol remains authoritative for full G7-5 closure.
