#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Evidence-only check for explicit TSETMC option identity in an OptionSchool24 workbook."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd


ACCEPTED_ID_ALIASES = (
    "insCode",
    "InsCode",
    "instrument_id",
    "InstrumentID",
    "کد نماد",
    "کد معاملاتی",
)


def inspect_workbook(path: str | Path) -> dict:
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(source)

    raw = source.read_bytes()
    df = pd.read_excel(source)

    present = [name for name in ACCEPTED_ID_ALIASES if name in df.columns]
    populated = {}
    for name in present:
        populated[name] = int(df[name].notna().sum())

    return {
        "status": "EXPLICIT_ID_AVAILABLE" if any(populated.values()) else "NO_EXPLICIT_OPTION_ID",
        "source_file": source.name,
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "rows": int(len(df)),
        "columns": int(len(df.columns)),
        "accepted_id_aliases_present": present,
        "populated_id_counts": populated,
        "identity_inference": "DISABLED",
        "promotion_ready": bool(any(populated.values())),
        "note": (
            "Promotion-ready means only that the workbook contains a populated "
            "accepted explicit option-ID column. It does not prove a TSETMC match."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("workbook")
    args = parser.parse_args()
    print(json.dumps(inspect_workbook(args.workbook), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
