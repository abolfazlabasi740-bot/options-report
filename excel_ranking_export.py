#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Six-block option ranking export to a columnar Excel (.xlsx) workbook.

Produces a real .xlsx file where:
  - Each option contract is one row.
  - Rows are ordered by the six-block TSETMC evidence score (descending).
  - The eleven user-facing columns from the option-market ranking come first.
  - Each of the six blocks (LIQUIDITY, VALUATION, PAYOFF, TIME, GREEKS, MARKET)
    has its own score column, in the canonical block order, followed by the
    total six-block score and the global rank.

The workbook is written next to the ranking JSON artifact and is also returned
by path so the Bale listener can attach it. openpyxl is the only dependency.
"""
from __future__ import annotations

import json
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from bale_option_market_cards import OPTION_COLUMNS, rank_snapshot
from tsetmc_scoring_engine import BLOCK_WEIGHTS

ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "output" / "tsetmc_first"

# Block order follows tsetmc_scoring_engine.BLOCK_WEIGHTS insertion order:
# LIQUIDITY, VALUATION, PAYOFF, TIME, GREEKS, MARKET.
BLOCK_ORDER = tuple(BLOCK_WEIGHTS.keys())

# Persian labels for the six-block score columns.
BLOCK_LABELS = {
    "LIQUIDITY": "بلوک نقدشوندگی",
    "VALUATION": "بلوک ارزش‌گذاری",
    "PAYOFF": "بلوک پایه (Payoff)",
    "TIME": "بلوک زمان",
    "GREEKS": "بلوک Greeks",
    "MARKET": "بلوک بازار",
}

TOTAL_SCORE_LABEL = "امتیاز کل شش‌بلوک"
RANK_LABEL = "رتبه کلی"

HEADER_FILL = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
HEADER_FONT = Font(bold=True, color="FFFFFF", size=11)
HEADER_ALIGN = Alignment(horizontal="center", vertical="center", wrap_text=True)
RIGHT_ALIGN = Alignment(horizontal="right", vertical="center")


def _column_headers():
    """Eleven user-facing columns + one column per block + total score + rank."""
    headers = list(OPTION_COLUMNS)
    for block in BLOCK_ORDER:
        headers.append(BLOCK_LABELS[block])
    headers.append(TOTAL_SCORE_LABEL)
    headers.append(RANK_LABEL)
    return headers


def _row_values(row):
    """Flatten one ranking display row into the ordered Excel cell values."""
    # The eleven canonical columns, in OPTION_COLUMNS order.
    values = [row.get(col) for col in OPTION_COLUMNS]

    block_scores = row.get("block_scores") or {}
    for block in BLOCK_ORDER:
        score = block_scores.get(block)
        if isinstance(score, (int, float)):
            values.append(round(float(score), 4))
        else:
            values.append(None)

    total = row.get("امتیاز شش‌بلوک")
    if isinstance(total, (int, float)):
        values.append(round(float(total), 4))
    else:
        values.append(None)

    values.append(row.get("rank"))
    return values


def export_ranking_excel(payload, *, dest=None):
    """Write the six-block ranking payload to a columnar .xlsx workbook.

    ``payload`` is the structure returned by ``bale_option_market_cards.rank_snapshot``
    (or loaded from ``latest_option_market_ranking.json``). Rows are sorted by the
    six-block score descending so the sheet reads top-to-bottom in rank order.

    Returns the absolute Path of the written workbook.
    """
    rows = list(payload.get("rows") or [])
    # Stable descending sort: highest six-block score first, then global rank.
    rows.sort(
        key=lambda r: (
            -(r.get("امتیاز شش‌بلوک") if isinstance(r.get("امتیاز شش‌بلوک"), (int, float)) else -1.0),
            r.get("rank") if isinstance(r.get("rank"), int) else 0,
            str(r.get("نماد") or ""),
        )
    )

    dest_path = Path(dest) if dest else OUTPUT_DIR / "latest_option_market_ranking.xlsx"
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "رتبه‌بندی شش‌بلوک"

    headers = _column_headers()
    sheet.append(headers)
    for column_index, _ in enumerate(headers, start=1):
        cell = sheet.cell(row=1, column=column_index)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = HEADER_ALIGN

    for row in rows:
        sheet.append(_row_values(row))

    # Right-to-left sheet direction for Persian readability.
    sheet.sheet_view.rightToLeft = True

    # Reasonable column widths: fixed width for the long text columns, a touch
    # narrower for the numeric block/score columns at the end.
    text_widths = {
        "نماد": 16, "نوع قرارداد": 12, "سهم پایه": 14, "تاریخ سررسید": 14,
    }
    last_text_col = len(OPTION_COLUMNS)
    for column_index in range(1, last_text_col + 1):
        header_text = headers[column_index - 1]
        width = text_widths.get(header_text, 13)
        sheet.column_dimensions[get_column_letter(column_index)].width = width
    for column_index in range(last_text_col + 1, len(headers) + 1):
        sheet.column_dimensions[get_column_letter(column_index)].width = 16

    # Freeze the header row and the symbol column so the sheet stays navigable.
    sheet.freeze_panes = "B2"

    workbook.save(dest_path)
    return dest_path


def build_ranking_excel(symbol=None, *, refresh=False):
    """Build (or load) the ranking payload and export it to Excel.

    When ``symbol`` is given, the workbook is filtered to that underlying symbol
    only, preserving the global six-block rank order — matching the drill-down
    reached from the "نمادها" glass button.
    """
    from bale_option_market_cards import _build_report, _load_report, _norm_symbol

    payload = _build_report() if refresh else (_load_report() or _build_report())
    if symbol:
        target = _norm_symbol(symbol)
        filtered = {
            **payload,
            "rows": [
                row for row in (payload.get("rows") or [])
                if _norm_symbol(row.get("سهم پایه")) == target
            ],
        }
        payload = filtered
        dest = OUTPUT_DIR / f"symbol_{target}_options_ranking.xlsx"
    else:
        dest = OUTPUT_DIR / "latest_option_market_ranking.xlsx"

    return export_ranking_excel(payload, dest=dest)


def _self_check():
    """Smoke path: build from a synthetic snapshot, then read the workbook back."""
    import tempfile

    snapshot = {
        "source_of_truth": "TSETMC",
        "generated_at": "2099-01-01T00:00:00+00:00",
        "data_mode": "LIVE_TSETMC_REFRESH",
        "snapshot_sha256": "x" * 64,
        "rows": [
            {
                "canonical": {
                    "نماد": "OPT1", "قیمت اعمال": 100, "قیمت سهم پایه": 110,
                    "تاریخ سررسید": "20990120", "روزهای تقویمی": 20,
                    "آخرین قیمت": 5, "قیمت پایانی": 5, "حجم معاملات": 1000,
                    "ارزش معاملات": 5000, "تعداد معاملات": 10,
                    "بیشترین قیمت": 5.5, "کمترین قیمت": 4.5,
                },
                "identity": {
                    "instrument_id": "I1", "underlying_id": "U1",
                    "underlying_symbol": "BASE1", "contract_type": "CALL",
                },
            },
            {
                "canonical": {
                    "نماد": "OPT2", "قیمت اعمال": 120, "قیمت سهم پایه": 110,
                    "تاریخ سررسید": "20990120", "روزهای تقویمی": 20,
                    "آخرین قیمت": 2, "قیمت پایانی": 2, "حجم معاملات": 10,
                    "ارزش معاملات": 20, "تعداد معاملات": 1,
                    "بیشترین قیمت": 2.2, "کمترین قیمت": 1.8,
                },
                "identity": {
                    "instrument_id": "I2", "underlying_id": "U2",
                    "underlying_symbol": "BASE2", "contract_type": "CALL",
                },
            },
        ],
    }
    payload = rank_snapshot(snapshot)
    with tempfile.TemporaryDirectory() as tmp:
        path = export_ranking_excel(payload, dest=Path(tmp) / "rank.xlsx")
        text = path.read_bytes()[:2]
        assert text == b"PK", "xlsx must start with the PK zip signature"
        assert path.exists() and path.stat().st_size > 0
        print(f"SELF_CHECK_OK rows={len(payload.get('rows') or [])} path={path}")


if __name__ == "__main__":
    _self_check()
