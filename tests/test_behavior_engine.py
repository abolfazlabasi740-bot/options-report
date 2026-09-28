import json
from pathlib import Path

from behavior_engine import build_behavior_report, format_behavior_report


def _snapshot(path: Path, sha: str, ts: str, last: float, volume: float, value: float, oi: float, underlying: float):
    row = {
        "canonical": {
            "نماد": "ضTEST",
            "آخرین قیمت": last,
            "قیمت پایانی": last,
            "حجم معاملات": volume,
            "ارزش معاملات": value,
            "موقعیت های باز": oi,
            "قیمت سهم پایه": underlying,
        },
        "identity": {
            "instrument_id": "I1",
            "underlying_symbol": "TEST",
            "underlying_id": "U1",
            "contract_type": "CALL",
        },
    }
    payload = {
        "source_of_truth": "TSETMC",
        "snapshot_sha256": sha,
        "observation_retrieved_at": ts,
        "rows": [row],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_behavior_delta(tmp_path):
    root = tmp_path
    d = root / "output" / "history" / "tsetmc"
    d.mkdir(parents=True)
    _snapshot(d / "a.json", "a", "2026-09-28T09:30:00+00:00", 100, 100, 1000, 100, 1000)
    _snapshot(d / "b.json", "b", "2026-09-28T10:00:00+00:00", 110, 200, 2000, 120, 1010)
    result = build_behavior_report(root)
    assert result["status"] == "PASS"
    assert result["transition_count"] == 1
    assert "PRICE_UP_VOLUME_UP" in result["events"][0]["flags"]
    assert "PRICE_UP_OI_UP" in result["events"][0]["flags"]
    assert "OPTION_UP_UNDERLYING_UP" in result["events"][0]["flags"]
    assert "ضTEST" in format_behavior_report(result)


def test_jalali_begin_date_excludes_creation_day(tmp_path):
    root = tmp_path
    d = root / "output" / "history" / "tsetmc"
    d.mkdir(parents=True)
    _snapshot(d / "a.json", "a", "2026-09-28T09:30:00+00:00", 100, 100, 1000, 100, 1000)
    payload = json.loads((d / "a.json").read_text(encoding="utf-8"))
    payload["rows"][0]["identity"]["begin_date"] = "14050706"
    (d / "a.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    _snapshot(d / "b.json", "b", "2026-09-28T10:00:00+00:00", 410, 6100, 16000, 95, 1021)
    result = build_behavior_report(root)
    assert result["transition_count"] == 1
    assert result["events"] == []
