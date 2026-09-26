from __future__ import annotations

import json
from pathlib import Path


def archive_universe_snapshot(snapshot: dict, root: Path) -> Path | None:
    """Persist a unique TSETMC universe snapshot for future replay/calibration."""
    sha = str(snapshot.get("snapshot_sha256") or "").strip()
    rows = snapshot.get("universe_rows") or []
    if not sha or not rows:
        return None

    evidence = snapshot.get("evidence") or {}
    market_watch = evidence.get("market_watch") or {}
    payload = {
        "archive_version": "TSETMC-HISTORY-1.1",
        "source_of_truth": "TSETMC",
        "snapshot_sha256": sha,
        "generated_at": snapshot.get("generated_at"),
        "observation_retrieved_at": market_watch.get("retrieved_at"),
        "market_watch_endpoint": market_watch.get("endpoint"),
        "market_watch_snapshot_sha256": market_watch.get("snapshot_sha256"),
        "data_mode": snapshot.get("data_mode"),
        "live_refresh_status": snapshot.get("live_refresh_status"),
        "market_state": snapshot.get("market_state") or {},
        "row_count": len(rows),
        "rows": rows,
    }
    path = root / "output" / "history" / "tsetmc" / f"{sha}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        text = json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False)
        path.write_text(text, encoding="utf-8")
    return path
