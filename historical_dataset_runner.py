#!/usr/bin/env python3
from __future__ import annotations
import argparse, glob, hashlib, json
from pathlib import Path
from typing import Any
import pandas as pd
from historical_sensitivity_audit import run_sensitivity

def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

def run_file(path: Path, top_n: int) -> dict[str, Any]:
    book={"file":path.name,"path":str(path),"sha256":sha256_file(path),"sheets":[]}
    for sheet in pd.ExcelFile(path).sheet_names:
        item={"sheet":sheet}
        try:
            df=pd.read_excel(path,sheet_name=sheet)
            item["row_count"]=int(len(df)); item["column_count"]=int(len(df.columns))
            item["columns"]=list(map(str,df.columns))
            try:
                item["status"]="SENSITIVITY_OK"
                item["evidence"]=run_sensitivity(df,top_n=top_n)
            except Exception as exc:
                item["status"]="UNRESOLVED"; item["error_type"]=type(exc).__name__; item["error"]=str(exc)
        except Exception as exc:
            item["status"]="UNRESOLVED"; item["error_type"]=type(exc).__name__; item["error"]=str(exc)
        book["sheets"].append(item)
    return book

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("input_glob"); ap.add_argument("--output",default="g7_2_historical_sensitivity_evidence.json")
    ap.add_argument("--top-n",type=int,default=15)
    args=ap.parse_args()
    paths=[Path(p) for p in sorted(glob.glob(args.input_glob)) if Path(p).is_file()]
    if not paths: raise SystemExit("NO_HISTORICAL_FILES_MATCHED")
    result={"audit":"G7-2_HISTORICAL_DATASET_RUNNER","status":"EVIDENCE_ONLY","production_mutation":False,
            "top_n":args.top_n,"files":[run_file(p,args.top_n) for p in paths]}
    Path(args.output).write_text(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True),encoding="utf-8")
    print(json.dumps({"status":result["status"],"files":len(paths),"output":args.output},ensure_ascii=False))
    return 0
if __name__=="__main__": raise SystemExit(main())
