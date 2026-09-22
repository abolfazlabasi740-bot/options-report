import pandas as pd
from equity_intelligence_shadow import analyze_equities
from equity_evidence_cluster_shadow import build_equity_evidence_clusters

def test_equity_multi_family_cluster():
    df=pd.DataFrame([{"instrument_id":"EQ1","last_price":110,"close_price":100,"volume":1000,"trade_value":50000}])
    r=analyze_equities(df,"s1")
    c=build_equity_evidence_clusters(r["cases"])
    assert c["summary"]["cluster_count"]==1
    assert c["clusters"][0]["independent_family_count"]>=2
    assert c["clusters"][0]["direction_inference"]=="DISABLED"

def test_equity_single_family_no_cluster():
    df=pd.DataFrame([{"instrument_id":"EQ1","last_price":110,"close_price":100}])
    r=analyze_equities(df,"s1")
    c=build_equity_evidence_clusters([r["cases"][0]])
    assert c["summary"]["cluster_count"]==0

def test_equity_cluster_deterministic():
    df=pd.DataFrame([{"instrument_id":"EQ1","last_price":110,"close_price":100,"volume":1000}])
    r=analyze_equities(df,"s1")
    a=build_equity_evidence_clusters(r["cases"]); b=build_equity_evidence_clusters(r["cases"])
    assert a["clusters_sha256"]==b["clusters_sha256"]
