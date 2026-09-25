#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TSETMC-only canonical option source for OptimusAI V4.1."""
from __future__ import annotations
import hashlib, json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from tsetmc_adapter import TSETMCAdapter

ENGINE_VERSION = "TSETMC-FIRST-SOURCE-1.3-MARKETWATCH-CANONICAL"
CACHE_PATH = Path("output/tsetmc_first/latest_snapshot.json")
FIELD_NAMES = [
    "نماد","قیمت اعمال","قیمت سهم پایه","اختلاف تا اعمال","تاریخ سررسید",
    "روزهای تقویمی","روزهای معاملاتی","موقعیت های باز","حجم معاملات","تعداد معاملات","ارزش معاملات",
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
    try:
        d_even=int(qdata.get("dEven")); h_even=int(qdata.get("hEven"))
        hh=h_even//10000; mm=(h_even//100)%100; ss=h_even%100
        return datetime.strptime(f"{d_even:08d} {hh:02d}:{mm:02d}:{ss:02d}","%Y%m%d %H:%M:%S").isoformat()
    except (TypeError, ValueError): return None
def _load_last_known_snapshot() -> dict[str, Any] | None:
    try:
        path=CACHE_PATH
        if not path.exists(): return None
        cached=json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(cached,dict) or cached.get("source_of_truth")!="TSETMC": return None
        cached["data_mode"]="LAST_KNOWN_TSETMC_SNAPSHOT"; cached["live_refresh_status"]="UNAVAILABLE"; cached["cache_path"]=str(path)
        return cached
    except (OSError, ValueError, TypeError): return None
def _persist_snapshot(snapshot: dict[str, Any]) -> None:
    try:
        CACHE_PATH.parent.mkdir(parents=True,exist_ok=True)
        CACHE_PATH.write_text(json.dumps(snapshot,ensure_ascii=False,indent=2,allow_nan=False),encoding="utf-8")
    except OSError: pass
def build_tsetmc_snapshot(*, adapter: TSETMCAdapter | None=None, flow: int | None=None, max_instruments: int | None=None, symbol_prefix: str | None=None) -> dict[str,Any]:
    adapter=adapter or TSETMCAdapter()
    if max_instruments is not None:
        if isinstance(max_instruments,bool) or int(max_instruments)<=0: raise ValueError("max_instruments must be a positive integer")
    try:
        universe_method=getattr(adapter,"option_market_watch_universe",None)
        if flow is None and callable(universe_method): mw=universe_method()
        elif flow is None: mw=adapter.option_market_watch_instrument_records(flow=1)
        else: mw=adapter.option_market_watch_instrument_records(flow=flow)
    except Exception as exc:
        cached=_load_last_known_snapshot()
        if cached is not None: cached["fallback_reason"]=type(exc).__name__; return cached
        raise
    instruments=mw.get("records",[])
    if not instruments:
        cached=_load_last_known_snapshot()
        if cached is not None: cached["fallback_reason"]="TSETMC_MARKET_WATCH_EMPTY"; return cached
    if symbol_prefix:
        prefix=str(symbol_prefix).strip()
        instruments=[item for item in instruments if str(item.get("symbol") or "").startswith(prefix)]
    if max_instruments is not None: instruments=instruments[:int(max_instruments)]
    rows=[]; quote_evidence=[]; orderbook_evidence=[]; underlying_evidence={}
    for instrument in instruments:
        option_id=instrument.get("instrument_id"); underlying_id=instrument.get("underlying_id")
        if not option_id: continue
        market_fields=instrument.get("market_watch_fields")
        if not isinstance(market_fields,dict): market_fields={}
        underlying_fields=instrument.get("underlying_market_watch_fields")
        if not isinstance(underlying_fields,dict): underlying_fields={}
        quote={"status":"DERIVED_FROM_MARKET_WATCH","source":"TSETMC","endpoint":mw.get("endpoint"),"snapshot_sha256":mw.get("snapshot_sha256"),"retrieved_at":mw.get("retrieved_at"),"data":market_fields}
        quote_status="SUCCESS" if market_fields else "INSUFFICIENT"; quote_retrieved_at=mw.get("retrieved_at")
        orderbook={"status":"NOT_REQUESTED","reason":"AUXILIARY_BEST_LIMITS_DISABLED_BY_DEFAULT","source":"TSETMC","endpoint":"BestLimits/{instrument_id}"}
        orderbook_status="NOT_REQUESTED"; orderbook_data=[]
        info={"status":"DERIVED_FROM_MARKET_WATCH","source":"TSETMC","endpoint":mw.get("endpoint"),"snapshot_sha256":mw.get("snapshot_sha256"),"retrieved_at":mw.get("retrieved_at"),"data":{"contractSize":instrument.get("contract_size")}}
        info_status="SUCCESS" if instrument.get("contract_size") not in (None,"") else "INSUFFICIENT"
        underlying_evidence[str(underlying_id)]={"status":"DERIVED_FROM_MARKET_WATCH" if underlying_fields else "INSUFFICIENT","source":"TSETMC","endpoint":mw.get("endpoint"),"snapshot_sha256":mw.get("snapshot_sha256"),"retrieved_at":mw.get("retrieved_at"),"quote":{"status":"DERIVED_FROM_MARKET_WATCH","source":"TSETMC","endpoint":mw.get("endpoint"),"snapshot_sha256":mw.get("snapshot_sha256"),"retrieved_at":mw.get("retrieved_at"),"data":underlying_fields}}
        strike=_as_number(instrument.get("strike"))
        row={field:None for field in FIELD_NAMES}
        row.update({
            "نماد":instrument.get("symbol"),"اندازه قرارداد":_as_number(instrument.get("contract_size")),
            "قیمت اعمال":strike,"قیمت سهم پایه":_as_number(_first(underlying_fields,"last_price")),
            "تاریخ سررسید":instrument.get("end_date"),"روزهای تقویمی":_as_number(instrument.get("remaining_days")),
            "موقعیت های باز":_as_number(_first(market_fields,"open_interest")),
            "حجم معاملات":_as_number(_first(market_fields,"volume")),
            "تعداد معاملات":_as_number(_first(market_fields,"trade_count")),
            "ارزش معاملات":_as_number(_first(market_fields,"trade_value")),
            "آخرین قیمت":_as_number(_first(market_fields,"last_price")),"قیمت پایانی":_as_number(_first(market_fields,"close_price")),
            "کمترین قیمت":_as_number(_first(market_fields,"low_price")),"بیشترین قیمت":_as_number(_first(market_fields,"high_price")),
            "حجم بهترین تقاضا":_as_number(_first(market_fields,"bid_quantity")),"قیمت بهترین تقاضا":_as_number(_first(market_fields,"bid_price")),
            "حجم بهترین عرضه":_as_number(_first(market_fields,"ask_quantity")),"قیمت بهترین عرضه":_as_number(_first(market_fields,"ask_price")),
        })
        source_market_timestamp = _source_market_timestamp(instrument.get("raw_market_watch") or {})
        source_market_timestamp_status = "AVAILABLE" if source_market_timestamp else "UNAVAILABLE"
        rows.append({
            "canonical":row,
            "identity":{"instrument_id":option_id,"contract_type":instrument.get("contract_type"),"underlying_id":underlying_id,"underlying_symbol":instrument.get("underlying_symbol"),"identity_source_field":instrument.get("identity_source_field")},
            "raw_market_watch":instrument,"market_watch_fields":market_fields,"raw_remaining_days":instrument.get("remaining_days"),
            "expiry_evidence":{"end_date":instrument.get("end_date"),"remaining_days":instrument.get("remaining_days"),"source":"TSETMC","source_field":"endDate/remainedDay"},
            "source_market_timestamp":source_market_timestamp,"source_market_timestamp_status":source_market_timestamp_status,
            "quote":quote,"order_book":orderbook,"instrument_info":info,"orderbook_raw_levels":orderbook_data,
            "quote_status":quote_status,"orderbook_status":orderbook_status,"instrument_info_status":info_status,"orderbook_level_count":0,
        })
        quote_evidence.append({"instrument_id":option_id,"status":quote_status,"source":"TSETMC","endpoint":mw.get("endpoint"),"snapshot_sha256":mw.get("snapshot_sha256"),"retrieved_at":mw.get("retrieved_at"),"evidence_mode":"MARKET_WATCH_CANONICAL"})
        delta_status="NOT_APPLICABLE_MARKET_WATCH_CANONICAL"
        orderbook_evidence.append({"instrument_id":option_id,"status":"NOT_REQUESTED","source":"TSETMC","endpoint":"BestLimits/{instrument_id}","level_count":0,"market_watch_snapshot_sha256":mw.get("snapshot_sha256"),"identity_source_field":instrument.get("identity_source_field"),"source_market_timestamp":None,"quote_retrieved_at":quote_retrieved_at,"delta_seconds":None,"delta_status": delta_status})
    generated_at=datetime.now(timezone.utc).isoformat()
    evidence={"engine_version":ENGINE_VERSION,"source":"TSETMC","generated_at":generated_at,
              "market_watch":{"endpoint":mw.get("endpoint"),"snapshot_sha256":mw.get("snapshot_sha256"),"retrieved_at":mw.get("retrieved_at"),"record_count":len(instruments),"flows":mw.get("flows"),"flow_evidence":mw.get("flow_evidence"),"source_market_timestamp_count":sum(1 for r in rows if r.get("source_market_timestamp")),"latest_source_market_timestamp":max((r.get("source_market_timestamp") for r in rows if r.get("source_market_timestamp")), default=None)},
              "quote_evidence":quote_evidence,"orderbook_evidence":orderbook_evidence,"underlying_evidence":underlying_evidence,
              "best_limits_contract":{"status":"RAW_ONLY_QUARANTINED","source":"TSETMC","endpoint":"BestLimits/{instrument_id}","identity_binding":"instrument_id","market_watch_binding":"market_watch_snapshot_sha256","source_timestamp_binding":"source_market_timestamp","delta_seconds_limit":2.0,"consumption_status":"NOT_CONSUMED_BY_SCORING_OR_RANKING_FEATURES"}}
    snapshot={"status":"SUCCESS","engine_version":ENGINE_VERSION,"source_of_truth":"TSETMC","external_comparison_source":None,"generated_at":generated_at,"row_count":len(rows),"rows":rows,"evidence":evidence,"snapshot_sha256":_hash_json({"rows":rows,"evidence":evidence}),"data_mode":"LIVE_TSETMC_REFRESH","live_refresh_status":"SUCCESS"}
    _persist_snapshot(snapshot); return snapshot
def write_snapshot(snapshot:dict[str,Any], output:str|Path)->Path:
    path=Path(output); path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(snapshot,ensure_ascii=False,indent=2,allow_nan=False),encoding="utf-8"); return path
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
