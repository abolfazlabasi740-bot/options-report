import json
from pathlib import Path

from historical_pattern_forward_engine import build_historical_pattern_forward_report


def _snapshot(
    path: Path,
    sha: str,
    ts: str,
    last: float,
    volume: float,
    value: float,
    oi: float,
    underlying: float,
):
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
    path.write_text(
        json.dumps(
            {
                "source_of_truth": "TSETMC",
                "snapshot_sha256": sha,
                "observation_retrieved_at": ts,
                "rows": [row],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def test_forward_uses_first_meaningful_change_not_duplicate_snapshot(tmp_path):
    d = tmp_path / "output" / "history" / "tsetmc"
    d.mkdir(parents=True)

    _snapshot(d / "a.json", "a", "2026-09-28T09:30:00+00:00", 100, 100, 1000, 100, 1000)
    _snapshot(d / "b.json", "b", "2026-09-28T10:00:00+00:00", 110, 200, 2000, 120, 1010)
    _snapshot(d / "c.json", "c", "2026-09-28T10:30:00+00:00", 110, 200, 2000, 120, 1010)
    _snapshot(d / "d.json", "d", "2026-09-28T11:00:00+00:00", 121, 300, 3000, 130, 1020)

    result = build_historical_pattern_forward_report(tmp_path)

    assert result["status"] == "PASS"
    assert result["engine_version"] == "TSETMC-HISTORICAL-PATTERN-FORWARD-1.1"
    assert result["forward_horizon"] == "FIRST_MEANINGFUL_CHANGE_AFTER_PATTERN"
    assert result["forward_valid_transition_count"] == 2

    pattern = next(
        p for p in result["patterns"]
        if p["signature"] == "PRICE_UP_VOLUME_UP + PRICE_UP_OI_UP + OPTION_UP_UNDERLYING_UP"
    )
    assert pattern["observed_occurrences"] == 1
    assert pattern["forward_valid_occurrences"] == 1
    assert pattern["outcomes"][0]["forward_observation_to"] == "2026-09-28T11:00:00+00:00"
    assert pattern["outcomes"][0]["last_change_pct"] == 0.1


def test_forward_does_not_infer_missing_instrument(tmp_path):
    d = tmp_path / "output" / "history" / "tsetmc"
    d.mkdir(parents=True)

    _snapshot(d / "a.json", "a", "2026-09-28T09:30:00+00:00", 100, 100, 1000, 100, 1000)
    _snapshot(d / "b.json", "b", "2026-09-28T10:00:00+00:00", 110, 200, 2000, 120, 1010)
    _snapshot(d / "c.json", "c", "2026-09-28T10:30:00+00:00", 110, 200, 2000, 120, 1010)

    payload = json.loads((d / "c.json").read_text(encoding="utf-8"))
    payload["rows"] = []
    (d / "c.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    result = build_historical_pattern_forward_report(tmp_path)

    assert result["status"] == "PASS"
    assert result["forward_valid_transition_count"] == 1
    assert all(
        outcome["instrument_id"] == "I1"
        for pattern in result["patterns"]
        for outcome in pattern["outcomes"]
    )
