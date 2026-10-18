import json
import hashlib
from pathlib import Path
from datetime import datetime
from collections import Counter

ROOT = Path.cwd()
OUT = ROOT / "output"
HISTORY = OUT / "base_share" / "daily_history"
VERSIONS = OUT / "base_share" / "history_versions"
COMPARISONS = OUT / "base_share" / "comparisons"
LATEST = OUT / "base_share" / "latest_whole_market_opportunity_report.json"
TREND = OUT / "base_share" / "latest_plain_symbol_trend_report.json"

def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

def date_key(obj):
    if not isinstance(obj, dict):
        return None, None
    g = obj.get("latest_history_date")
    j = obj.get("latest_history_date_jalali")
    if g:
        g = str(g).strip()
    if j:
        j = str(j).strip()
    return g, j

def ordinary_rows(obj):
    if not isinstance(obj, dict) or not isinstance(obj.get("rows"), list):
        return []
    result = []
    seen = set()
    for row in obj["rows"]:
        if not isinstance(row, dict):
            continue
        iid = str(row.get("instrument_id") or "").strip()
        symbol = str(row.get("symbol") or "").strip()
        score = row.get("final_score")
        if not iid or not symbol or iid in seen:
            continue
        cls = str(row.get("instrument_classification") or "").upper()
        if cls and not any(x in cls for x in ("ORDINARY", "PLAIN", "COMMON")):
            continue
        if score is None:
            continue
        try:
            score = float(score)
        except (TypeError, ValueError):
            continue
        seen.add(iid)
        result.append({
            "instrument_id": iid,
            "symbol": symbol,
            "name": row.get("name"),
            "final_score": score,
            "engine_version": row.get("engine_version"),
            "classification": row.get("classification"),
            "evidence_coverage_pct": row.get("evidence_coverage_pct"),
            "trend_state": row.get("trend_state"),
            "correction_state": row.get("correction_state"),
        })
    result.sort(key=lambda x: (-x["final_score"], x["instrument_id"]))
    for i, row in enumerate(result, 1):
        row["rank"] = i
    return result

