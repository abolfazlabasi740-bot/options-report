#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Evidence-only 38-field reconciliation.

OptionSchool24 does not expose the TSETMC numeric instrument ID. Its explicit
option symbol (نماد) is the source identity key. This runner accepts a symbol
mapping only when uniqueness is verified in both snapshots; it never guesses
from prefixes, strike, expiry, or contract type and never changes production.
"""

from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
import pandas as pd

ID_ALIASES = ("insCode","InsCode","instrument_id","InstrumentID","کد نماد","کد معاملاتی")
SYMBOL_COLUMN = "نماد"

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

def normalized_symbols(values):
    return [str(v).strip() for v in values if pd.notna(v) and str(v).strip()]

def load_tsetmc(path):
    p=json.loads(Path(path).read_text(encoding="utf-8"))
    records=[]
    data=p.get("data",p)
    raw=data.get("instrumentOptMarketWatch",[]) if isinstance(data,dict) else []
    for x in raw if isinstance(raw,list) else []:
        if not isinstance(x,dict): continue
        for key, side, sym in (("insCode_P","PUT","lVal18AFC_P"),("insCode_C","CALL","lVal18AFC_C")):
            if x.get(key) not in (None,"") and x.get(sym) not in (None,""):
                records.append({
                    "instrument_id":str(x[key]),
                    "contract_type":side,
                    "symbol":str(x[sym]).strip(),
                    "underlying_id":str(x["uaInsCode"]) if x.get("uaInsCode") not in (None,"") else None,
                    "underlying_symbol":x.get("lval30_UA"),
                    "strike":x.get("strikePrice"),
                    "begin_date":x.get("beginDate"),
                    "end_date":x.get("endDate"),
                    "remaining_days":x.get("remainedDay")
                })
    return p,records

def reconcile(workbook,tsetmc):
    df=pd.read_excel(workbook)
    tmeta,trecs=load_tsetmc(tsetmc)
    id_col,ids=explicit_ids(df)

    t_ids={r["instrument_id"] for r in trecs}
    exact_id_matches=[x for x in ids if x in t_ids]
    exact_id_complete=bool(ids) and len(exact_id_matches)==len(ids) and len(ids)==len(set(ids))

    os_symbols=normalized_symbols(df[SYMBOL_COLUMN].tolist()) if SYMBOL_COLUMN in df.columns else []
    t_symbols=[r["symbol"] for r in trecs]
    os_unique=len(os_symbols)==len(set(os_symbols))
    t_unique=len(t_symbols)==len(set(t_symbols))
    t_by_symbol={}
    for r in trecs:
        t_by_symbol.setdefault(r["symbol"],[]).append(r)
    symbol_matches=sum(1 for s in os_symbols if len(t_by_symbol.get(s,[]))==1)
    symbol_ambiguous=sum(1 for s in os_symbols if len(t_by_symbol.get(s,[]))>1)
    symbol_not_found=sum(1 for s in os_symbols if s not in t_by_symbol)

    if exact_id_complete:
        identity_method="EXACT_ID_MATCH"
        field_reconciliation="IDENTITY_READY_FOR_FIELD_COMPARISON"
    elif os_symbols and os_unique and t_unique and symbol_matches == len(os_symbols):
        identity_method="EXPLICIT_SYMBOL_MATCH"
        field_reconciliation="IDENTITY_READY_FOR_FIELD_COMPARISON"
    elif os_symbols and os_unique and t_unique and symbol_matches > 0:
        identity_method="PARTIAL_EXPLICIT_SYMBOL_MATCH"
        field_reconciliation="PARTIAL_IDENTITY_READY_UNMATCHED_ROWS_BLOCKED"
    else:
        identity_method="NO_SAFE_IDENTITY_MATCH"
        field_reconciliation="BLOCKED_UNTIL_EXPLICIT_ID_OR_UNIQUE_SYMBOL_MATCH"

    row_mappings=[]
    for i, s in enumerate(os_symbols, start=1):
        matches=t_by_symbol.get(s,[])
        if len(matches)==1:
            r=matches[0]
            row_mappings.append({
                "optionschool_row":i,
                "symbol":s,
                "mapping_status":"EXACT_UNIQUE_SYMBOL_MATCH",
                "tsetmc_instrument_id":r["instrument_id"],
                "tsetmc_contract_type":r["contract_type"],
                "tsetmc_underlying_id":r["underlying_id"],
                "tsetmc_underlying_symbol":r["underlying_symbol"],
                "tsetmc_strike":r["strike"],
                "tsetmc_begin_date":r["begin_date"],
                "tsetmc_end_date":r["end_date"],
                "tsetmc_remaining_days":r["remaining_days"]
            })
        elif len(matches)>1:
            row_mappings.append({"optionschool_row":i,"symbol":s,"mapping_status":"AMBIGUOUS_SYMBOL"})
        else:
            row_mappings.append({"optionschool_row":i,"symbol":s,"mapping_status":"SYMBOL_NOT_FOUND"})

    return {
      "status":"SUCCESS",
      "workbook_sha256":sha256_file(workbook),
      "workbook_rows":int(len(df)),
      "workbook_columns":int(len(df.columns)),
      "explicit_option_id_column":id_col,
      "explicit_option_id_count":len(ids),
      "tsetmc_record_count":len(trecs),
      "exact_id_matches":len(exact_id_matches),
      "exact_id_match_rate":(len(exact_id_matches)/len(ids)) if ids else None,
      "exact_id_match_complete":exact_id_complete,
      "optionschool_symbol_column":SYMBOL_COLUMN if SYMBOL_COLUMN in df.columns else None,
      "optionschool_symbol_count":len(os_symbols),
      "optionschool_symbol_unique":os_unique,
      "tsetmc_symbol_unique":t_unique,
      "unique_symbol_matches":symbol_matches,
      "ambiguous_symbol_matches":symbol_ambiguous,
      "symbol_not_found":symbol_not_found,
      "symbol_match_rate":(symbol_matches/len(os_symbols)) if os_symbols else None,
      "identity_method":identity_method,
      "tsetmc_snapshot_sha256":tmeta.get("snapshot_sha256"),
      "tsetmc_endpoint":tmeta.get("endpoint"),
      "tsetmc_retrieved_at":tmeta.get("retrieved_at"),
      "identity_inference":"DISABLED",
      "production_changed":False,
      "field_reconciliation":field_reconciliation,
      "row_mapping_count":len(row_mappings),
      "row_mapping_exact_unique_count":sum(1 for x in row_mappings if x["mapping_status"]=="EXACT_UNIQUE_SYMBOL_MATCH"),
      "row_mapping_unmatched_count":sum(1 for x in row_mappings if x["mapping_status"]!="EXACT_UNIQUE_SYMBOL_MATCH"),
      "row_mappings":row_mappings,
      "note":"Symbol matching is accepted only as an exact explicit source-field match after uniqueness is verified in both snapshots. It is not inference. Derived-field equality requires a separate formula reconciliation layer."
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
