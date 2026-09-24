#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Evidence-only lifecycle analysis for OptionSchool symbols absent from TSETMC.

Absence from the current TSETMC Option Market-Watch is never treated as proof
of expiry/closure. Lifecycle classification is promoted only when an explicit
snapshot retrieval timestamp and a parseable OptionSchool expiry establish
that the contract had already expired before the snapshot.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b):
            h.update(b)
    return h.hexdigest()


def load_symbols(path):
    df = pd.read_excel(path)
    if "نماد" not in df.columns:
        raise ValueError("OptionSchool workbook has no نماد column")
    vals = [str(v).strip() for v in df["نماد"].tolist()
            if pd.notna(v) and str(v).strip()]
    return df, vals


def load_tsetmc_symbols(path):
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    data = payload.get("data", payload)
    root = data.get("instrumentOptMarketWatch", []) if isinstance(data, dict) else []
    rows = []
    for x in root if isinstance(root, list) else []:
        if not isinstance(x, dict):
            continue
        for id_key, sym_key, side in (
            ("insCode_P", "lVal18AFC_P", "PUT"),
            ("insCode_C", "lVal18AFC_C", "CALL"),
        ):
            if x.get(id_key) not in (None, "") and x.get(sym_key) not in (None, ""):
                rows.append({
                    "symbol": str(x[sym_key]).strip(),
                    "instrument_id": str(x[id_key]),
                    "contract_type": side,
                    "underlying_id": str(x["uaInsCode"])
                    if x.get("uaInsCode") not in (None, "") else None,
                    "end_date": x.get("endDate"),
                    "remaining_days": x.get("remainedDay"),
                })
    return payload, rows


def parse_snapshot_time(value):
    if not value:
        return None
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def parse_expiry(value):
    if pd.isna(value):
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value
    text = str(value).strip()
    if not text:
        return None

    # Gregorian/ISO forms supported without guessing the calendar.
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            pass

    # Excel may expose a real datetime-like string.
    try:
        dt = pd.to_datetime(text, errors="raise")
        if hasattr(dt, "to_pydatetime"):
            dt = dt.to_pydatetime()
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def lifecycle_evidence(expiry_raw, snapshot_time):
    expiry = parse_expiry(expiry_raw)
    if expiry is None or snapshot_time is None:
        return {
            "lifecycle_status": "NOT_PROVABLE_FROM_CURRENT_EVIDENCE",
            "closed_or_expired_proven": False,
        }
    if expiry < snapshot_time:
        return {
            "lifecycle_status": "EXPIRED_BEFORE_SNAPSHOT",
            "closed_or_expired_proven": True,
        }
    return {
        "lifecycle_status": "NOT_EXPIRED_BEFORE_SNAPSHOT",
        "closed_or_expired_proven": False,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--optionschool", required=True)
    ap.add_argument("--tsetmc", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument(
        "--snapshot-retrieved-at",
        default=None,
        help="Explicit TSETMC snapshot retrieval timestamp, ISO-8601. "
             "Use only when independently evidenced by the retained wrapper output.",
    )
    a = ap.parse_args()

    df, os_symbols = load_symbols(a.optionschool)
    payload, t_rows = load_tsetmc_symbols(a.tsetmc)
    t_symbols = {r["symbol"] for r in t_rows}

    snapshot_time_raw = (
        a.snapshot_retrieved_at
        or payload.get("retrieved_at_utc")
        or payload.get("retrieved_at")
        or payload.get("timestamp")
    )
    snapshot_time = parse_snapshot_time(snapshot_time_raw)

    expiry_column = "تاریخ سررسید" if "تاریخ سررسید" in df.columns else None
    unmatched = []

    for row_no, symbol in enumerate(os_symbols, start=1):
        if symbol in t_symbols:
            continue

        row = df.iloc[row_no - 1]
        expiry_raw = row[expiry_column] if expiry_column else None
        evidence = lifecycle_evidence(expiry_raw, snapshot_time)

        item = {
            "optionschool_row": row_no,
            "symbol": symbol,
            "expiry_raw": None if pd.isna(expiry_raw) else str(expiry_raw),
            "snapshot_retrieved_at": snapshot_time.isoformat() if snapshot_time else None,
            "classification": "NOT_IN_CURRENT_TSETMC_SNAPSHOT",
            "evidence": (
                "Exact symbol equality check failed because the symbol is absent "
                "from the retained current TSETMC Option Market-Watch snapshot."
            ),
            **evidence,
        }

        if evidence["lifecycle_status"] == "EXPIRED_BEFORE_SNAPSHOT":
            item["classification"] = "EXPIRED_BEFORE_SNAPSHOT"
            item["evidence"] += (
                " OptionSchool expiry is before the independently supplied "
                "TSETMC snapshot retrieval timestamp."
            )

        unmatched.append(item)

    out = {
        "status": "SUCCESS",
        "workbook_sha256": sha256_file(a.optionschool),
        "workbook_rows": int(len(df)),
        "tsetmc_snapshot_sha256": payload.get("snapshot_sha256"),
        "tsetmc_record_count": len(t_rows),
        "optionschool_symbol_count": len(os_symbols),
        "unmatched_count": len(unmatched),
        "snapshot_retrieved_at": snapshot_time.isoformat() if snapshot_time else None,
        "expiry_column": expiry_column,
        "unmatched": unmatched,
        "lifecycle_inference": "DISABLED",
        "identity_inference": "DISABLED",
        "note": (
            "Absence from the current TSETMC snapshot is not proof of closure. "
            "EXPIRED_BEFORE_SNAPSHOT is promoted only when an explicit snapshot "
            "retrieval timestamp and a parseable expiry establish that the "
            "expiry preceded the snapshot. Non-parseable or calendar-ambiguous "
            "expiry remains NOT_PROVABLE_FROM_CURRENT_EVIDENCE."
        ),
    }
    Path(a.output).write_text(
        json.dumps(out, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
