import copy
from opportunity_evidence_cluster import build_opportunity_evidence_clusters

def case(cid, symbol, typ, status="CONFIRMED", expired=False):
    return {
        "case_id": cid,
        "symbol": symbol,
        "type": typ,
        "status": status,
        "evidence": [{"name": "x", "value": 1, "source": typ}],
        "eligibility": {"status": "EXPIRED" if expired else "ACTIVE_ELIGIBLE"},
    }

def test_three_independent_families_create_confirmed_cluster():
    cases = [
        case("1", "ABC", "RELATIVE_VALUE_ANOMALY"),
        case("2", "ABC", "BREAKEVEN_COMPRESSION"),
        case("3", "ABC", "LIQUIDITY_CONFIRMED"),
    ]
    result = build_opportunity_evidence_clusters(cases)
    assert result["summary"]["cluster_count"] == 1
    cluster = result["clusters"][0]
    assert cluster["status"] == "MULTI_FAMILY_CONFIRMED"
    assert cluster["independent_family_count"] == 3
    assert cluster["source_diversity"] == "SINGLE_SOURCE_OR_DERIVED"
    assert cluster["source_family_count"] == 1


def test_source_diversity_does_not_equate_family_count_with_multi_source_confirmation():
    c1 = case("1", "ABC", "RELATIVE_VALUE_ANOMALY")
    c2 = case("2", "ABC", "BREAKEVEN_COMPRESSION")
    c3 = case("3", "ABC", "LIQUIDITY_CONFIRMED")
    c3["evidence"] = [{"name": "quote", "value": 1, "source": "TSETMC_CURRENT_QUOTE"}]
    result = build_opportunity_evidence_clusters([c1, c2, c3])
    cluster = result["clusters"][0]
    assert cluster["independent_family_count"] == 3
    assert cluster["source_diversity"] == "MULTI_SOURCE"
    assert cluster["source_family_count"] == 2
    assert result["summary"]["multi_source_cluster_count"] == 1
    assert result["rules"]["family_count_is_not_source_independence"] is True

def test_one_family_does_not_create_cluster():
    result = build_opportunity_evidence_clusters(
        [case("1", "ABC", "RELATIVE_VALUE_ANOMALY")]
    )
    assert result["clusters"] == []

def test_two_families_create_watch_cluster():
    result = build_opportunity_evidence_clusters([
        case("1", "ABC", "RELATIVE_VALUE_ANOMALY"),
        case("2", "ABC", "BREAKEVEN_COMPRESSION"),
    ])
    assert result["clusters"][0]["status"] == "MULTI_FAMILY_WATCH"

def test_contradictory_red_team_evidence_is_retained():
    result = build_opportunity_evidence_clusters(
        [case("1", "ABC", "RELATIVE_VALUE_ANOMALY"),
         case("2", "ABC", "BREAKEVEN_COMPRESSION")],
        red_team={"challenges": [{"case_id": "1", "challenge": "execution concern"}]},
    )
    cluster = result["clusters"][0]
    assert cluster["contradiction_count"] == 1
    assert cluster["contradictory_evidence"]

def test_missing_evidence_is_not_zero_filled():
    c1 = case("1", "ABC", "RELATIVE_VALUE_ANOMALY")
    c2 = case("2", "ABC", "BREAKEVEN_COMPRESSION")
    c2["evidence"] = [{"name": "distance", "value": None, "source": "missing"}]
    cluster = build_opportunity_evidence_clusters([c1, c2])["clusters"][0]
    assert cluster["data_gap_count"] == 1

def test_cluster_is_deterministic():
    cases = [
        case("2", "ABC", "BREAKEVEN_COMPRESSION"),
        case("1", "ABC", "RELATIVE_VALUE_ANOMALY"),
        case("3", "ABC", "LIQUIDITY_CONFIRMED"),
    ]
    a = build_opportunity_evidence_clusters(cases)
    b = build_opportunity_evidence_clusters(list(reversed(cases)))
    assert a["clusters_sha256"] == b["clusters_sha256"]
    assert a["clusters"][0]["cluster_sha256"] == b["clusters"][0]["cluster_sha256"]

def test_expired_non_risk_case_cannot_become_active_cluster():
    cases = [
        case("1", "ABC", "RELATIVE_VALUE_ANOMALY", expired=True),
        case("2", "ABC", "BREAKEVEN_COMPRESSION", expired=True),
        case("3", "ABC", "LIQUIDITY_CONFIRMED", expired=True),
    ]
    result = build_opportunity_evidence_clusters(cases)
    assert result["clusters"] == []

def test_input_cases_are_not_mutated():
    cases = [
        case("1", "ABC", "RELATIVE_VALUE_ANOMALY"),
        case("2", "ABC", "BREAKEVEN_COMPRESSION"),
    ]
    original = copy.deepcopy(cases)
    build_opportunity_evidence_clusters(cases)
    assert cases == original
