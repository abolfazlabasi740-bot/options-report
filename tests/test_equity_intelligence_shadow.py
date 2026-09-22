import pandas as pd
from equity_intelligence_shadow import analyze_equities, ENGINE_VERSION

def test_equity_only_observes_explicit_fields():
    df=pd.DataFrame([{"instrument_id":"EQ1","نماد":"ABC","last_price":110,"close_price":100,"volume":1000,"trade_value":50000,"return_pct":10,"volume_change_pct":20,"benchmark_return_pct":5,"individual_net_flow":100}])
    r=analyze_equities(df,"snap1")
    assert r["status"]=="SUCCESS" and r["analysis_mode"]=="EQUITY_ONLY" and r["engine_version"]==ENGINE_VERSION
    assert r["summary"]["instrument_count"]==1 and r["cases_sha256"]

def test_missing_instrument_id_never_infers_from_symbol():
    r=analyze_equities(pd.DataFrame([{"نماد":"ABC","last_price":100,"close_price":99}]),"snap1")
    assert r["status"]=="INSUFFICIENT_DATA" and r["cases"]==[]

def test_missing_fields_are_not_zero_filled():
    r=analyze_equities(pd.DataFrame([{"instrument_id":"EQ1","نماد":"ABC"}]),"snap1")
    assert all(c["status"]=="INSUFFICIENT_DATA" for c in r["cases"])

def test_deterministic_output():
    df=pd.DataFrame([{"instrument_id":"EQ1","last_price":100,"close_price":100,"volume":10,"trade_value":1000,"return_pct":0,"volume_change_pct":0}])
    assert analyze_equities(df,"snap1")["cases_sha256"]==analyze_equities(df,"snap1")["cases_sha256"]

def test_no_direction_or_score():
    r=analyze_equities(pd.DataFrame([{"instrument_id":"EQ1","last_price":100,"close_price":90}]),"snap1")
    assert r["rules"]["direction_inference"]=="DISABLED" and r["rules"]["score_change"]=="NONE"
    assert "FinalScore" not in r["cases"][0]
