#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TSETMC-only canonical option source for OptimusAI V4.1."""
from __future__ import annotations
import hashlib, json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from tsetmc_adapter import TSETMCAdapter

ENGINE_VERSION = "TSETMC-FIRST-SOURCE-1.2"
CACHE_PATH = Path("output/tsetmc_first/latest_snapshot.json")
FIELD_NAMES = [
    "نماد","قیمت اعمال","قیمت سهم پایه","اختلاف تا اعمال","تاریخ سررسید",
    "روزهای تقویمی","روزهای معاملاتی","موقعیت های باز","حجم معاملات","ارزش معاملات",
    "آخرین قیمت","درصد آخرین قیمت","قیمت پایانی","درصد قیمت پایانی","ارزش ذاتی",
    "ارزش زمانی","سر به سر","اختلاف تا سر به سر","بلک شولز","اختلاف تا بلک شولز",
    "وضعیت","اهرم","نوسان ضمنی","نوسان تاریخی","اندازه قرارداد","حجم بهترین تقاضا",
    "قیمت بهترین تقاضا","حجم بهترین عرضه","قیمت بهترین عرضه","کمترین قیمت","بیشترین قیمت",
    "شکاف قیمتی","وجه تضمین","دلتا","تتا","گاما","وگا","رو",
]
def _first(mapping: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in mapping and mapping[key] not in (None, ""): return mapping[key]
    return None
def _as_number(value: Any) -> float | None:
    try:
        return None if value in (None, "") else float(value)
    except (TypeError, ValueError): return None
def _hash_json(value: Any) -> str:
    payload=json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
def _quote_values(result: dict[str, Any]) -> dict[str, Any]:
    data=result.get("data")
    if isinstance(data,dict): return data
    if isinstance(data,list) and data and isinstance(data[0],dict): return data[0]
    return {}

def _source_market_timestamp(qdata: dict[str, Any]) -> str | None:
    """Use only TSETMC's explicit dEven/hEven observation fields."""
    try:
        d_even = int(qdata.get("dEven"))
        h_even = int(qdata.get("hEven"))
        hh = h_even // 10000
        mm = (h_even // 100) % 100
        ss = h_even % 100
        return datetime.strptime(
            f"{d_even:08d} {hh:02d}:{mm:02d}:{ss:02d}",
            "%Y%m%d %H:%M:%S",
        ).isoformat()
    except (TypeError, ValueError):
        return None
def _load_last_known_snapshot() -> dict[str, Any] | None:
    try:
        path = CACHE_PATH
        if not path.exists():
            return None
        cached = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(cached, dict) or cached.get("source_of_truth") != "TSETMC":
            return None
        cached["data_mode"] = "LAST_KNOWN_TSETMC_SNAPSHOT"
        cached["live_refresh_status"] = "UNAVAILABLE"
        cached["cache_path"] = str(path)
        return cached
    except (OSError, ValueError, TypeError):
        return None

def _persist_snapshot(snapshot: dict[str, Any]) -> None:
    try:
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        CACHE_PATH.write_text(
            json.dumps(snapshot, ensure_ascii=False, indent=2, allow_nan=False),
            encoding="utf-8",
        )
    except OSError:
        pass

def build_tsetmc_snapshot(*, adapter: TSETMCAdapter | None=None, flow: int | None=None, max_instruments: int | None=None, symbol_prefix: str | None=None) -> dict[str,Any]:
    adapter=adapter or TSETMCAdapter()
    if max_instruments is not None:
        if isinstance(max_instruments, bool) or int(max_instruments) <= 0:
            raise ValueError("max_instruments must be a positive integer")
    try:
        universe_method = getattr(adapter, "option_market_watch_universe", None)
        if flow is None and callable(universe_method):
            mw = universe_method()
        elif flow is None:
            # Compatibility path for minimal/test adapters that expose only the
            # single-flow contract. Production TSETMCAdapter has the universe method.
            mw = adapter.option_market_watch_instrument_records(flow=1)
        else:
            mw = adapter.option_market_watch_instrument_records(flow=flow)
    except Exception as exc:
        cached = _load_last_known_snapshot()
        if cached is not None:
            cached["fallback_reason"] = type(exc).__name__
            return cached
        raise
    instruments=mw.get("records",[])
    if not instruments:
        cached = _load_last_known_snapshot()
        if cached is not None:
            cached["fallback_reason"] = "TSETMC_MARKET_WATCH_EMPTY"
            return cached
    if symbol_prefix:
        prefix = str(symbol_prefix).strip()
        instruments = [item for item in instruments if str(item.get("symbol") or "").startswith(prefix)]
    if max_instruments is not None:
        instruments = instruments[:int(max_instruments)]
    rows=[]; quote_evidence=[]; orderbook_evidence=[]; underlying_evidence={}
    for instrument in instruments:
        option_id=instrument.get("instrument_id"); underlying_id=instrument.get("underlying_id")
        if not option_id: continue
        quote = {"status": "FAILED", "error_type": "UNAVAILABLE"}
        orderbook = {"status": "FAILED", "error_type": "UNAVAILABLE"}
        qdata = {}
        quote_status = "FAILED"
        orderbook_status = "FAILED"
        delta_seconds = None
        delta_status = "UNAVAILABLE"
        quote_retrieved_at = None
        orderbook_retrieved_at = None
        # Quote is canonical evidence. BestLimits is auxiliary/quarantined.
        # Live production does not request BestLimits by default because this
        # endpoint can stall inside urllib before the socket timeout is honored
        # on some Termux/network combinations. This must never block the
        # TSETMC option universe. It can be explicitly enabled for diagnostics.
        best_limits_enabled = str(__import__("os").getenv("TSETMC_ENABLE_BEST_LIMITS", "")).strip().lower() in {"1", "true", "yes"}
        try:
            quote = adapter.quote(str(option_id))
            qdata = _quote_values(quote)
            quote_status = "SUCCESS"
        except Exception as exc:
            quote = {"status": "FAILED", "error_type": type(exc).__name__}
            qdata = {}
            quote_status = "FAILED"

        if best_limits_enabled:
            try:
                orderbook = adapter.order_book(str(option_id))
                orderbook_status = "SUCCESS"
            except Exception as exc:
                orderbook = {"status": "FAILED", "error_type": type(exc).__name__}
                orderbook_status = "FAILED"
        else:
            orderbook = {
                "status": "NOT_REQUESTED",
                "reason": "AUXILIARY_BEST_LIMITS_DISABLED_BY_DEFAULT",
                "source": "TSETMC",
                "endpoint": "BestLimits/{instrument_id}",
            }
            orderbook_status = "NOT_REQUESTED"

        quote_retrieved_at = quote.get("retrieved_at") if isinstance(quote, dict) else None
        orderbook_retrieved_at = orderbook.get("retrieved_at") if isinstance(orderbook, dict) else None
        if quote_status == "SUCCESS" and orderbook_status == "SUCCESS":
            try:
                if quote_retrieved_at and orderbook_retrieved_at:
                    qt = datetime.fromisoformat(str(quote_retrieved_at).replace("Z", "+00:00"))
                    bt = datetime.fromisoformat(str(orderbook_retrieved_at).replace("Z", "+00:00"))
                    delta_seconds = round(abs((bt - qt).total_seconds()), 6)
                    delta_status = "WITHIN_2_SECONDS" if delta_seconds <= 2.0 else "OVER_2_SECONDS"
                else:
                    delta_seconds = None
                    delta_status = "UNAVAILABLE"
            except (TypeError, ValueError):
                delta_seconds = None
                delta_status = "UNAVAILABLE"
        orderbook_data = orderbook.get("data") if isinstance(orderbook, dict) else None
        if not isinstance(orderbook_data, list):
            orderbook_data = []
        # InstrumentInfo is auxiliary enrichment. Keep it out of the default
        # live path because the TSETMC endpoint can stall at TCP connect on
        # constrained Termux/network routes, just like BestLimits.
        instrument_info_enabled = str(__import__("os").getenv("TSETMC_ENABLE_INSTRUMENT_INFO", "")).strip().lower() in {"1", "true", "yes"}
        if instrument_info_enabled:
            try:
                info=adapter.instrument_info(str(option_id)); idata=_quote_values(info); info_status="SUCCESS"
            except Exception as exc:
                info={"status":"FAILED","error_type":type(exc).__name__}; idata={}; info_status="FAILED"
        else:
            info={"status":"NOT_REQUESTED","reason":"AUXILIARY_INSTRUMENT_INFO_DISABLED_BY_DEFAULT","source":"TSETMC","endpoint":"Instrument/GetInstrumentInfo/{instrument_id}"}
            idata={}
            info_status="NOT_REQUESTED"
        if underlying_id and str(underlying_id) not in underlying_evidence:
            try:
                uq=adapter.quote(str(underlying_id))
                underlying_evidence[str(underlying_id)]={"status":"SUCCESS","quote":uq}
            except Exception as exc:
                underlying_evidence[str(underlying_id)]={"status":"FAILED","error_type":type(exc).__name__}
        ue=underlying_evidence.get(str(underlying_id),{})
        udata=_quote_values(ue.get("quote",{})) if ue.get("status")=="SUCCESS" else {}
        strike=_as_number(instrument.get("strike"))
        row={field:None for field in FIELD_NAMES}
        contract_size=_as_number(_first(idata,"contractSize","contract_size"))
        row.update({
            "نماد":instrument.get("symbol"),
            "اندازه قرارداد":contract_size,
            "قیمت اعمال":strike,
            "قیمت سهم پایه":_as_number(_first(udata,"pDrCotVal","pl")),
            "تاریخ سررسید":instrument.get("end_date"),
            "روزهای تقویمی":_as_number(instrument.get("remaining_days")),
            "حجم معاملات":_as_number(_first(qdata,"qTotTran5J","zTotTran")),
            "ارزش معاملات":_as_number(_first(qdata,"qTotCap")),
            "آخرین قیمت":_as_number(_first(qdata,"pDrCotVal","pl")),
            "قیمت پایانی":_as_number(_first(qdata,"pClosing","pc")),
            "کمترین قیمت":_as_number(_first(qdata,"priceMin","pMin")),
            "بیشترین قیمت":_as_number(_first(qdata,"priceMax","pMax")),
        })
        source_market_timestamp = _source_market_timestamp(qdata)
        rows.append({
            "canonical":row,
            "identity":{
                "instrument_id":option_id,
                "contract_type":instrument.get("contract_type"),
                "underlying_id":underlying_id,
                "underlying_symbol":instrument.get("underlying_symbol"),
                "identity_source_field":instrument.get("identity_source_field"),
            },
            "raw_market_watch":instrument,
            "raw_remaining_days":instrument.get("remaining_days"),
            "expiry_evidence":{"end_date":instrument.get("end_date"),"remaining_days":instrument.get("remaining_days"),
                               "source":"TSETMC","source_field":"endDate/remainedDay"},
            "source_market_timestamp":source_market_timestamp,
            "source_market_timestamp_status":"AVAILABLE" if source_market_timestamp else "UNAVAILABLE",
            "quote":quote,"order_book":orderbook,"instrument_info":info,
            "orderbook_raw_levels":orderbook_data,
            "quote_status":quote_status,"orderbook_status":orderbook_status,"instrument_info_status":info_status,
            "orderbook_level_count":len(orderbook_data),
        })
        quote_evidence.append({"instrument_id":option_id,"status":quote_status,"source":quote.get("source"),
                               "endpoint":quote.get("endpoint"),"snapshot_sha256":quote.get("snapshot_sha256"),
                               "retrieved_at":quote.get("retrieved_at")})
        orderbook_evidence.append({
            "instrument_id": option_id,
            "status": orderbook_status,
            "source": orderbook.get("source"),
            "endpoint": orderbook.get("endpoint"),
            "snapshot_sha256": orderbook.get("snapshot_sha256"),
            "retrieved_at": orderbook.get("retrieved_at"),
            "level_count": len(orderbook_data),
            "market_watch_snapshot_sha256": mw.get("snapshot_sha256"),
            "identity_source_field": instrument.get("identity_source_field"),
            "source_market_timestamp": source_market_timestamp,
            "quote_retrieved_at": quote_retrieved_at,
            "delta_seconds": delta_seconds,
            "delta_status": delta_status,
        })
    generated_at=datetime.now(timezone.utc).isoformat()
    evidence={"engine_version":ENGINE_VERSION,"source":"TSETMC","generated_at":generated_at,
              "market_watch":{"endpoint":mw.get("endpoint"),"snapshot_sha256":mw.get("snapshot_sha256"),
                              "retrieved_at":mw.get("retrieved_at"),"record_count":len(instruments),
                              "flows":mw.get("flows"),"flow_evidence":mw.get("flow_evidence")},
              "quote_evidence":quote_evidence,"orderbook_evidence":orderbook_evidence,
              "underlying_evidence":underlying_evidence,
              "best_limits_contract":{
                  "status":"RAW_ONLY_QUARANTINED",
                  "source":"TSETMC",
                  "endpoint":"BestLimits/{instrument_id}",
                  "identity_binding":"instrument_id",
                  "market_watch_binding":"market_watch_snapshot_sha256",
                  "source_timestamp_binding":"source_market_timestamp",
                  "delta_seconds_limit":2.0,
                  "consumption_status":"NOT_CONSUMED_BY_SCORING_OR_RANKING_FEATURES",
              }}
    snapshot = {"status":"SUCCESS","engine_version":ENGINE_VERSION,"source_of_truth":"TSETMC",
                "external_comparison_source":None,"generated_at":generated_at,"row_count":len(rows),
                "rows":rows,"evidence":evidence,
                "snapshot_sha256":_hash_json({"rows":rows,"evidence":evidence}),
                "data_mode":"LIVE_TSETMC_REFRESH",
                "live_refresh_status":"SUCCESS"}
    _persist_snapshot(snapshot)
    return snapshot
def write_snapshot(snapshot:dict[str,Any], output:str|Path)->Path:
    path=Path(output); path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(snapshot,ensure_ascii=False,indent=2,allow_nan=False),encoding="utf-8")
    return path
if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser(description="Build TSETMC-only option snapshot")
    parser.add_argument("--output",type=Path,default=Path("output/tsetmc_first/latest_snapshot.json"))
    parser.add_argument("--flow",type=int,default=1)
    args=parser.parse_args()
    snapshot=build_tsetmc_snapshot(flow=args.flow); write_snapshot(snapshot,args.output)
    print(json.dumps({"status":snapshot["status"],"source_of_truth":snapshot["source_of_truth"],
                      "row_count":snapshot["row_count"],"snapshot_sha256":snapshot["snapshot_sha256"],
                      "output":str(args.output)},ensure_ascii=False))
