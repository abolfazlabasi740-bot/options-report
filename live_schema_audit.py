#!/usr/bin/env python3
"""Download the live OptionSchool24 export and emit schema metadata only."""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import requests
import pandas as pd
from schema_audit import audit_schema

DEFAULT_URL = "https://s3.optionschool24.com/export/excel?type=1"

def audit_live(url: str = DEFAULT_URL, temp_path: Path = Path("output/.live_optionschool.xlsx")) -> dict:
    response = requests.get(url, timeout=90)
    response.raise_for_status()
    if len(response.content) < 5000 or not response.content.startswith(b"PK"):
        raise RuntimeError("Live source did not return a valid XLSX workbook")
    temp = Path(temp_path)
    temp.parent.mkdir(parents=True, exist_ok=True)
    temp.write_bytes(response.content)
    try:
        df = pd.read_excel(temp)
        audit = audit_schema(df)
        result = {
            "status": "SUCCESS",
            "engine_version": audit["engine_version"],
            "source_url": args.url,
            "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
            "source_sha256": hashlib.sha256(response.content).hexdigest(),
            "row_count": int(len(df)),
            "column_count": int(len(df.columns)),
            "audit": audit,
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return result
    finally:
        temp.unlink(missing_ok=True)

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--output", type=Path, default=Path("output/live_schema_audit.json"))
    args = parser.parse_args()
    result = audit_live(args.url)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
