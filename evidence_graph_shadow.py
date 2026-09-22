#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Evidence Graph Shadow for auditable multi-family opportunity intelligence."""

from __future__ import annotations
import hashlib, json
from typing import Any, Iterable

ENGINE_VERSION = "EVIDENCE-GRAPH-SHADOW-1.0"

def _hash(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(raw).hexdigest()

def build_evidence_graph(
    cases: Iterable[dict[str, Any]],
    *,
    historical_patterns: dict[str, Any] | None = None,
    red_team: dict[str, Any] | None = None,
    tsetmc_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build an evidence-only graph; never modifies scores or case statuses."""
    cases = list(cases)
    patterns = historical_patterns or {}
    red = red_team or {}
    pattern_map: dict[str, list[dict[str, Any]]] = {}
    for item in patterns.get("patterns", []):
        pattern_map.setdefault(str(item.get("identity")), []).append(item)
    red_map = {str(x.get("case_id")): x for x in red.get("cases", [])}

    nodes = []
    edges = []
    for case in cases:
        cid = case.get("case_id")
        if not cid:
            continue
        symbol = str(case.get("symbol") or "")
        node = {
            "id": f"case:{cid}",
            "kind": "CASE",
            "case_id": cid,
            "symbol": symbol,
            "type": case.get("type"),
            "status": case.get("status"),
        }
        nodes.append(node)

        for ev in case.get("evidence", []):
            eid = f"evidence:{cid}:{ev.get('name')}"
            nodes.append({
                "id": eid, "kind": "EVIDENCE",
                "name": ev.get("name"), "value": ev.get("value"),
                "source": ev.get("source"),
            })
            edges.append({"from": node["id"], "to": eid, "relation": "SUPPORTED_BY"})

        for pattern in pattern_map.get(symbol, []):
            pid = f"pattern:{symbol}:{pattern.get('type')}:{pattern.get('snapshot_id')}"
            nodes.append({
                "id": pid, "kind": "HISTORICAL_PATTERN",
                "identity": symbol, "type": pattern.get("type"),
                "classification": pattern.get("classification"),
            })
            edges.append({"from": node["id"], "to": pid, "relation": "HISTORICAL_CONTEXT"})

        challenge = red_map.get(str(cid))
        if challenge:
            rid = f"redteam:{cid}"
            nodes.append({"id": rid, "kind": "RED_TEAM", "challenges": challenge.get("challenges", [])})
            edges.append({"from": node["id"], "to": rid, "relation": "CHALLENGED_BY"})

    meta = {
        "engine_version": ENGINE_VERSION,
        "case_count": sum(1 for c in cases if c.get("case_id")),
        "tsetmc_evidence_status": (tsetmc_evidence or {}).get("status", "NOT_ATTACHED"),
    }
    graph = {"metadata": meta, "nodes": nodes, "edges": edges}
    graph["graph_sha256"] = _hash(graph)
    return graph
