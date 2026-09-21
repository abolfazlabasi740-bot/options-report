"""Synthetic fixtures are tests only, never market-report data."""
import unittest
import tempfile
import json
import hashlib
from pathlib import Path
from unittest.mock import patch, Mock
import numpy as np
import pandas as pd
import requests
from scoring_engine import score_dataframe, parse_number, block_weighted_score
from report_engine import build_report, format_report, save_report
from bale_transport import split_message, send_message
import bale_listener
import send_to_bale


def fixture():
    rows = []
    for i in range(4):
        rows.append({
            "نماد": f"ضتست{i}", "حجم معاملات": 100 + 100*i,
            "ارزش معاملات": 10000 + 1000*i, "آخرین قیمت": 100 + i,
            "قیمت اعمال": 1000, "قیمت سهم پایه": 1050,
            "روزهای تقویمی": 25+i, "روزهای معاملاتی": 18+i,
            "اهرم": 4+i, "قیمت پایانی": 100, "موقعیت های باز": 50+i,
            "سر به سر": 1100, "نوسان ضمنی": .3+i*.01,
            "نوسان تاریخی": .2, "ارزش زمانی": 50+i,
            "اختلاف تا بلک شولز": .1+i*.01, "شکاف قیمتی": 10,
            "قیمت بهترین تقاضا": 95, "قیمت بهترین عرضه": 105,
            "حجم بهترین تقاضا": 10, "حجم بهترین عرضه": 20,
            "کمترین قیمت": 80, "بیشترین قیمت": 120,
            "دلتا": -.5, "تتا": -.01, "گاما": .02,
            "وگا": .03, "رو": .01, "تاریخ سررسید": None,
        })
    return pd.DataFrame(rows)