def make_snapshot(source, obj):
    g, j = date_key(obj)
    rows = ordinary_rows(obj)
    if not rows:
        return None, "NO_VALID_ORDINARY_ROWS"
    if not g and not j:
        return None, "NO_MARKET_DATE"
    identity = j or g
    engine_counts = Counter(str(r.get("engine_version") or "UNKNOWN")
                            for r in rows)
    snapshot = {
        "schema_version": "1.0",
        "snapshot_type": "BASE_SHARE_ORDINARY_HISTORY",
        "market_date": g,
        "market_date_jalali": j,
        "source_file": source.relative_to(ROOT).as_posix(),
        "source_sha256": digest(source),
        "source_generated_at": obj.get("generated_at"),
        "source_of_truth": obj.get("source_of_truth"),
        "row_count": len(rows),
        "engine_versions": dict(engine_counts),
        "rows": rows,
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    snapshot["snapshot_sha256"] = hashlib.sha256(
        json.dumps(snapshot, ensure_ascii=False, sort_keys=True).encode()
    ).hexdigest()
    return (identity, snapshot), None

def main():
    HISTORY.mkdir(parents=True, exist_ok=True)
    VERSIONS.mkdir(parents=True, exist_ok=True)
    COMPARISONS.mkdir(parents=True, exist_ok=True)

    # Prefer the dedicated plain-symbol report; use the whole-market report
    # only if its metadata independently validates as a history report.
    candidates = []
    for p in (TREND, LATEST):
        if p.is_file():
            obj = read_json(p)
            if obj:
                candidates.append((p, obj))

    added = 0
    rejected = []
    for p, obj in candidates:
        built, error = make_snapshot(p, obj)
        if error:
            rejected.append(f"{p.relative_to(ROOT)}: {error}")
            continue
        identity, snapshot = built
        safe = "".join(c for c in str(identity) if c.isalnum() or c in "-_")
        target = VERSIONS / f"{safe}.json"

        # Never overwrite an existing historical snapshot.
        if target.exists():
            old = read_json(target)
            if old and old.get("source_sha256") == snapshot["source_sha256"]:
                continue
            version = hashlib.sha256(
                snapshot["source_sha256"].encode()
            ).hexdigest()[:12]
            target = VERSIONS / f"{safe}__{version}.json"

        if not target.exists():
            target.write_text(
                json.dumps(snapshot, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            check = read_json(target)
            if not check or check.get("snapshot_sha256") != snapshot["snapshot_sha256"]:
                raise RuntimeError(f"Snapshot verification failed: {target}")
            added += 1

    # Compare snapshots only when they represent distinct market dates.
    snapshots = []
    for p in sorted(VERSIONS.glob("*.json")):
        obj = read_json(p)
        if obj and obj.get("snapshot_type") == "BASE_SHARE_ORDINARY_HISTORY":
            snapshots.append((p, obj))

    by_date = {}
    for p, obj in snapshots:
        key = obj.get("market_date_jalali") or obj.get("market_date")
        if key:
            by_date.setdefault(str(key), (p, obj))

    ordered = sorted(by_date.items(), key=lambda kv: kv[0])
    comparison_written = None
    if len(ordered) >= 2:
        (prev_date, (prev_path, prev)), (curr_date, (curr_path, curr)) = ordered[-2:]
        old = {r["instrument_id"]: r for r in prev.get("rows", [])}
        new = {r["instrument_id"]: r for r in curr.get("rows", [])}
        common = old.keys() & new.keys()
        changes = []
        for iid in common:
            a, b = old[iid], new[iid]
            changes.append({
                "instrument_id": iid,
                "symbol_previous": a["symbol"],
                "symbol_current": b["symbol"],
                "score_previous": a["final_score"],
                "score_current": b["final_score"],
                "score_delta": round(b["final_score"] - a["final_score"], 4),
                "rank_previous": a["rank"],
                "rank_current": b["rank"],
                "rank_delta": a["rank"] - b["rank"],
                "engine_previous": a.get("engine_version"),
                "engine_current": b.get("engine_version"),
                "engine_changed": a.get("engine_version") != b.get("engine_version"),
            })
        changes.sort(key=lambda r: (-abs(r["score_delta"]), r["instrument_id"]))
        comparison = {
            "schema_version": "1.0",
            "previous_market_date": prev_date,
            "current_market_date": curr_date,
            "previous_snapshot": prev_path.relative_to(ROOT).as_posix(),
            "current_snapshot": curr_path.relative_to(ROOT).as_posix(),
            "previous_snapshot_sha256": prev.get("snapshot_sha256"),
            "current_snapshot_sha256": curr.get("snapshot_sha256"),
            "common_instruments": len(common),
            "only_previous": sorted(old.keys() - new.keys()),
            "only_current": sorted(new.keys() - old.keys()),
            "engine_changed_count": sum(r["engine_changed"] for r in changes),
            "changes": changes,
            "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        }
        comparison["comparison_sha256"] = hashlib.sha256(
            json.dumps(comparison, ensure_ascii=False, sort_keys=True).encode()
        ).hexdigest()
        # تاریخ‌ها ممکن است شمسی و دارای / باشند؛ نام فایل باید امن باشد.
        safe_prev = "".join(c if c.isalnum() or c in "-_" else "-" for c in str(prev_date))
        safe_curr = "".join(c if c.isalnum() or c in "-_" else "-" for c in str(curr_date))
        out = COMPARISONS / f"compare_{safe_prev}_vs_{safe_curr}.json"
        COMPARISONS.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(comparison, ensure_ascii=False, indent=2),
                       encoding="utf-8")
        comparison_written = out.relative_to(ROOT).as_posix()

    print("HISTORY_MANAGER_FINISHED")
    print("NEW_SNAPSHOTS:", added)
    print("TOTAL_SNAPSHOTS:", len(list(VERSIONS.glob("*.json"))))
    print("DISTINCT_MARKET_DATES:", len(by_date))
    print("COMPARISON:", comparison_written or "NOT_CREATED_NEED_TWO_DISTINCT_DATES")
    print("REJECTED_REPORTS:", len(rejected))
    for item in rejected:
        print("REJECTED:", item)

if __name__ == "__main__":
    main()
