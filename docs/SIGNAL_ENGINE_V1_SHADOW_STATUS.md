# Signal Engine V1 — Shadow Status

## Purpose
The Signal Engine is currently a fail-closed shadow layer. It evaluates whether a ranked TSETMC candidate has the minimum identity, evidence, strategy-policy, and risk-policy state required for a future strategy decision.

## Current boundary
- Production BUY/SELL is disabled.
- Ranking score is not converted directly into a trading signal.
- Missing evidence blocks the candidate.
- Strategy and risk policies must be explicitly versioned before any future production decision.
- This layer does not claim expected return, probability of profit, or predictive validity.

## Next evidence requirements
1. Version and evidence the strategy policy.
2. Version and evidence the risk policy.
3. Establish independent outcome labels from historical observations.
4. Validate the signal logic out of sample before any production release gate is considered.

Until those items are independently evidenced, the output remains BLOCKED/WATCH and NOT_GENERATED.