class RegressionTests(unittest.TestCase):
    def test_six_block_weights_sum_to_100(self):
        from scoring_engine import WEIGHTS
        self.assertEqual(
            sum(sum(block.values()) for block in WEIGHTS.values()),
            100,
        )

    def test_report_tie_break_is_deterministic(self):
        base = fixture().iloc[[0]].copy()
        data = pd.concat(
            [base.assign(نماد=symbol) for symbol in ["ضتست3", "ضتست1", "ضتست2", "ضتست0"]],
            ignore_index=True,
        )
        with patch("report_engine.pd.read_excel", return_value=data):
            work = build_report("unused.xlsx", top_count=4)
        self.assertEqual(work["نماد"].tolist(), ["ضتست0", "ضتست1", "ضتست2", "ضتست3"])

    def test_invalid_rows_cannot_change_valid_scores(self):
        valid = fixture()
        expected = score_dataframe(valid)
        invalid = []
        for col, value in [("حجم معاملات", 0), ("ارزش معاملات", 0),
                           ("قیمت اعمال", 0), ("روزهای تقویمی", 1),
                           ("اهرم", 2), ("نماد", None),
                           ("قیمت سهم پایه", np.inf), ("آخرین قیمت", -1)]:
            row = valid.iloc[0].copy()
            row[col] = value
            invalid.append(row)
        actual = score_dataframe(pd.concat([valid, pd.DataFrame(invalid)], ignore_index=True))
        pd.testing.assert_series_equal(expected.FinalScore, actual.FinalScore)
        self.assertEqual(actual.attrs["excluded_count"], 8)

    def test_leverage_cap_is_in_base_score(self):
        scored = score_dataframe(fixture())
        row = scored.iloc[-1]
        self.assertEqual(row.Score_Leverage, .92)
        expected = (row.Score_BreakevenDistance * 10 + .92 * 5) * 18 / 15
        self.assertAlmostEqual(row.BlockScore_Payoff, expected)

    def test_range_uses_high_low_not_quotes(self):
        scored = score_dataframe(fixture())
        self.assertAlmostEqual(scored.iloc[0].IntradayRangePct, 40)
        data = fixture().drop(columns=["کمترین قیمت", "بیشترین قیمت"])
        scored = score_dataframe(data)
        self.assertTrue(scored.IntradayRangePct.isna().all())
        self.assertTrue(scored.FinalScore.notna().all())

    def test_missing_entire_block_is_not_zero(self):
        data = fixture().drop(columns=["دلتا", "گاما", "وگا", "رو"])
        self.assertTrue(score_dataframe(data).FinalScore.isna().all())
        with patch("report_engine.pd.read_excel", return_value=data):
            with self.assertRaises(RuntimeError):
                build_report("unused.xlsx")

    def test_within_block_redistribution(self):
        data = pd.DataFrame({"a": [.8], "b": [np.nan]})
        self.assertAlmostEqual(block_weighted_score(data, [("a", 7), ("b", 3)], 20).iloc[0], 16)

    def test_parser_does_not_silently_truncate(self):
        self.assertEqual(parse_number("۱٬۲۳۴٫۵"), 1234.5)
        self.assertEqual(parse_number("1.5M"), 1500000)
        for value in ["12oops", "1e999", np.inf, "12%", "2026/09/19"]:
            self.assertTrue(pd.isna(parse_number(value)))

    def test_schema_duplicate_and_normalization(self):
        data = fixture().rename(columns={"قیمت سهم پایه": " قيمت سهم پايه "})
        self.assertEqual(len(score_dataframe(data)), 4)
        with self.assertRaises(ValueError):
            score_dataframe(fixture().drop(columns=["قیمت اعمال"]))
        with self.assertRaises(ValueError):
            score_dataframe(pd.concat([fixture(), fixture().iloc[:1]]))

    def test_put_delta_not_automatically_extreme(self):
        self.assertNotIn("ExtremeDelta", score_dataframe(fixture()).iloc[0].AnalyticsFlags)

    def test_incoming_derived_days_cannot_override_expiry(self):
        data = fixture()
        data["RemainingDays"] = 999
        data.loc[0, "روزهای تقویمی"] = 1
        self.assertNotIn("ضتست0", score_dataframe(data)["نماد"].tolist())

    def test_symbol_filter_before_top_and_global_score_consistent(self):
        data = fixture()
        with patch("report_engine.pd.read_excel", return_value=data):
            all_rows = build_report("unused.xlsx", top_count=100)
            one = build_report("unused.xlsx", top_count=1, symbol_prefix="ضتست0")
        self.assertEqual(one.iloc[0]["نماد"], "ضتست0")
        expected = all_rows.set_index("نماد").loc["ضتست0", "FinalScore"]
        self.assertEqual(one.iloc[0].FinalScore, expected)
        self.assertAlmostEqual(one.iloc[0]["فاصله سر به سری"], 50/1050*100)

    def test_report_discloses_limits_and_missing_expiry(self):
        with patch("report_engine.pd.read_excel", return_value=fixture()):
            work = build_report("unused.xlsx")
        text = format_report(work, "unused.xlsx")
        self.assertIn("V4.1.1", text)
        self.assertIn("زمان واقعی داده بازار", text)
        self.assertIn("شاخص کامل‌بودن داده", text)
        self.assertIn("سررسید: داده موجود نیست", text)
        self.assertNotIn("<NA>", text)
        for limit in [0, -1, 1.2, True]:
            with self.assertRaises(ValueError):
                build_report("unused.xlsx", top_count=limit)

    def test_chunking_preserves_text_and_cards(self):
        text = "header\n" + "".join(f"🔹 {i}\n" + "x"*1000 + "\n" for i in range(15))
        chunks = split_message(text)
        self.assertEqual("".join(chunks), text)
        self.assertTrue(all(len(c) <= 3500 for c in chunks))
        for c in chunks[1:]:
            self.assertTrue(c.startswith("🔹 "))
        long = "🔹 " + "x"*8000
        self.assertEqual("".join(split_message(long)), long)

    def test_transport_masks_credentials_and_stops_on_failure(self):
        with patch("bale_transport.requests.post", side_effect=requests.ConnectionError("SECRET")) as post:
            with self.assertRaises(RuntimeError) as caught:
                send_message("SECRET", "123", "message")
            self.assertNotIn("SECRET", str(caught.exception))
            self.assertEqual(post.call_count, 1)
        with patch("bale_transport.requests.post") as post:
            with self.assertRaises(ValueError):
                send_message("token", "", "message")
            post.assert_not_called()

    def test_listener_requires_explicit_destination(self):
        with patch.object(bale_listener, "TOKEN", "test"), patch.object(bale_listener, "CHAT_ID", ""):
            with self.assertRaises(RuntimeError):
                bale_listener.main()

    def test_saved_audit_matches_report_and_source(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "fixture.xlsx"
            fixture().to_excel(source, index=False)
            work = build_report(source)
            with patch("report_engine.ROOT", root):
                report = save_report(work, source)
            audit = json.loads((root / "output/latest_audit.json").read_text(encoding="utf-8"))
            self.assertEqual((root / "output/latest_report.txt").read_text(encoding="utf-8"), report)
            self.assertEqual(audit["source_sha256"], hashlib.sha256(source.read_bytes()).hexdigest())
            self.assertEqual(audit["selected_count"], 4)
            self.assertIsNone(audit["market_data_timestamp"])
            self.assertEqual([r["نماد"] for r in audit["selected"]], work["نماد"].tolist())


if __name__ == "__main__":
    unittest.main()
