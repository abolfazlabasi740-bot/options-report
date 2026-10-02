#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Audit OptionSchool24 as a supplemental-only evidence source.

Never edits TSETMC snapshots, identities, scores, ranking, or production gates.
OptionSchool rows remain source-local until an independently verified mapping exists.
"""
from __future__ import annotations
import hashlib, json, math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from openpyxl import load_workbook

SOURCE = "OPTIONSCHOOL24_SUPPLEMENTAL_ONLY"
FILE = Path("data/optionschool24_live.xlsx")
OUT = Path("data/optionschool24_supplemental_audit.json")

def clean(v):
    if v is None: return None
    if isinstance(v, str):
        v = v.strip().replace(",", "")
        if not v: return None
    try:
        x = float(v)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return str(v).strip() or None

def normalize_digits(value):
    table = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
    return str(value).translate(table)

def parse_contract_symbol(value):
    """Parse OptionSchool's explicit Persian contract prefix convention.
    ض = CALL, ط = PUT; remaining letters are underlying symbol and trailing digits
    are the contract number. No TSETMC identity is inferred here.
    """
    if value is None:
        return None
    s = normalize_digits(str(value)).strip()
    s = " ".join(s.split())
    import re
    m = re.fullmatch(r"([ضط])\s*([\u0600-\u06FF]+?)\s*(\d+)", s)
    if not m:
        return None
    prefix, underlying, number = m.groups()
    return {
        "contract_type": "CALL" if prefix == "ض" else "PUT",
        "underlying_symbol": underlying.strip(),
        "contract_number": int(number),
        "normalized_contract_symbol": f"{prefix}{underlying.strip()} {int(number)}"
    }

def main():
    # Contract convention regression checks supplied by the project owner.
    examples = {
        "ضفزر ۷۱۹": ("CALL", "فزر", 719),
        "ضسپا ۷۰۲۹": ("CALL", "سپا", 7029),
        "طفزر ۷۱۹": ("PUT", "فزر", 719),
        "طسپا ۷۰۲۹": ("PUT", "سپا", 7029),
    }
    for sample, expected in examples.items():
        got = parse_contract_symbol(sample)
        actual = (got["contract_type"], got["underlying_symbol"], got["contract_number"]) if got else None
        if actual != expected:
            raise SystemExit(f"Contract parser regression: {sample!r}: {actual!r} != {expected!r}")
    raw = FILE.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    wb = load_workbook(FILE, read_only=True, data_only=True)
    ws = wb[wb.sheetnames[0]]
    it = ws.iter_rows(values_only=True)
    headers = [str(x).strip() if x is not None else "" for x in next(it)]
    rows = [dict(zip(headers, r)) for r in it if any(x is not None for x in r)]
    required_relative = ["نماد", "قیمت اعمال", "قیمت سهم پایه", "تاریخ سررسید",
                         "آخرین قیمت", "اختلاف تا بلک شولز", "بلک شولز", "نوسان ضمنی"]
    relative_missing = {k: sum(1 for r in rows if clean(r.get(k)) is None) for k in required_relative}
    relative_complete = sum(1 for r in rows if all(clean(r.get(k)) is not None for k in required_relative))
    chain_required = ["نماد", "قیمت اعمال", "تاریخ سررسید"]
    chain_missing = {k: sum(1 for r in rows if clean(r.get(k)) is None) for k in chain_required}

    parsed = []
    parse_failures = []
    for idx, row in enumerate(rows, start=2):
        identity = parse_contract_symbol(row.get("نماد"))
        if identity is None:
            parse_failures.append({"excel_row": idx, "symbol": str(row.get("نماد"))})
            continue
        parsed.append({**identity, "excel_row": idx,
                       "strike": clean(row.get("قیمت اعمال")),
                       "expiry": str(row.get("تاریخ سررسید")).strip() if row.get("تاریخ سررسید") is not None else None})
    symbol_counts = Counter(x["normalized_contract_symbol"] for x in parsed)
    duplicate_contract_symbols = {k: v for k, v in symbol_counts.items() if v > 1}
    chains = Counter((x["underlying_symbol"], x["contract_type"], x["expiry"]) for x in parsed)
    chain_groups = [
        {"underlying_symbol": k[0], "contract_type": k[1], "expiry": k[2], "member_count": n}
        for k, n in sorted(chains.items(), key=lambda z: (z[0][0], z[0][1], str(z[0][2])))
    ]
    chain_ready = len(parsed) == len(rows) and not duplicate_contract_symbols

    payload = {
      "status": "AUDIT_COMPLETE",
      "source": SOURCE,
      "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
      "file": str(FILE), "file_bytes": len(raw), "sha256": sha,
      "sheet": ws.title, "data_rows": len(rows), "column_count": len(headers),
      "columns": headers,
      "relative_value_anomaly": {
        "status": "RAW_FIELDS_AVAILABLE_REQUIRES_TSETMC_MAPPING_AND_INDEPENDENT_VALIDATION",
        "required_fields": required_relative,
        "missing_rows_by_field": relative_missing,
        "rows_with_all_raw_fields": relative_complete,
        "available_raw_fields": ["بلک شولز", "اختلاف تا بلک شولز", "نوسان ضمنی", "نوسان تاریخی",
          "ارزش ذاتی", "ارزش زمانی", "سر به سر", "اختلاف تا سر به سر",
          "آخرین قیمت", "قیمت سهم پایه", "قیمت اعمال", "حجم معاملات", "ارزش معاملات",
          "قیمت بهترین تقاضا", "قیمت بهترین عرضه", "دلتا", "تتا", "گاما", "وگا", "رو"],
        "constraints": [
          "OptionSchool rows remain supplemental; no TSETMC instrument_id is present in this workbook.",
          "A parsed contract symbol is not itself a TSETMC instrument identity.",
          "Do not change TSETMC snapshots, scores, ranking, or source-of-truth.",
          "Raw Black-Scholes/IV availability is not itself independent economic validation."
        ]
      },
      "chain_structure_anomaly": {
        "status": "IDENTITY_PARSED" if chain_ready else "PARTIAL_PARSE_OR_DUPLICATE_REQUIRES_REVIEW",
        "symbol_convention": {"prefix_ض": "CALL", "prefix_ط": "PUT", "trailing_digits": "contract_number", "middle_text": "underlying_symbol"},
        "parsed_rows": len(parsed),
        "parse_failure_count": len(parse_failures),
        "parse_failures_sample": parse_failures[:25],
        "duplicate_contract_symbols": duplicate_contract_symbols,
        "unique_contract_symbols": len(symbol_counts),
        "chain_group_count": len(chain_groups),
        "chain_groups": chain_groups,
        "identity_fields": ["underlying_symbol", "contract_type", "contract_number", "expiry", "strike"],
        "constraints": [
          "The parsed OptionSchool identity is source-local and supplemental only.",
          "No TSETMC instrument_id is created or replaced.",
          "No chain member-score dispersion is computed until the approved scoring definition is independently validated."
        ]
      },
      "project_boundary": {
        "tsetmc_modified": False,
        "tsetmc_snapshot_files_modified": False,
        "supplemental_only": True,
        "production_signal_authorization": "FORBIDDEN",
        "g7_5_closure": "NOT_AUTHORIZED_BY_THIS_AUDIT_ALONE"
      }
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: payload[k] for k in ("status","file_bytes","sha256","data_rows","column_count","relative_value_anomaly","chain_structure_anomaly","project_boundary")}, ensure_ascii=False, indent=2))

if __name__ == "__main__": main()
