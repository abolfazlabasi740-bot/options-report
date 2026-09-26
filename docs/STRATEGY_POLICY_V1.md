# OptimusAI V4.1 — Strategy Policy V1

## Purpose

Define the controlled Strategy layer between Six-Block Ranking and Signal Gate.

This policy is intentionally fail-closed. It does not authorize a BUY/SELL action merely from ranking score.

## Policy identity

- strategy_policy_id: OPTIMUSAI-STRATEGY-V1
- version: 1.0.0
- status: SHADOW_ONLY
- production_authorized: false
- ranking_score_as_signal: FORBIDDEN

## Direction model

For a long-option strategy:

- CALL candidates can only produce BUY_CALL or WATCH/BLOCKED.
- PUT candidates can only produce BUY_PUT or WATCH/BLOCKED.

For a short-option strategy:

- CALL candidates can only produce SELL_CALL or WATCH/BLOCKED.
- PUT candidates can only produce SELL_PUT or WATCH/BLOCKED.

Short-option actions are NOT enabled by this policy version because a validated short-option risk policy and position/margin model are not yet present.

## Mandatory evidence gate

A candidate must have all of the following before any directional proposal can be considered:

1. explicit TSETMC instrument identity;
2. explicit TSETMC contract type;
3. valid underlying price;
4. valid option price reference;
5. valid strike;
6. valid expiry;
7. valid source market timestamp;
8. sufficient activity evidence to be an OPPORTUNITY_CANDIDATE;
9. ranking evidence;
10. no unresolved mandatory risk blocker.

Missing mandatory evidence means BLOCKED.

## Long-option directional logic

The policy does NOT yet assign economic thresholds for:

- acceptable premium burden;
- acceptable breakeven distance;
- acceptable leverage;
- acceptable expiry horizon;
- acceptable intraday range;
- acceptable liquidity;
- acceptable market movement.

Those thresholds must be derived/approved through historical validation rather than guessed.

Therefore V1 can produce only:

- WATCH when the structural evidence is complete but the economic policy threshold set is not yet released;
- BLOCKED when mandatory evidence is missing or a risk blocker exists.

It cannot produce a production BUY_CALL or BUY_PUT.

## Short-option logic

SELL_CALL and SELL_PUT remain BLOCKED until a separately versioned short-option risk policy establishes:

- maximum loss / collateral treatment;
- margin requirement evidence;
- assignment/exercise treatment;
- liquidity and exit requirements;
- expiry risk;
- position sizing;
- adverse movement controls.

No short-option signal is inferred from a low ranking score.

## Decision trace

Every evaluation must preserve:

- policy ID/version;
- candidate instrument ID;
- contract type;
- ranking rank/score;
- observed evidence;
- rule results;
- blockers;
- proposed state;
- snapshot SHA.

## Required future calibration

Before enabling directional BUY signals, the project must create replay/golden datasets from historical TSETMC evidence and measure:

- signal frequency;
- false-positive/false-negative behavior where labels are available;
- sensitivity to each threshold;
- stability across expiry buckets;
- stability across liquidity regimes;
- impact of missing evidence;
- out-of-sample behavior.

Thresholds must be evidence-derived and versioned. No fixed threshold is authorized merely because it looks reasonable.

## Current release decision

The only released strategy decisions are:

- WATCH: structurally eligible but directional economic thresholds are not released.
- BLOCKED: mandatory evidence/risk requirements are not satisfied.

Production BUY/SELL remains disabled.

