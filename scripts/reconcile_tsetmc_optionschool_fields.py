#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Evidence-only comparison of OptionSchool 38 fields against retained TSETMC option-watch data.

Only fields directly represented by the retained TSETMC snapshot are compared here.
No formulas, tolerances, or inferred values are introduced.
"""

from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
import pandas as pd

def sha256_file(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()

def norm(v):
    if pd.isna(v): return None
    s=str(v).strip()
    return s if s else None

def load_tsetmc(path):
    p=json.loads(Path(path).read_text(encoding="utf-8"))
    data=p.get("data",p)
    raw=data.get("instrumentOptMarketWatch",[]) if isinstance(data,dict) else []
    by_symbol={}
    for x in raw if isinstance(raw,list) else []:
        if not isinstance(x,dict): continue
        for id_key, sym_key, side in (("insCode_P","lVal18AFC_P","PUT"),("insCode_C","lVal18AFC_C","CALL")):
            if x.get(id_key) not in (None,"") and x.get(sym_key) not in (None,""):
                symbol=norm(x.get(sym_key))
                if symbol:
                    by_symbol.setdefault(symbol,[]).append({
                        "instrument_id":norm(x.get(id_key)),
                        "contract_type":side,
                        "strike":norm(x.get("strikePrice")),
                        "end_date":norm(x.get("endDate")),
                        "remaining_days":norm(x.get("remainedDay")),
                        "underlying_id":norm(x.get("uaInsCode")),
                        "underlying_symbol":norm(x.get("lval30_UA")),
                    })
    return p,by_symbol

def compare(a,b):
    if a is None or b is None: return "NOT_COMPARABLE"
    return "MATCH" if str(a)==str(b) else "MISMATCH"

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--optionschool",required=True)
    ap.add_argument("--reconciliation",required=True)
    ap.add_argument("--tsetmc",required=True)
    ap.add_argument("--output",required=True)
    a=ap.parse_args()

    df=pd.read_excel(a.optionschool)
    rec=json.loads(Path(a.reconciliation).read_text(encoding="utf-8"))
    tmeta,tby=load_tsetmc(a.tsetmc)

    rows=[]
    for mapping in rec.get("row_mappings",[]):
        if mapping.get("mapping_status")!="EXACT_UNIQUE_SYMBOL_MATCH":
            continue
        i=int(mapping["optionschool_row"])
        if i < 1 or i > len(df): continue
        row=df.iloc[i-1]
        symbol=mapping["symbol"]
        tm=tby.get(symbol,[])
        if len(tm)!=1:
            rows.append({"optionschool_row":i,"symbol":symbol,"identity_status":"BLOCKED_NON_UNIQUE_TSETMC"})
            continue
        t=tm[0]
        checks={
            "field_1_symbol":{"optionschool":symbol,"tsetmc":symbol,"result":"MATCH"},
            "field_2_strike":{"optionschool":norm(row.get("قیمت اعمال")),"tsetmc":t["strike"],
                              "result":compare(norm(row.get("قیمت اعمال")),t["strike"])},
            "field_5_expiry":{"optionschool":norm(row.get("تاریخ سررسید")),"tsetmc":t["end_date"],
                              "result":"SOURCE_FORMAT_DIFFERENT_OR_MATCH_REQUIRES_DATE_NORMALIZATION"},
            "field_6_calendar_days":{"optionschool":norm(row.get("روزهای تقویمی")),"tsetmc":t["remaining_days"],
                              "result":"SOURCE_CONVENTION_NOT_PROVEN"},
        }
        rows.append({
            "optionschool_row":i,
            "symbol":symbol,
            "tsetmc_instrument_id":t["instrument_id"],
            "tsetmc_contract_type":t["contract_type"],
            "tsetmc_underlying_id":t["underlying_id"],
            "tsetmc_underlying_symbol":t["underlying_symbol"],
            "checks":checks,
        })

    summary={}
    for r in rows:
        for c in r.get("checks",{}).values():
            summary[c["result"]]=summary.get(c["result"],0)+1

    out={
        "status":"SUCCESS",
        "workbook_sha256":sha256_file(a.optionschool),
        "reconciliation_sha256":sha256_file(a.reconciliation),
        "tsetmc_raw_sha256":sha256_file(a.tsetmc),
        "tsetmc_snapshot_sha256":tmeta.get("snapshot_sha256"),
        "row_count_compared":len(rows),
        "summary":summary,
        "rows":rows,
        "production_changed":False,
        "formula_inference":"DISABLED",
        "note":"This is evidence-only. Derived fields and source-convention differences are not converted into matches by tolerance or guessed formulas."
    }
    Path(a.output).write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":"SUCCESS","row_count_compared":len(rows),"summary":summary},ensure_ascii=False))

if __name__=="__main__":
    main()
