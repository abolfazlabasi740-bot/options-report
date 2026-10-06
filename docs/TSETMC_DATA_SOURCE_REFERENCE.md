# TSETMC Data Source Reference

## Purpose

This document is the permanent operational reference for downloading and using TSETMC option-market data in OptimusAI. It exists to prevent repeated endpoint discovery and incorrect data-source assumptions.

## Repository / project

- Repository: `abolfazlabasi740-bot/options-report`
- Project runtime: `~/OptimusAI_V41_LIVE`
- Source of truth: TSETMC only
- OptionSchool is not an operational source.

## Confirmed option-universe endpoint

The validated source for discovering the option universe is:

`https://cdn.tsetmc.com/api/Instrument/GetInstrumentOptionMarketWatch/{flow}`

The project implementation is:

`TSETMCAdapter.option_market_watch_universe()`

Default flows:

`0, 1, 2, 4`

The implementation:
1. requests each flow;
2. takes identity from explicit `insCode_P` / `insCode_C`;
3. de-duplicates by `instrument_id`;
4. does not infer identity from symbol prefixes;
5. preserves per-flow evidence, endpoint, timestamp and SHA-256.

## Confirmed live retrieval

On 2026-10-06 the validated function returned:

- total unique option instruments: 1,834
- flow 0: 1,834 raw / 1,834 accepted unique
- flow 1: 1,324 raw / 0 new / 1,324 duplicates
- flow 2: 510 raw / 0 new / 510 duplicates
- flow 4: 0 raw
- retrieved_at: 2026-10-06T14:13:45Z

Evidence SHA-256 values:
- flow 0: `4b51743c75930d8ef0eb93eb517bf2fb1c44ce2b373a11708b4db165842ee846`
- flow 1: `21e1f73733b88f3582ae06bf7d2bdf40ff8c65af6796f1fc088e03024b2316a8`
- flow 2: `02c66448e541fc8f30a6515f1c5dfda0d3f2d7cc96c3f0a22ba0d8391a1ee09`
- flow 4: `6c8e1c788836e24e88a239a2a73f8005652c0d5da6f259ff28cdacd37c7ccc34`

## Fields confirmed available

Each option record can include:

- `underlying_id`
- `underlying_symbol`
- `strike`
- `begin_date`
- `end_date`
- `remaining_days`
- `instrument_id`
- `symbol`
- `contract_type` (CALL / PUT)
- `identity_source_field`
- `contract_size`

Market fields:
- `last_price`
- `close_price`
- `previous_price`
- `volume`
- `trade_count`
- `trade_value`
- `open_interest`
- `previous_open_interest`
- `bid_price`
- `ask_price`
- `bid_quantity`
- `ask_quantity`
- `notional_value`

Underlying market fields:
- `last_price`
- `close_price`
- `previous_price`

## Important endpoint distinction

Do NOT use `ClosingPrice/GetMarketWatch` as the primary option-universe source.

A direct request to:

`ClosingPrice/GetMarketWatch`

returned:

`{"marketwatch":[]}`

during the post-market test on 2026-10-06.

The project's option-universe endpoint above successfully returned 1,834 unique instruments at the same general post-market period. Therefore the option-universe discovery path is `Instrument/GetInstrumentOptionMarketWatch/{flow}`.

`GetMarketWatch` may still be used where the project's evidence logic explicitly requires it, but it is not the default option-universe discovery source.

## Direct download / diagnostic command

For future raw option-universe capture from Termux:

```bash
cd ~/OptimusAI_V41_LIVE || exit 1

python - <<'PY'
from tsetmc_adapter import TSETMCAdapter
import json
from pathlib import Path
from datetime import datetime, timezone

adapter = TSETMCAdapter()
result = adapter.option_market_watch_universe()

ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
path = Path("output") / f"tsetmc_option_universe_raw_{ts}.json"

payload = {
    "source": result.get("source"),
    "endpoint": result.get("endpoint"),
    "flows": result.get("flows"),
    "retrieved_at": result.get("retrieved_at"),
    "snapshot_sha256": result.get("snapshot_sha256"),
    "record_count": result.get("record_count"),
    "flow_evidence": result.get("flow_evidence"),
    "records": result.get("records"),
}

path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print("FILE=", path)
print("RECORD_COUNT=", result.get("record_count"))
print("RETRIEVED_AT=", result.get("retrieved_at"))
print("SNAPSHOT_SHA256=", result.get("snapshot_sha256"))
PY
```

This command uses the project's validated adapter rather than duplicating endpoint logic in shell scripts.

## Market-time rule

TSETMC live market data is considered live only during:

- Saturday through Wednesday
- 09:00 through 12:30 local Tehran market time

After 12:30, and on Thursday/Friday, do not manufacture a same-day live market snapshot. Use the most recent valid snapshot/evidence.

Before 09:00 Sunday, the valid prior window is Saturday 12:30 through Sunday 09:00.

A post-market raw TSETMC response may be retained for analysis, but must not automatically be labeled as a valid live trading snapshot.

## Reporting rule

For option reporting:

1. Discover option universe from `Instrument/GetInstrumentOptionMarketWatch/{flow}`.
2. Preserve raw payload/evidence and retrieval timestamp.
3. Use explicit `underlying_id`, `underlying_symbol`, `insCode_P`, `insCode_C` identity.
4. Never infer contract identity from symbol naming alone.
5. Rank option contracts using the active OptimusAI scoring model.
6. The underlying stock itself does not have to appear in the ranking; the selected option contracts are ranked.
7. Missing evidence remains unavailable; do not impute invented IV, Greeks, risk-free rate, OI or other unsupported fields.
8. A report is analytical evidence, not a BUY/SELL authorization unless the required production gates are explicitly closed.

## Current active scoring reference

Current TSETMC scoring block weights:

- LIQUIDITY: 20
- VALUATION: 25
- PAYOFF: 18
- TIME: 15
- GREEKS: 12
- MARKET: 10

Current factor weights:

- liquidity / trade_value: 7
- liquidity / volume: 5
- valuation / time_value_ratio: 5
- payoff / breakeven_distance: 10
- payoff / leverage: 5
- payoff / moneyness: 3
- time / calendar_days: 2
- market / last_vs_close: 4
- market / intraday_range: 3

Do not silently change these weights when reproducing a report. Any change must be versioned and documented.

## Evidence and governance

The TSETMC option-universe result is suitable for building an analytical report, but a post-market capture is not by itself evidence of a current live trading state.

The project remains fail-closed:
- missing endpoint/evidence/snapshot integrity blocks production use;
- analytical shadow failures may be non-blocking only where the documented gate permits;
- no production BUY/SELL authorization without the required evidence gates.

## Historical snapshot fallback

When live market capture is unavailable because the market is closed, use the most recent valid project snapshot rather than attempting to create a synthetic current snapshot.

Known project artifacts include:
- `output/historical_snapshots.jsonl`
- `output/final_live_tsetmc_test_20261002.json`
- `canonical_snapshot.py`
- `historical_snapshot.py`
- `tsetmc_history.py`
- `capture_tsetmc_historical_snapshot.py`

## Change-control rule

If TSETMC changes the endpoint, response schema, flow behavior or field meanings:
1. capture the new raw response;
2. compare it with this document and the adapter;
3. update the adapter and this reference together;
4. record the evidence and commit hash;
5. do not silently substitute a new source.

This document is the first reference to consult before performing another TSETMC option-data discovery exercise.
