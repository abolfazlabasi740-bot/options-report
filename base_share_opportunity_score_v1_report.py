#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BASE SHARE OPPORTUNITY SCORE V1 live report.
New-project baseline. TSETMC-only. Missing components are excluded, never imputed.
"""
from __future__ import annotations
import json, hashlib
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from tsetmc_first_source import build_tsetmc_snapshot
from underlying_trend_engine import fetch_underlying_context

ROOT = Path(__file__).resolve().parent
TEHRAN = ZoneInfo("Asia/Tehran")

def n(v):
    try:
        if v in (None, ""): return None
        x = float(v)
        return x if x == x and abs(x) != float("inf") else None
    except Exception:
        return None

def clamp(x, a=0, b=1):
    return max(a, min(b, x))

def score_ratio(x, neutral=1.0, strong=2.0):
    if x is None: return None
    if x <= 0: return 0.0
    return clamp((x-neutral)/(strong-neutral))

def score_pct(x, lo=-5, hi=5):
    if x is None: return None
    return clamp((x-lo)/(hi-lo))

def tape(a):
    vals=[]
    p=n(a.get("individual_power_ratio"))
    if p is not None: vals.append((score_ratio(p,1.0,2.5),7))
    bc=n(a.get("individual_buy_count")); sc=n(a.get("individual_sell_count"))
    if bc is not None and sc not in (None,0): vals.append((score_ratio(bc/sc,0.8,1.8),4))
    bi=n(a.get("individual_buy_volume")); si=n(a.get("individual_sell_volume"))
    if bi is not None and si not in (None,0): vals.append((score_ratio(bi/si,0.8,1.8),4))
    vr=n(a.get("volume_ratio_5_to_20"))
    if vr is not None: vals.append((score_ratio(vr,0.8,1.8),3))
    ob=n(a.get("orderbook_imbalance_5"))
    if ob is not None: vals.append((clamp((ob+1)/2),2))
    lp=n(a.get("legal_power_ratio"))
    if lp is not None: vals.append((score_ratio(lp,0.8,1.5),2))
    total=sum(w for _,w in vals)
    return sum(s*w for s,w in vals)/total*30 if total else None

def price_score(a):
    vals=[]
    ch=n(a.get("daily_change_pct"))
    if ch is None: ch=n(a.get("return_5_sessions_pct"))
    if ch is not None: vals.append((score_pct(ch,-5,5),4))
    head=n(a.get("upper_limit_headroom_pct"))
    if head is not None: vals.append((clamp(1-abs(head)/5),4))
    touched=a.get("touched_upper_limit_today")
    if touched is True: vals.append((1.0,4))
    elif touched is False: vals.append((0.25,4))
    r=n(a.get("range_position_20"))
    if r is not None: vals.append((r,4))
    vr=n(a.get("volume_ratio_5_to_20"))
    if vr is not None: vals.append((score_ratio(vr,0.8,1.8),4))
    total=sum(w for _,w in vals)
    return sum(s*w for s,w in vals)/total*20 if total else None

def technical(a):
    vals=[]
    trend=a.get("trend_state")
    ts=1.0 if trend=="UP_TREND_STRUCTURE" else 0.5 if trend=="MIXED_STRUCTURE" else 0.0 if trend=="DOWN_TREND_STRUCTURE" else None
    if ts is not None: vals.append((ts,5))
    r=n(a.get("rsi_14"))
    if r is not None: vals.append((clamp(1-abs(r-60)/40),4))
    mac=n(a.get("macd_12_26"))
    if mac is not None: vals.append((1.0 if mac>0 else 0.0,4))
    s20=n(a.get("sma_20")); s50=n(a.get("sma_50")); last=n(a.get("last_close"))
    if last is not None and s20 not in (None,0): vals.append((1.0 if last>s20 else 0.0,3))
    if s20 is not None and s50 not in (None,0): vals.append((1.0 if s20>s50 else 0.0,2))
    ret20=n(a.get("return_20_sessions_pct"))
    if ret20 is not None: vals.append((score_pct(ret20,-15,15),2))
    total=sum(w for _,w in vals)
    return sum(s*w for s,w in vals)/total*20 if total else None

def early(a):
    e=a.get("early_move") or {}
    vals=[]
    es=n(e.get("score"))
    if es is not None: vals.append((clamp((es+100)/200),4))
    br=e.get("breakout_above_prior_20_high")
    if br is not None: vals.append((1.0 if br else 0.25,3))
    state=(e.get("pre_lock_sequence") or {}).get("state")
    ss=1.0 if state=="EARLY" else 0.75 if state=="DEVELOPING" else 0.5 if state=="WATCH" else 0.0 if state=="NO_SEQUENCE_EVIDENCE" else None
    if ss is not None: vals.append((ss,3))
    total=sum(w for _,w in vals)
    return sum(s*w for s,w in vals)/total*10 if total else None

def classification(score):
    if score is None: return "C"
    if score >= 75: return "A"
    if score >= 55: return "B"
    return "C"

def _snapshot_underlyings(snap):
    """Build one immutable underlying view from the single TSETMC snapshot.
    No per-underlying network calls are allowed here.
    """
    out={}
    for row in snap.get("rows") or []:
        if not isinstance(row,dict): continue
        ident=row.get("identity") or {}
        uid=str(ident.get("underlying_id") or "").strip()
        sym=str(ident.get("underlying_symbol") or "").strip()
        if not uid or not sym or uid in out: continue
        mf=row.get("underlying_market_watch_fields") or {}
        # The canonical snapshot keeps the underlying market-watch fields in
        # raw_market_watch. Prefer that immutable evidence when present.
        raw=row.get("raw_market_watch") or {}
        if not isinstance(mf,dict):
            mf={}
        out[uid]={
            "symbol":sym,
            "last_price":n(mf.get("last_price")),
            "last_close":n(mf.get("close_price")),
            "low_price":n(mf.get("low_price")),
            "high_price":n(mf.get("high_price")),
            "volume":n(mf.get("volume")),
            "trade_count":n(mf.get("trade_count")),
            "trade_value":n(mf.get("trade_value")),
            "bid_quantity":n(mf.get("bid_quantity")),
            "bid_price":n(mf.get("bid_price")),
            "ask_quantity":n(mf.get("ask_quantity")),
            "ask_price":n(mf.get("ask_price")),
            "snapshot_market_fields":mf,
            "snapshot_raw":raw,
        }
    return out

def _snapshot_price_score(a):
    vals=[]
    last=a.get("last_price"); close=a.get("last_close")
    low=a.get("low_price"); high=a.get("high_price")
    if last is not None and close not in (None,0):
        vals.append((clamp((last/close-0.95)/0.10),5))
    if last is not None and low is not None and high is not None and high>low:
        vals.append((clamp((last-low)/(high-low)),5))
    total=sum(w for _,w in vals)
    return sum(s*w for s,w in vals)/total*20 if total else None

def _snapshot_technical_score(a):
    # Do not manufacture technical indicators from a closed option snapshot.
    return None

def _snapshot_tape_score(a):
    # Underlying client-type/order-flow fields are not present in the
    # canonical option MarketWatch snapshot; using option order flow here
    # would contaminate the base-share model.
    return None

def _snapshot_early_score(a):
    return None

def main():
    # ONE snapshot for the whole universe. After market close this resolves
    # to the frozen final TSETMC snapshot and MUST NOT refresh each underlying.
    snap=build_tsetmc_snapshot(flow=None,max_instruments=None,symbol_prefix=None)
    if snap.get("source_of_truth")!="TSETMC":
        raise RuntimeError("TSETMC_SOURCE_OF_TRUTH_REQUIRED")
    under=_snapshot_underlyings(snap)
    ranked=[]
    for uid,a in under.items():
        t=_snapshot_tape_score(a)
        p=_snapshot_price_score(a)
        tech=_snapshot_technical_score(a)
        em=_snapshot_early_score(a)
        components=[("tape",t,30),("price_momentum",p,20),("technical",tech,20),("early_move",em,10)]
        available_weight=sum(w for _,v,w in components if v is not None)
        available_points=sum(v for _,v,w in components if v is not None)
        final=available_points/available_weight*100 if available_weight else None
        last=a.get("last_price"); close=a.get("last_close")
        intraday=(last/close-1)*100 if last is not None and close not in (None,0) else None
        range_pos=((last-a["low_price"])/(a["high_price"]-a["low_price"])) if last is not None and a.get("low_price") is not None and a.get("high_price") is not None and a["high_price"]>a["low_price"] else None
        ranked.append({
            "instrument_id":uid,"symbol":a["symbol"],
            "final_score_live":round(final,2) if final is not None else None,
            "classification":classification(final),
            "tape_score":None,
            "price_momentum_score":round(p,2) if p is not None else None,
            "technical_score":None,
            "early_move_score":None,
            "strategy_fit_score":"DATA_UNAVAILABLE",
            "fundamental_context_score":"DATA_UNAVAILABLE",
            "snapshot_last_price":last,"snapshot_close_price":close,
            "intraday_last_vs_close_pct":round(intraday,3) if intraday is not None else None,
            "daily_range_position":round(range_pos,4) if range_pos is not None else None,
            "snapshot_low":a.get("low_price"),"snapshot_high":a.get("high_price"),
            "snapshot_volume":a.get("volume"),"snapshot_trade_count":a.get("trade_count"),
            "snapshot_trade_value":a.get("trade_value"),
            "source":"TSETMC","source_snapshot_sha256":snap.get("snapshot_sha256"),
            "data_mode":snap.get("data_mode"),"selection_reason":snap.get("selection_reason"),
        })
    ranked.sort(key=lambda x:(x["final_score_live"] is None,-(x["final_score_live"] or -1e9)))
    report=[
        "📊 گزارش رتبه‌بندی سهم‌های پایه — BASE SHARE OPPORTUNITY SCORE V1",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "Source of Truth: TSETMC",
        "اجرای داده‌ای: یک Snapshot مشترک برای کل Universe",
        f"Data mode: {snap.get('data_mode')}",
        f"Snapshot SHA256: {snap.get('snapshot_sha256')}",
        "قانون خارج از بازار: استفاده از آخرین Snapshot معتبر؛ بدون Fetch جداگانه برای هر سهم پایه.",
        "⚠️ مؤلفه‌های فاقد شواهد در Snapshot صفرگذاری یا حدس زده نشده‌اند.",
        "⚠️ Tape / Technical / Early-Move در این اجرای Snapshot-only فقط در صورت وجود داده صریح قابل امتیازدهی هستند.",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━","🏆 رتبه‌بندی","━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    ]
    for i,x in enumerate(ranked,1):
        report.append(f"#{i} {x['symbol']} | امتیاز {x['final_score_live'] if x['final_score_live'] is not None else 'داده موجود نیست'} | کلاس {x['classification']}")
        report.append(f"   قیمت/مومنتوم {x['price_momentum_score'] if x['price_momentum_score'] is not None else 'داده موجود نیست'}/20 | آخرین/پایانی={x['intraday_last_vs_close_pct'] if x['intraday_last_vs_close_pct'] is not None else 'داده موجود نیست'}% | موقعیت در دامنه={x['daily_range_position'] if x['daily_range_position'] is not None else 'داده موجود نیست'}")
        report.append("   تابلو=داده موجود نیست | تکنیکال=داده موجود نیست | Early-Move=داده موجود نیست | Strategy Fit=داده موجود نیست | بنیادی=داده موجود نیست")
        report.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    out=ROOT/"output"/"base_share"; out.mkdir(parents=True,exist_ok=True)
    txt="\n".join(report)
    payload={
        "report_version":"BASE-SHARE-OPPORTUNITY-SCORE-V1-SNAPSHOT-ONLY",
        "generated_at":datetime.now(TEHRAN).isoformat(),
        "source_of_truth":"TSETMC",
        "underlying_count":len(ranked),
        "rows":ranked,
        "source_snapshot_sha256":snap.get("snapshot_sha256"),
        "data_mode":snap.get("data_mode"),
        "selection_reason":snap.get("selection_reason"),
        "model_doc":"docs/BASE_SHARE_OPPORTUNITY_SCORING_MODEL_V1.md",
        "missing_policy":"NO_IMPUTATION",
        "score_scale":"0-100",
        "execution_rule":"ONE_SHARED_TSETMC_SNAPSHOT_FOR_ALL_UNDERLYINGS",
        "network_rule":"NO_PER_UNDERLYING_FETCH_AFTER_SNAPSHOT",
        "score_formula":"sum(available_component_points) / sum(available_component_weights) * 100",
    }
    (out/"latest_opportunity_report.txt").write_text(txt,encoding="utf-8")
    (out/"latest_opportunity_report.json").write_text(json.dumps(payload,ensure_ascii=False,indent=2,allow_nan=False),encoding="utf-8")
    print(txt)
    print("\nREPORT_FILE =",out/"latest_opportunity_report.txt")
    print("REPORT_JSON =",out/"latest_opportunity_report.json")
    print("REPORT_SHA256 =",hashlib.sha256(txt.encode("utf-8")).hexdigest())

if __name__=="__main__":
    main()
