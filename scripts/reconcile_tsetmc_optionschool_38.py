#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Evidence-only 38-field reconciliation scaffold.

Consumes a real OptionSchool24 workbook and a retained TSETMC option
market-watch evidence JSON. It never infers identity and never changes
production scoring/ranking.
"""

from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
import pandas as pd

ID_ALIASES = ("insCode","InsCode","instrument_id","InstrumentID","کد نماد","کد معاملاتی")

def sha256_file(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()

def explicit_ids(df):
    for c in ID_ALIASES:
        if c in df.columns:
            vals=df[c].dropna().astype(str).str.strip()
            vals=vals[vals!=""]
            if len(vals):
                return c, vals.tolist()
    return None, []

def load_tsetmc(path):
    p=json.loads(Path(path).read_text(encoding="utf-8"))
    records=[]
    data=p.get("data",p)
    raw=data.get("instrumentOptMarketWatch",[]) if isinstance(data,dict) else []
    for x in raw if isinstance(raw,list) else []:
        if not isinstance(x,dict): continue
        for key, side, sym in (("insCode_P","PUT","lVal18AFC_P"),("insCode_C","CALL","lVal18AFC_C")):
            if x.get(key) not in (None,""):
                records.append({"instrument_id":str(x[key]),"contract_type":side,
                                "symbol":x.get(sym),"underlying_id":str(x["uaInsCode"]) if x.get("uaInsCode") not in (None,"") else None,
                                "underlying_symbol":x.get("lval30_UA"),"strike":x.get("strikePrice"),
                                "begin_date":x.get("beginDate"),"end_date":x.get("endDate"),
                                "remaining_days":x.get("remainedDay")})
    return p,records

def reconcile(workbook,tsetmc):
    df=pd.read_excel(workbook)
    tmeta,trecs=load_tsetmc(tsetmc)
    id_col,ids=explicit_ids(df)
    t_ids={r["instrument_id"] for r in trecs}
    matched=[x for x in ids if x in t_ids]
    return {
      "status":"SUCCESS",
      "workbook_sha256":sha256_file(workbook),
      "workbook_rows":int(len(df)),
      "workbook_columns":int(len(df.columns)),
      "explicit_option_id_column":id_col,
      "explicit_option_id_count":len(ids),
      "tsetmc_record_count":len(trecs),
      "exact_id_matches":len(matched),
      "exact_id_match_rate":(len(matched)/len(ids)) if ids else None,
      "tsetmc_snapshot_sha256":tmeta.get("snapshot_sha256"),
      "tsetmc_endpoint":tmeta.get("endpoint"),
      "tsetmc_retrieved_at":tmeta.get("retrieved_at"),
      "identity_inference":"DISABLED",
      "production_changed":False,
      "field_reconciliation":"BLOCKED_UNTIL_EXPLICIT_ID_MATCH" if not matched else "IDENTITY_READY_FOR_FIELD_COMPARISON",
      "note":"This runner proves identity linkage only. Derived-field equality requires a separate formula reconciliation layer."
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--optionschool",required=True)
    ap.add_argument("--tsetmc",required=True)
    ap.add_argument("--output",required=True)
    a=ap.parse_args()
    out=reconcile(a.optionschool,a.tsetmc)
    Path(a.output).write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(out,ensure_ascii=False))

if __name__=="__main__": main()
