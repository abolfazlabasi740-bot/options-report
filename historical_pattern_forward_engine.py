from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from behavior_engine import _pct, _row, _snapshots, analyze_snapshot_pair

ENGINE_VERSION = "TSETMC-HISTORICAL-PATTERN-FORWARD-1.0"
SOURCE_OF_TRUTH = "TSETMC"


def _signature(event: dict[str, Any]) -> str:
    return " + ".join(event.get("flags") or [])


def _rows_by_id(snapshot: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        x["instrument_id"]: x
        for x in map(_row, snapshot.get("rows", []))
        if x["instrument_id"]
    }


def _outcome(previous: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    return {
        "last_change_pct": _pct(previous.get("last"), current.get("last")),
        "volume_change_pct": _pct(previous.get("volume"), current.get("volume")),
        "value_change_pct": _pct(previous.get("value"), current.get("value")),
        "oi_change_pct": _pct(previous.get("oi"), current.get("oi")),
        "underlying_change_pct": _pct(
            previous.get("underlying_price"), current.get("underlying_price")
        ),
    }


def build_historical_pattern_forward_report(
    root: Path,
    limit_patterns: int | None = None,
) -> dict[str, Any]:
    snapshots = _snapshots(root)
    if len(snapshots) < 3:
        return {
            "status": "INSUFFICIENT_HISTORY",
            "engine_version": ENGINE_VERSION,
            "source_of_truth": SOURCE_OF_TRUTH,
            "snapshot_count": len(snapshots),
            "transition_count": max(0, len(snapshots) - 1),
            "forward_valid_transition_count": max(0, len(snapshots) - 2),
            "patterns": [],
        }

    observed = Counter()
    occurrences: dict[str, list[dict[str, Any]]] = defaultdict(list)

    # The final transition has no following snapshot, so it is observed
    # behavior but cannot be used for forward-outcome validation.
    for i in range(1, len(snapshots) - 1):
        pair = analyze_snapshot_pair(snapshots[i - 1], snapshots[i])
        current_rows = _rows_by_id(snapshots[i])
        next_rows = _rows_by_id(snapshots[i + 1])

        for event in pair["events"]:
            sig = _signature(event)
            observed[sig] += 1
            iid = event["instrument_id"]
            if iid not in current_rows or iid not in next_rows:
                continue

            out = _outcome(current_rows[iid], next_rows[iid])
            occurrences[sig].append({
                "instrument_id": iid,
                "symbol": event.get("symbol"),
                "underlying_symbol": event.get("underlying_symbol"),
                "pattern_observation_from": event.get("observation_from"),
                "pattern_observation_to": event.get("observation_to"),
                "forward_observation_to": snapshots[i + 1].get(
                    "observation_retrieved_at"
                ),
                **out,
            })

    patterns = []
    for sig, count in observed.most_common():
        rows = occurrences.get(sig, [])
        last_changes = [
            x["last_change_pct"] for x in rows if x["last_change_pct"] is not None
        ]
        underlying_changes = [
            x["underlying_change_pct"]
            for x in rows
            if x["underlying_change_pct"] is not None
        ]
        up = sum(1 for x in last_changes if x > 0)
        down = sum(1 for x in last_changes if x < 0)
        flat = sum(1 for x in last_changes if x == 0)

        patterns.append({
            "signature": sig,
            "observed_occurrences": count,
            "forward_valid_occurrences": len(rows),
            "instrument_count": len({x["instrument_id"] for x in rows}),
            "forward_last_up_count": up,
            "forward_last_down_count": down,
            "forward_last_flat_count": flat,
            "forward_last_up_rate": (up / len(last_changes)) if last_changes else None,
            "forward_last_down_rate": (down / len(last_changes)) if last_changes else None,
            "forward_last_avg_change_pct": (
                sum(last_changes) / len(last_changes) if last_changes else None
            ),
            "forward_underlying_avg_change_pct": (
                sum(underlying_changes) / len(underlying_changes)
                if underlying_changes
                else None
            ),
            "outcomes": rows,
        })

    if limit_patterns is not None:
        patterns = patterns[: max(1, int(limit_patterns))]

    return {
        "status": "PASS",
        "engine_version": ENGINE_VERSION,
        "source_of_truth": SOURCE_OF_TRUTH,
        "snapshot_count": len(snapshots),
        "transition_count": len(snapshots) - 1,
        "forward_valid_transition_count": len(snapshots) - 2,
        "patterns": patterns,
        "rules": {
            "identity": "EXACT_INSTRUMENT_ID_ONLY",
            "pattern_signature": "EXACT_FLAGS_JOINED",
            "forward_horizon": "NEXT_SNAPSHOT_ONLY",
            "final_transition": "OBSERVED_BUT_NOT_FORWARD_VALIDATED",
            "missing_values": "NOT_INFERRED",
            "prediction": False,
            "signal_generation": False,
            "scoring": False,
            "ranking": False,
        },
    }


def format_historical_pattern_forward_report(result: dict[str, Any]) -> str:
    lines = [
        "Historical Pattern -> Forward Outcome — TSETMC",
        "━━━━━━━━━━━━━━━━━━━━",
        f"STATUS={result.get('status')}",
        f"SNAPSHOTS={result.get('snapshot_count', 0)}",
        f"TRANSITIONS={result.get('transition_count', 0)}",
        f"FORWARD_VALID_TRANSITIONS={result.get('forward_valid_transition_count', 0)}",
    ]
    if result.get("status") != "PASS":
        return "\n".join(lines)

    lines.append("━━━━━━━━━━━━━━━━━━━━")
    for n, p in enumerate(result.get("patterns", []), 1):
        def fmt(v):
            return "NA" if v is None else f"{v * 100:+.1f}%"

        lines += [
            f"{n}. {p['signature']}",
            f"OBSERVED={p['observed_occurrences']} | FORWARD_VALID={p['forward_valid_occurrences']} | INSTRUMENTS={p['instrument_count']}",
            f"NEXT_OPTION_UP={p['forward_last_up_count']} ({fmt(p.get('forward_last_up_rate'))}) | NEXT_OPTION_DOWN={p['forward_last_down_count']} ({fmt(p.get('forward_last_down_rate'))})",
            f"NEXT_OPTION_AVG={fmt(p.get('forward_last_avg_change_pct'))} | NEXT_UNDERLYING_AVG={fmt(p.get('forward_underlying_avg_change_pct'))}",
            "━━━━━━━━━━━━━━━━━━━━",
        ]
    lines.append(
        "این خروجی توصیفی/اعتبارسنجی تاریخی است؛ پیش‌بینی، سیگنال، Scoring و Ranking تولید نمی‌کند."
    )
    return "\n".join(lines)
