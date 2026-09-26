# OptimusAI V4.1 — Signal Engine V1 Specification

## 1. Objective

The final business objective of OptimusAI is production-quality option BUY/SELL signals.

The existing Six-Block Ranking is an upstream evidence-ranking layer. It is not itself a trading signal.

Canonical path:

TSETMC
→ Identity / Validation
→ Features / Evidence
→ Opportunity Candidate
→ Six-Block Ranking
→ Strategy
→ Decision Trace
→ Signal Gate
→ BUY / SELL / WATCH
→ Audit
→ Bale

## 2. Signal boundary

A ranking score may identify an attractive evidence profile, but it must not be converted to BUY or SELL by a hidden threshold.

The Signal Engine must consume an approved Strategy policy and a Decision Trace.

No undocumented economic threshold is permitted.

## 3. Signal vocabulary

The production signal vocabulary is:

- BUY_CALL
- BUY_PUT
- SELL_CALL
- SELL_PUT
- WATCH
- BLOCKED

The signal must also contain:

- signal_status
- signal_reason_codes
- instrument_id
- symbol
- contract_type
- ranking_rank
- ranking_score
- entry_reference
- risk_state
- expiry_state
- evidence_source
- snapshot_sha256
- generated_at

If an approved entry/risk reference cannot be produced from source evidence, the production signal remains BLOCKED or WATCH; a guessed price or threshold is forbidden.

## 4. Current evidence available in TSETMC V4.1

The active TSETMC path currently provides, where present:

- explicit option instrument ID
- explicit option contract type
- underlying price
- strike
- last price
- closing price
- volume
- trade count
- trade value
- high/low
- expiry
- explicit source market timestamp
- bid/ask quantity evidence where available
- ranking features derived from the above

The current production ranking does not compute IV or Greeks.

Open interest is not used by the current ranking contract.

## 5. Required Signal policy inputs

Before BUY/SELL production activation, the Strategy/Governance layer must explicitly close:

### Entry policy
Defines what observed evidence is sufficient for an entry and whether the action is BUY_CALL, BUY_PUT, SELL_CALL or SELL_PUT.

### Risk policy
Defines the conditions that block an entry because of liquidity, spread/depth, expiry, price quality, or other approved risk constraints.

### Exit policy
Defines when an existing signal becomes invalid, exits, or changes state.

### Expiry policy
Defines the minimum/maximum acceptable time-to-expiry and treatment of near-expiry contracts.

### Market policy
Defines how current market-state evidence affects signal authorization.

### Missing-evidence policy
Defines which missing fields are tolerable and which mandatory fields block a signal.

### Freshness policy
Defines the maximum acceptable age of market evidence for a live signal.

All such parameters must be versioned and regression-tested before production use.

## 6. Separation of BUY and SELL

BUY and SELL are not mirror labels.

BUY_CALL / BUY_PUT require an approved long-option entry policy.

SELL_CALL / SELL_PUT require an independently approved short-option policy because the risk model and required evidence are different.

Therefore a low ranking score must never automatically become a SELL signal.

Likewise a high ranking score must never automatically become a BUY signal.

## 7. Signal Gate

The Signal Gate must fail closed.

Production signal authorization requires:

1. exact TSETMC instrument identity;
2. valid current/last-known source state according to freshness policy;
3. valid Strategy policy version;
4. valid Decision Trace;
5. mandatory risk conditions passed;
6. mandatory evidence available;
7. deterministic signal result;
8. audit linkage to the same snapshot;
9. Gate 7 release state closed.

Any failed mandatory condition produces BLOCKED rather than an invented signal.

## 8. Shadow implementation path

The first implementation step is a deterministic Shadow Signal Engine.

Shadow output must be structurally complete but cannot affect production Bale output.

For every candidate it should record:

- eligible / blocked state;
- strategy-policy version;
- decision inputs;
- rule outcomes;
- blockers;
- proposed signal state;
- evidence references;
- snapshot hash.

This permits historical/replay testing without contaminating the live report.

## 9. Production activation rule

Signal production remains OFF until:

- Signal Engine contract is implemented;
- Strategy policy is versioned;
- Risk policy is versioned;
- deterministic regression tests pass;
- replay/golden cases are available;
- historical sensitivity/ablation evidence is recorded;
- economic validation is completed;
- Gate 7 is explicitly closed.

No arbitrary score cutoff such as “score >= X = BUY” is authorized by this specification.

## 10. Current state

Signal Engine: PENDING POLICY CLOSURE

Current report behavior remains:

Six-Block Ranking → Top-N → Audit → Bale

Current runtime must continue to report:

buy_sell_signal = NOT_GENERATED

until the above policy and release gates are closed.

## 11. Non-negotiable evidence rule

No signal may be created from:

- guessed IV;
- guessed Greeks;
- guessed open interest;
- external option data;
- symbol-prefix inference;
- an undocumented score threshold;
- a manually selected contract;
- a stale snapshot presented as live movement.

