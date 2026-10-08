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

def main():
    snap=build_tsetmc_snapshot(flow=None,max_instruments=None,symbol_prefix=None)
    rows=list(snap.get("rows") or [])
    under={}
    for row in rows:
        ident=row.get("identity") or {}
        uid=str(ident.get("underlying_id") or "").strip()
        sym=str(ident.get("underlying_symbol") or "").strip()
        if uid and sym: under[uid]=sym
    ctx=fetch_underlying_context(sorted(under),include_board=True)
    ranked=[]
    for uid,a in (ctx.get("instruments") or {}).items():
        if not isinstance(a,dict): continue
        t,p,tech,em=tape(a),price_score(a),technical(a),early(a)
        components=[("tape",t,30),("price_momentum",p,20),("technical",tech,20),("early_move",em,10)]
        available_weight=sum(w for _,v,w in components if v is not None)
        available_points=sum(v for _,v,w in components if v is not None)
        # FIX: components are already point scores; do not multiply by their weights again.
        final=available_points/available_weight*100 if available_weight else None
        latest=n(a.get("last_price")); close=n(a.get("last_close"))
        bc=n(a.get("individual_buy_count")); sc=n(a.get("individual_sell_count"))
        bi=n(a.get("individual_buy_volume")); si=n(a.get("individual_sell_volume"))
        ranked.append({
            "instrument_id":uid,"symbol":under.get(uid),
            "final_score_live":round(final,2) if final is not None else None,
            "classification":classification(final),
            "tape_score":round(t,2) if t is not None else None,
            "price_momentum_score":round(p,2) if p is not None else None,
            "technical_score":round(tech,2) if tech is not None else None,
            "early_move_score":round(em,2) if em is not None else None,
            "strategy_fit_score":"DATA_UNAVAILABLE",
            "fundamental_context_score":"DATA_UNAVAILABLE",
            "daily_change_last_pct":round((latest/close-1)*100,3) if latest is not None and close not in (None,0) else None,
            "last_price":latest,"last_close":close,
            "upper_limit_headroom_pct":a.get("upper_limit_headroom_pct"),
            "touched_upper_limit_today":a.get("touched_upper_limit_today"),
            "real_buyer_power":a.get("individual_power_ratio"),
            "real_buy_per_capita":a.get("individual_buy_power"),
            "real_buyer_count":bc,"real_seller_count":sc,
            "real_buyer_seller_count_ratio":bc/sc if sc not in (None,0) else None,
            "real_buy_sell_volume_ratio":bi/si if si not in (None,0) else None,
            "volume_ratio_5_to_20":a.get("volume_ratio_5_to_20"),
            "orderbook_imbalance_5":a.get("orderbook_imbalance_5"),
            "trend_state":a.get("trend_state"),"rsi_14":a.get("rsi_14"),"macd_12_26":a.get("macd_12_26"),
            "return_5_sessions_pct":a.get("return_5_sessions_pct"),"return_20_sessions_pct":a.get("return_20_sessions_pct"),
            "early_move_state":(a.get("early_move") or {}).get("state"),
            "prelock_state":(a.get("early_move") or {}).get("pre_lock_sequence",{}).get("state"),
            "source":"TSETMC"
        })
    ranked.sort(key=lambda x:(x["final_score_live"] is None,-(x["final_score_live"] or -1e9)))
    report=[
        "📊 گزارش امتیازدهی سهم‌های پایه — BASE SHARE OPPORTUNITY SCORE V1",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━","Source of Truth: TSETMC",
        "Universe: سهم‌های پایه دارای قرارداد اختیار در Universe فعلی",
        "مدل: BASE SHARE OPPORTUNITY SCORING MODEL V1 — پروژه جدید",
        "⚠️ این گزارش با مدل‌های قبلی پروژه مخلوط نشده است.",
        "⚠️ Strategy Fit تاریخی و Fundamental فعلاً DATA_UNAVAILABLE هستند و امتیاز مصنوعی نگرفته‌اند.",
        "⚠️ داده مفقود صفرگذاری نشده؛ وزن مؤلفه‌های دارای شواهد نرمال‌سازی می‌شود.",
        "⚠️ امتیاز نهایی در مقیاس ۰ تا ۱۰۰ است.",
        f"تعداد سهم‌ها: {len(ranked)}","━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━","🏆 رتبه‌بندی","━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    ]
    for i,x in enumerate(ranked,1):
        report.append(f"#{i} {x['symbol']} | امتیاز {x['final_score_live'] if x['final_score_live'] is not None else 'داده موجود نیست'} | کلاس {x['classification']}")
        report.append(f"   تابلو {x['tape_score'] if x['tape_score'] is not None else 'داده موجود نیست'}/30 | قیمت/مومنتوم {x['price_momentum_score'] if x['price_momentum_score'] is not None else 'داده موجود نیست'}/20 | تکنیکال {x['technical_score'] if x['technical_score'] is not None else 'داده موجود نیست'}/20 | Early-Move {x['early_move_score'] if x['early_move_score'] is not None else 'داده موجود نیست'}/10")
        report.append(f"   تغییر روزانه={x['daily_change_last_pct'] if x['daily_change_last_pct'] is not None else 'داده موجود نیست'}% | سقف روز={x['touched_upper_limit_today']} | فاصله سقف={x['upper_limit_headroom_pct'] if x['upper_limit_headroom_pct'] is not None else 'داده موجود نیست'}% | قدرت حقیقی={x['real_buyer_power'] if x['real_buyer_power'] is not None else 'داده موجود نیست'} | نسبت تعداد حقیقی={round(x['real_buyer_seller_count_ratio'],2) if x['real_buyer_seller_count_ratio'] is not None else 'داده موجود نیست'}")
        report.append(f"   حجم 5/20={x['volume_ratio_5_to_20'] if x['volume_ratio_5_to_20'] is not None else 'داده موجود نیست'} | روند={x['trend_state'] or 'داده موجود نیست'} | RSI={x['rsi_14'] if x['rsi_14'] is not None else 'داده موجود نیست'} | MACD={x['macd_12_26'] if x['macd_12_26'] is not None else 'داده موجود نیست'}")
        report.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    out=ROOT/"output"/"base_share"; out.mkdir(parents=True,exist_ok=True)
    txt="\n".join(report)
    payload={"report_version":"BASE-SHARE-OPPORTUNITY-SCORE-V1-LIVE","generated_at":datetime.now(TEHRAN).isoformat(),"source_of_truth":"TSETMC","underlying_count":len(ranked),"rows":ranked,"source_snapshot_sha256":snap.get("snapshot_sha256"),"model_doc":"docs/BASE_SHARE_OPPORTUNITY_SCORING_MODEL_V1.md","missing_policy":"NO_IMPUTATION","score_scale":"0-100","score_formula":"sum(available_component_points) / sum(available_component_weights) * 100"}
    (out/"latest_opportunity_report.txt").write_text(txt,encoding="utf-8")
    (out/"latest_opportunity_report.json").write_text(json.dumps(payload,ensure_ascii=False,indent=2,allow_nan=False),encoding="utf-8")
    print(txt)
    print("\nREPORT_FILE =",out/"latest_opportunity_report.txt")
    print("REPORT_JSON =",out/"latest_opportunity_report.json")
    print("REPORT_SHA256 =",hashlib.sha256(txt.encode("utf-8")).hexdigest())

if __name__=="__main__":
    main()
