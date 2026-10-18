# -*- coding: utf-8 -*-
"""تست گزارش تحلیل مدیریتی نسخه ۲.۰ — چندعاملی (تکنیکال/پرایس‌اکشن/تابلو)"""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "build_management_analysis_report",
    ROOT / "scripts" / "build_management_analysis_report.py",
)


def _row(sym, score, **kw):
    base = {
        "symbol": sym, "final_score": score, "classification": "A",
        "return_5_sessions_pct": 2.0, "return_20_sessions_pct": 8.0,
        "rsi_14": 62.0, "trend_state": "UP_TREND_STRUCTURE",
        "correction_state": "RECOVERY_BOUNCE",
        "macd_pct": 1.5, "atr_14_pct": 2.4, "volatility_20_pct": 3.1,
        "range_position_20": 0.9, "upper_limit_headroom_pct": 4.2,
        "volume_ratio_5_to_20": 1.7, "value_ratio_5_to_20": 1.8,
        "volume_ratio_5_to_50": 1.4, "warnings": [],
        "early_move": {
            "breakout_above_prior_20_high": True,
            "pre_lock_sequence": {"state": "EARLY", "sequence": "VOLUME → PRICE → MOMENTUM"},
        },
    }
    base.update(kw)
    return base


class ManagementAnalysisReportV2Tests(unittest.TestCase):
    def run_builder(self, rows):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "rolling7.json"
            src.write_text(json.dumps({
                "latest_history_date": "20261015",
                "latest_history_date_jalali": "1405/07/24",
                "rows": rows,
            }, ensure_ascii=False), encoding="utf-8")
            module = importlib.util.module_from_spec(SPEC)
            module.BASE = Path(tmp)
            module.SRC = src
            module.DST = Path(tmp) / "mgmt.json"
            # run module body pieces we need by executing the file with patched paths
            import types, sys
            code = (ROOT / "scripts" / "build_management_analysis_report.py").read_text(encoding="utf-8")
            code = code.replace("SRC = BASE / 'latest_plain_symbol_trend_report_rolling7.json'", "SRC = globals()['_SRC_OVERRIDE']")
            code = code.replace("DST = BASE / 'latest_management_analysis_report.json'", "DST = globals()['_DST_OVERRIDE']")
            mod = types.ModuleType("mgmt_test")
            mod.__dict__["_SRC_OVERRIDE"] = src
            mod.__dict__["_DST_OVERRIDE"] = Path(tmp) / "mgmt.json"
            # BASE must exist before code runs; patch Path expression
            code = code.replace("BASE = Path(__file__).resolve().parents[1] / 'output' / 'base_share'", "BASE = Path(r'%s')" % tmp)
            exec(compile(code, "build_management_analysis_report.py", "exec"), mod.__dict__)
            return json.loads(mod.DST.read_text(encoding="utf-8")) if hasattr(mod, "DST") else json.loads((Path(tmp) / "mgmt.json").read_text(encoding="utf-8"))

    def test_multi_factor_note_and_factors_block(self):
        report = self.run_builder([_row("TEST", 90.0), _row("MISS", 50.0, macd_pct=None, atr_14_pct=None, range_position_20=None, upper_limit_headroom_pct=None, trend_state=None)])
        top = report["top10"]
        self.assertEqual(report["report_version"], "MANAGEMENT_ANALYSIS-2.0")
        self.assertEqual(top[0]["symbol"], "TEST")
        self.assertEqual(top[0]["note_label"], "هم‌گرایی مثبت چندعاملی")
        self.assertIn("شکست سقف ۲۰ جلسه", top[0]["note_detail"])
        self.assertIn("ATR", top[0]["note_detail"])
        f = top[0]["factors"]
        self.assertEqual(f["atr_14_pct"], 2.4)
        self.assertEqual(f["range_position_20"], 0.9)
        self.assertTrue(f["breakout_above_prior_20_high"])
        self.assertEqual(f["pre_lock_state"], "EARLY")
        self.assertEqual(f["board_bestlimits"], "داده موجود نیست — لایه BestLimits در گذر اول قرنطینه است (گیت معنایی)")
        # missing data must be labeled in the detail, never imputed
        self.assertIsNone(top[1]["factors"]["macd_pct"])
        self.assertIn("داده موجود نیست", top[1]["note_detail"])
        self.assertEqual(report["trade_permission"].split(" ")[0], "NOT_PERMITTED")

    def test_negative_convergence_label(self):
        row = _row("NEG", 60.0, trend_state="DOWN_TREND_STRUCTURE", rsi_14=75,
                   macd_pct=-2.0, volume_ratio_5_to_20=0.6, value_ratio_5_to_20=0.7,
                   early_move={"breakout_above_prior_20_high": False, "pre_lock_sequence": {}})
        report = self.run_builder([row])
        self.assertEqual(report["top10"][0]["note_label"], "هم‌گرایی منفی چندعاملی")


if __name__ == "__main__":
    unittest.main()
