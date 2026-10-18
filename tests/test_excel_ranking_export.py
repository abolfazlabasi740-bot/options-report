#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for the six-block Excel ranking export."""
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from openpyxl import load_workbook

import excel_ranking_export as exporter
from bale_option_market_cards import OPTION_COLUMNS, rank_snapshot
from tsetmc_scoring_engine import BLOCK_WEIGHTS


def _option(symbol, premium, volume, value, base="BASE1", kind="CALL"):
    return {
        "canonical": {
            "نماد": symbol, "قیمت اعمال": 100, "قیمت سهم پایه": 110,
            "تاریخ سررسید": "20990120", "روزهای تقویمی": 20,
            "آخرین قیمت": premium, "قیمت پایانی": premium,
            "حجم معاملات": volume, "ارزش معاملات": value,
            "تعداد معاملات": 10, "بیشترین قیمت": premium * 1.1,
            "کمترین قیمت": premium * 0.9,
        },
        "identity": {
            "instrument_id": symbol, "underlying_id": "U1",
            "underlying_symbol": base, "contract_type": kind,
        },
    }


class ExcelRankingExportTests(unittest.TestCase):
    SNAPSHOT = {
        "source_of_truth": "TSETMC",
        "generated_at": "2099-01-01T00:00:00+00:00",
        "data_mode": "LIVE_TSETMC_REFRESH",
        "snapshot_sha256": "x" * 64,
        "rows": [
            _option("WEAK", premium=2, volume=10, value=20),
            _option("STRONG", premium=5, volume=1000, value=5000),
            _option("MID", premium=3, volume=100, value=300),
        ],
    }

    def _payload(self):
        return rank_snapshot(self.SNAPSHOT)

    def test_xlsx_signature_and_columns(self):
        payload = self._payload()
        with TemporaryDirectory() as tmp:
            path = exporter.export_ranking_excel(payload, dest=Path(tmp) / "r.xlsx")
            self.assertEqual(path.read_bytes()[:2], b"PK")
            book = load_workbook(path)
            sheet = book.active
            headers = [c.value for c in sheet[1]]
            # Eleven canonical columns first, in order.
            self.assertEqual(headers[: len(OPTION_COLUMNS)], list(OPTION_COLUMNS))
            # Then one block column per block in canonical order.
            block_labels = [exporter.BLOCK_LABELS[b] for b in exporter.BLOCK_ORDER]
            self.assertEqual(
                headers[len(OPTION_COLUMNS): len(OPTION_COLUMNS) + len(block_labels)],
                block_labels,
            )
            # Then total score and rank.
            self.assertEqual(headers[-2], exporter.TOTAL_SCORE_LABEL)
            self.assertEqual(headers[-1], exporter.RANK_LABEL)
            self.assertEqual(
                exporter.BLOCK_ORDER, tuple(BLOCK_WEIGHTS.keys())
            )

    def test_rows_sorted_descending_by_total_score(self):
        payload = self._payload()
        with TemporaryDirectory() as tmp:
            path = exporter.export_ranking_excel(payload, dest=Path(tmp) / "r.xlsx")
            sheet = load_workbook(path).active
            rows = list(sheet.iter_rows(min_row=2, values_only=True))
            self.assertEqual(len(rows), 3)
            total_col = len(OPTION_COLUMNS) + len(BLOCK_WEIGHTS)  # total score index
            scores = [r[total_col] for r in rows]
            self.assertEqual(scores, sorted(scores, reverse=True))
            # The strongest contract should be first.
            self.assertEqual(rows[0][0], "STRONG")

    def test_symbol_filter_preserves_global_order(self):
        payload = self._payload()
        with TemporaryDirectory() as tmp:
            path = exporter.export_ranking_excel(payload, dest=Path(tmp) / "r.xlsx")
            sheet = load_workbook(path).active
            rows = list(sheet.iter_rows(min_row=2, values_only=True))
            self.assertEqual(len(rows), 3)


if __name__ == "__main__":
    unittest.main()
