#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Evidence-only historical Red Team and conflict fusion for Equity opportunities."""
from __future__ import annotations
import hashlib, json
from typing import Any
from equity_opportunity_lifecycle_shadow import opportunity_key

ENGINE_VERSION = "EQUITY-HISTORICAL-REDTEAM-SHADOW-1.0"

def _hash(v: Any) -> str:
    return hashlib.sha256(json.dumps(v, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":"), default=str).encode()).hexdigest()

def _events(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if isinstance(value, dict):
        return list(value.get("events", []) or [])
    return list(value or [])

def fuse_historical_redteam(opportunities: Any, lifecycle_events: Any = None) -> dict[str, Any]:
    rows = list((opportunities or {}).get("opportunities", []) if isinstance(opportunities, dict) else opportunities or [])
    events = _events(lifecycle_events)
    by_key: dict[str, list[dict[str, Any]]] = {}
    for event in events:
        key = str(event.get("opportunity_key") or "")
        if key:
            by_key.setdefault(key, []).append(event)

    out = []
    for opportunity in rows:
        item = dict(opportunity)
        key = opportunity_key(item)
        history = by_key.get(key, [])
        prior = [e for e in history if str(e.get("snapshot_id") or "") != str(item.get("snapshot_id") or "")]
        historical_support = any(e.get("state") != "RESOLVED" for e in prior)
        historical_red = [e for e in prior if e.get("red_team_challenges")]
        current_red = list(item.get("red_team_challenges") or [])

        if historical_support and historical_red:
            state = "HISTORICAL_MIXED_EVIDENCE"
        elif historical_red:
            state = "HISTORICAL_CONTRADICTION_PRESENT"
        elif historical_support:
            state = "HISTORICAL_SUPPORT_PRESENT"
        elif prior:
            state = "HISTORICAL_DATA_GAP"
        else:
            state = "HISTORICAL_NO_MATCH"

        evidence = {
            "state": state,
            "historical_event_count": len(prior),
            "historical_support_event_count": sum(e.get("state") != "RESOLVED" for e in prior),
            "historical_red_team_event_count": len(historical_red),
            "current_red_team_challenge_count": len(current_red),
            "historical_red_team_challenges": [
                {
                    "snapshot_id": e.get("snapshot_id"),
                    "state": e.get("state"),
                    "challenges": e.get("red_team_challenges") or [],
                }
                for e in historical_red
            ],
            "descriptive_only": True,
            "direction_inference": "DISABLED",
            "score_change": "NONE",
            "causal_inference": False,
            "engine_version": ENGINE_VERSION,
        }
        item["historical_redteam_fusion"] = evidence
        out.append(item)

    return {
        "status": "SUCCESS",
        "engine_version": ENGINE_VERSION,
        "opportunity_count": len(out),
        "opportunities": out,
        "rules": {
            "source": "equity_lifecycle_and_current_red_team_evidence",
            "historical_support_requires_non_resolved_event": True,
            "contradiction_requires_explicit_red_team_evidence": True,
            "direction_inference": "DISABLED",
            "score_change": "NONE",
            "causal_inference": False,
            "missing_data_policy": "NO_ZERO_FILL",
        },
        "fusion_sha256": _hash(out),
    }
