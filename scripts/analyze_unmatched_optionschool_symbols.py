#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Evidence-only analysis of OptionSchool symbols absent from the retained TSETMC snapshot.

Absence from current TSETMC Option Market-Watch is NOT treated as proof of expiry/closure.
No approximate symbol matching or lifecycle inference is performed.
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

def load_symbols(path):
    df=pd.read_excel(path)
    if "نماد" not in df.columns:
        raise ValueError("OptionSchool workbook has no نماد column")
    vals=[str(v).strip() for v in df["نماد"].tolist() if pd.notna(v) and str(v).strip()]
    return df, vals

def load_tsetmc_symbols(path):
    payload=json.loads(Path(path).read_text(encoding="utf-8"))
    data=payload.get("data",payload)
    root=data.get("instrumentOptMarketWatch",[]) if isinstance(data,dict) else []
    rows=[]
    for x in root if isinstance(root,list) else []:
        if not isinstance(x,dict): continue
        for id_key, sym_key, side in (
            ("insCode_P","lVal18AFC_P","PUT"),
            ("insCode_C","lVal18AFC_C","CALL"),
        ):
            if x.get(id_key) not in (None,"") and x.get(sym_key) not in (None,""):
                rows.append({
                    "symbol":str(x[sym_key]).strip(),
                    "instrument_id":str(x[id_key]),
                    "contract_type":side,
                    "underlying_id":str(x["uaInsCode"]) if x.get("uaInsCode") not in (None,"") else None,
                    "end_date":x.get("endDate"),
                    "remaining_days":x.get("remainedDay"),
                })
    return payload, rows

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--optionschool",required=True)
    ap.add_argument("--tsetmc",required=True)
    ap.add_argument("--output",required=True)
    a=ap.parse_args()

    df, os_symbols=load_symbols(a.optionschool)
    payload, t_rows=load_tsetmc_symbols(a.tsetmc)
    t_symbols={r["symbol"] for r in t_rows}
    unmatched=[]
    for row_no, symbol in enumerate(os_symbols, start=1):
        if symbol not in t_symbols:
            unmatched.append({
                "optionschool_row":row_no,
                "symbol":symbol,
                "classification":"NOT_IN_CURRENT_TSETMC_SNAPSHOT",
                "evidence":"Exact symbol equality check failed because the symbol is absent from the retained current TSETMC Option Market-Watch snapshot.",
                "closed_or_expired_proven":False,
            })

    out={
        "status":"SUCCESS",
        "workbook_sha256":sha256_file(a.optionschool),
        "workbook_rows":int(len(df)),
        "tsetmc_snapshot_sha256":payload.get("snapshot_sha256"),
        "tsetmc_record_count":len(t_rows),
        "optionschool_symbol_count":len(os_symbols),
        "unmatched_count":len(unmatched),
        "unmatched":unmatched,
        "lifecycle_inference":"DISABLED",
        "identity_inference":"DISABLED",
        "note":"A symbol absent from the current TSETMC snapshot is not classified as closed or expired. Proving lifecycle requires an authoritative historical/inactive record or explicit lifecycle evidence.",
    }
    Path(a.output).write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(out,ensure_ascii=False))

if __name__=="__main__":
    main()
