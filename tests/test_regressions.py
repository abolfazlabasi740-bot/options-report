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
from report_engine import build_report, format_report, save_report, snapshot_id_for
from bale_transport import split_message, send_message
from opportunity_engine import ENGINE_VERSION as OPP_ENGINE_VERSION, run_shadow
from red_team_shadow import ENGINE_VERSION as RED_TEAM_ENGINE_VERSION, challenge_cases
from case_memory_shadow import update_memory
from relative_value_shadow import analyze_chain
from case_explanation_shadow import explain_cases, ENGINE_VERSION as EXPLANATION_ENGINE_VERSION
from chain_identity_shadow import ENGINE_VERSION as CHAIN_ENGINE_VERSION, build_chain_identity
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

    def test_snapshot_id_fallback_is_deterministic(self):
        data = fixture()
        first = snapshot_id_for("missing-fixture.xlsx", data)
        second = snapshot_id_for("missing-fixture.xlsx", data.copy())
        self.assertEqual(first, second)
        self.assertEqual(len(first), 64)

    def test_opportunity_shadow_is_non_destructive_and_auditable(self):
        scored = score_dataframe(fixture())
        before = scored["FinalScore"].copy()

        scored.loc[:, "DataConfidence"] = 100.0
        scored.loc[:, "BlockScore_Liquidity"] = 18.0
        scored.loc[:, "Score_BlackScholesDiff"] = 0.95
        scored.loc[:, "Score_BreakevenDistance"] = 0.90
        scored.loc[:, "ExecutionPenalty"] = 0.05
        scored.loc[:, "RemainingDays"] = 20.0

        result = run_shadow(scored, "snapshot-test")
        self.assertEqual(result["status"], "SUCCESS")
        self.assertEqual(result["engine_version"], OPP_ENGINE_VERSION)
        self.assertEqual(result["summary"]["contracts_scanned"], 4)
        self.assertGreater(result["summary"]["confirmed_total"], 0)
        self.assertTrue(all("evidence" in case for case in result["cases"]))
        pd.testing.assert_series_equal(before, scored["FinalScore"])

    def test_opportunity_shadow_never_infers_contract_direction(self):
        scored = score_dataframe(fixture())
        scored.loc[:, "DataConfidence"] = 100.0
        scored.loc[:, "BlockScore_Liquidity"] = 18.0
        scored.loc[:, "Score_BlackScholesDiff"] = 0.95
        result = run_shadow(scored, "snapshot-direction")
        relative = [c for c in result["cases"] if c["type"] == "RELATIVE_VALUE_ANOMALY"][0]
        self.assertNotIn("BUY", relative["reason"].upper())
        self.assertNotIn("SELL", relative["reason"].upper())

    def test_red_team_challenges_near_expiry_opportunity(self):
        scored = score_dataframe(fixture())
        scored.loc[:, "DataConfidence"] = 100.0
        scored.loc[:, "BlockScore_Liquidity"] = 18.0
        scored.loc[:, "Score_BlackScholesDiff"] = 0.95
        scored.loc[:, "RemainingDays"] = 5.0

        result = run_shadow(scored, "snapshot-redteam")
        self.assertEqual(result["red_team"]["status"], "SUCCESS")
        self.assertEqual(
            result["red_team"]["engine_version"],
            RED_TEAM_ENGINE_VERSION,
        )
        challenged = [
            item for item in result["red_team"]["cases"]
            if item["original_status"] == "CONFIRMED"
        ]
        self.assertTrue(challenged)
        self.assertTrue(
            any(item["challenge_count"] > 0 for item in challenged)
        )

    def test_red_team_is_non_blocking(self):
        scored = score_dataframe(fixture())
        result = run_shadow(scored, "snapshot-nonblocking")
        self.assertEqual(result["status"], "SUCCESS")
        self.assertIn("red_team", result)
        self.assertTrue(
            all(case["status"] in {"CONFIRMED", "WATCH", "REJECTED", "INSUFFICIENT_DATA"}
                for case in result["cases"])
        )

    def test_case_memory_tracks_new_and_persistent_states(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "case_memory.json"
            case = {
                "symbol": "ضتست0",
                "type": "RELATIVE_VALUE_ANOMALY",
                "status": "WATCH",
                "snapshot_id": "s1",
            }
            first = update_memory(path, [case])
            self.assertEqual(first["cases"]["RELATIVE_VALUE_ANOMALY::ضتست0"]["state"], "NEW")

            case2 = dict(case)
            case2["snapshot_id"] = "s2"
            second = update_memory(path, [case2])
            self.assertEqual(
                second["cases"]["RELATIVE_VALUE_ANOMALY::ضتست0"]["state"],
                "PERSISTENT",
            )

    def test_case_memory_never_changes_score_path(self):
        scored = score_dataframe(fixture())
        before = scored["FinalScore"].copy()
        result = run_shadow(scored, "memory-score-test")
        self.assertEqual(result["status"], "SUCCESS")
        pd.testing.assert_series_equal(before, scored["FinalScore"])

    def test_chain_identity_requires_explicit_underlying(self):
        data = fixture()
        data["نماد سهم پایه"] = ["فزر", "فزر", "فزر", "فزر"]
        data["تاریخ سررسید"] = ["1405/07/30"] * 4
        data["نوع قرارداد"] = ["CALL", "PUT", "CALL", "PUT"]

        result = build_chain_identity(data)
        self.assertEqual(result["status"], "SUCCESS")
        self.assertEqual(result["engine_version"], CHAIN_ENGINE_VERSION)
        self.assertEqual(result["summary"]["chain_count"], 1)
        self.assertEqual(result["summary"]["valid_identity_rows"], 4)
        self.assertEqual(
            set(result["chains"].keys()),
            {"فزر::1405/07/30"},
        )

    def test_chain_identity_does_not_guess_from_symbol(self):
        data = fixture()
        result = build_chain_identity(data)
        self.assertEqual(result["status"], "SUCCESS")
        self.assertEqual(result["summary"]["chain_count"], 0)
        self.assertEqual(result["summary"]["insufficient_identity_rows"], 4)
        self.assertTrue(all(
            "MISSING_EXPLICIT_UNDERLYING" in row["reasons"]
            for row in result["rows"]
        ))

    def test_chain_shadow_detects_score_dispersion_without_changing_score(self):
        data = fixture()
        data["نماد سهم پایه"] = ["فزر"] * 4
        data["تاریخ سررسید"] = ["1405/07/30"] * 4
        data["نوع قرارداد"] = ["CALL", "PUT", "CALL", "PUT"]
        scored = score_dataframe(data)
        scored.loc[0, "FinalScore"] = 90.0
        scored.loc[1, "FinalScore"] = 60.0
        before = scored["FinalScore"].copy()

        result = run_shadow(scored, "chain-shadow-test")
        chain_cases = [
            c for c in result["cases"]
            if c["type"] == "CHAIN_STRUCTURE_ANOMALY"
        ]
        self.assertEqual(len(chain_cases), 1)
        self.assertEqual(chain_cases[0]["status"], "WATCH")
        self.assertEqual(chain_cases[0]["evidence"][2]["value"], 1)
        self.assertEqual(chain_cases[0]["evidence"][3]["value"], 30.0)
        pd.testing.assert_series_equal(before, scored["FinalScore"])

    def test_relative_pair_is_evidence_only_and_does_not_claim_parity(self):
        data = fixture()
        data["نماد سهم پایه"] = ["فزر"] * 4
        data["تاریخ سررسید"] = ["1405/07/30"] * 4
        data["نوع قرارداد"] = ["CALL", "PUT", "CALL", "PUT"]
        scored = score_dataframe(data)
        scored.loc[:, "قیمت اعمال"] = [1000.0, 1000.0, 1100.0, 1100.0]
        chain = build_chain_identity(scored)
        cases = analyze_chain(scored, chain, "relative-test")
        self.assertEqual(len(cases), 2)
        self.assertTrue(all(c["type"] == "RELATIVE_PAIR_STRUCTURE" for c in cases))
        self.assertTrue(all(c["status"] in {"WATCH", "INSUFFICIENT_DATA"} for c in cases))
        self.assertTrue(all("mispricing" not in c["reason"].lower() for c in cases))


    def test_case_explanation_is_evidence_only_and_traceable(self):
        cases = [{
            "case_id": "s:RELATIVE:ضتست0",
            "snapshot_id": "s",
            "symbol": "ضتست0",
            "type": "RELATIVE_PAIR_STRUCTURE",
            "status": "WATCH",
            "evidence": [
                {"name": "call_last_price", "value": 10, "source": "آخرین قیمت"},
                {"name": "put_last_price", "value": 8, "source": "آخرین قیمت"},
                {"name": "absolute_difference_last_price", "value": 2, "source": "آخرین قیمت"},
                {"name": "call_implied_volatility", "value": None, "source": "نوسان ضمنی"},
            ],
        }]
        result = explain_cases(cases, snapshot_id="s")
        self.assertEqual(result["status"], "SUCCESS")
        self.assertEqual(result["engine_version"], EXPLANATION_ENGINE_VERSION)
        item_map = {x["name"]: x for x in result["cases"][0]["items"]}
        self.assertEqual(item_map["call_last_price"]["classification"], "OBSERVED")
        self.assertEqual(item_map["absolute_difference_last_price"]["classification"], "EXPLAINED")
        self.assertEqual(item_map["call_implied_volatility"]["classification"], "DATA_GAP")
        self.assertEqual(result["cases"][0]["explanation_status"], "DATA_GAPS_PRESENT")

    def test_case_explanation_marks_red_team_challenge_without_mutation(self):
        cases = [{
            "case_id": "s:RELATIVE:ضتست0",
            "snapshot_id": "s",
            "symbol": "ضتست0",
            "type": "RELATIVE_VALUE_ANOMALY",
            "status": "CONFIRMED",
            "evidence": [{"name": "score", "value": 1, "source": "score"}],
        }]
        red = {"cases": [{
            "case_id": "s:RELATIVE:ضتست0",
            "challenges": [{
                "code": "LOW_CONFIDENCE",
                "evidence": 70,
                "source": "DataConfidence",
                "reason": "Evidence quality is below the confirmation threshold.",
            }],
        }]}
        result = explain_cases(cases, red, "s")
        self.assertEqual(result["cases"][0]["explanation_status"], "RED_TEAM_CHALLENGED")
        self.assertEqual(cases[0]["status"], "CONFIRMED")

    def test_opportunity_engine_persists_case_explanations_without_score_mutation
        import opportunity_engine
        import pandas as pd
        scored = pd.DataFrame([{
            "نماد": "TEST", "FinalScore": 80.0, "DataConfidence": 100.0,
            "AnalyticsFlags": "", "BlockScore_Liquidity": 20.0,
            "Score_BlackScholesDiff": 0.9, "Score_BreakevenDistance": 0.9,
            "BreakevenDistancePct": 1.0, "اختلاف تا بلک شولز": 2.0,
            "ExecutionPenalty": 0.0, "RemainingDays": 20.0, "ارزش معاملات": 100.0,
        }])
        before = scored["FinalScore"].copy()
        result = opportunity_engine.run_shadow(scored, "snapshot-test")
        self.assertEqual(result["status"], "SUCCESS")
        self.assertIn("case_explanations", result)
        self.assertEqual(result["case_explanations"]["status"], "SUCCESS")
        self.assertTrue(scored["FinalScore"].equals(before))

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
