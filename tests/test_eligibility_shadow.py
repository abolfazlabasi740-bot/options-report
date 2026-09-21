import pandas as pd
from eligibility_shadow import classify_row, classify_dataframe

def base(**overrides):
    row = {
        "نماد": "ضTEST",
        "آخرین": 10,
        "پایه": 100,
        "RemainingDays": 20,
        "اهرم": 4,
        "FinalScore": 70,
    }
    row.update(overrides)
    return row

def test_active():
    assert classify_row(base())["status"] == "ACTIVE_ELIGIBLE"

def test_expired_is_explicit_not_invalid():
    result = classify_row(base(RemainingDays=0))
    assert result["status"] == "EXPIRED"

def test_missing_leverage_is_not_expired():
    result = classify_row(base(اهرم=None))
    assert result["status"] == "LEVERAGE_UNAVAILABLE"

def test_low_leverage_is_distinguished():
    result = classify_row(base(اهرم=2))
    assert result["status"] == "LEVERAGE_LOW"

def test_missing_remaining_days_is_distinguished():
    assert classify_row(base(RemainingDays=None))["status"] == "MISSING_REMAINING_DAYS"

def test_invalid_market_data():
    assert classify_row(base(پایه=0))["status"] == "INVALID_MARKET_DATA"

def test_dataframe_summary():
    df = pd.DataFrame([base(), base(RemainingDays=0), base(اهرم=None)])
    result = classify_dataframe(df, min_leverage=3.5)
    assert result["summary"]["rows_scanned"] == 3
    assert result["summary"]["counts"]["ACTIVE_ELIGIBLE"] == 1
    assert result["summary"]["counts"]["EXPIRED"] == 1
    assert result["summary"]["counts"]["LEVERAGE_UNAVAILABLE"] == 1


def test_opportunity_universe_retains_expired_and_missing_leverage():
    from eligibility_shadow import opportunity_universe
    df = pd.DataFrame([base(), base(RemainingDays=0), base(اهرم=None)])
    result = opportunity_universe(df, min_leverage=3.5)
    assert result["summary"]["rows_scanned"] == 3
    assert result["summary"]["opportunity_candidates"] == 3
    assert result["summary"]["production_eligible"] == 1
