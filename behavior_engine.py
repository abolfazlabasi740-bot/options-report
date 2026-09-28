from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

ENGINE_VERSION = "TSETMC-BEHAVIOR-1.0"
SOURCE_OF_TRUTH = "TSETMC"

FIELDS = {
    "last": "آخرین قیمت",
    "close": "قیمت پایانی",
    "volume": "حجم معاملات",
    "value": "ارزش معاملات",
    "oi": "موقعیت های باز",
}


def _num(v: Any) -> float | None:
    try:
        if v in (None, ""):
            return None
        x = float(v)
        return x if x == x and abs(x) != float("inf") else None
    except (TypeError, ValueError):
        return None


def _time(s: Any) -> datetime | None:
    if not isinstance(s, str) or not s.strip():
        return None
    try:
        return datetime.fromisoformat(s.strip().replace("Z", "+00:00"))
    except ValueError:
        return None


def _snapshots(root: Path) -> list[dict[str, Any]]:
    out = []
    for p in (root / "output" / "history" / "tsetmc").glob("*.json"):
        try:
            x = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            continue
        if x.get("source_of_truth") == SOURCE_OF_TRUTH and isinstance(x.get("rows"), list):
            out.append(x)
    out.sort(key=lambda x: _time(x.get("observation_retrieved_at")).timestamp() if _time(x.get("observation_retrieved_at")) else float("-inf"))
    return out


def _row(r: dict[str, Any]) -> dict[str, Any]:
    c = r.get("canonical") or {}
    i = r.get("identity") or {}
    return {
        "instrument_id": str(i.get("instrument_id") or ""),
        "symbol": c.get("نماد"),
        "underlying_symbol": i.get("underlying_symbol"),
        "underlying_id": i.get("underlying_id"),
        "contract_type": i.get("contract_type"),
        "last": _num(c.get(FIELDS["last"])),
        "close": _num(c.get(FIELDS["close"])),
        "volume": _num(c.get(FIELDS["volume"])),
        "value": _num(c.get(FIELDS["value"])),
        "oi": _num(c.get(FIELDS["oi"])),
        "underlying_price": _num(c.get("قیمت سهم پایه")),
    }


def _pct(a: float | None, b: float | None) -> float | None:
    if a is None or b is None or a == 0:
        return None
    return (b - a) / abs(a)


def _direction(x: float | None) -> str:
    if x is None:
        return "داده موجود نیست"
    if x > 0:
        return "افزایش"
    if x < 0:
        return "کاهش"
    return "بدون تغییر"


def build_behavior_report(root: Path, limit: int = 15) -> dict[str, Any]:
    snaps = _snapshots(root)
    if len(snaps) < 2:
        return {
            "status": "INSUFFICIENT_HISTORY",
            "engine_version": ENGINE_VERSION,
            "source_of_truth": SOURCE_OF_TRUTH,
            "snapshot_count": len(snaps),
            "transition_count": 0,
            "events": [],
            "message": "برای تشخیص تغییر رفتار حداقل دو Snapshot معتبر TSETMC لازم است.",
        }

    prev, cur = snaps[-2], snaps[-1]
    previous = {x["instrument_id"]: x for x in map(_row, prev.get("rows", [])) if x["instrument_id"]}
    current = {x["instrument_id"]: x for x in map(_row, cur.get("rows", [])) if x["instrument_id"]}

    events = []
    for iid in sorted(set(previous) & set(current)):
        a, b = previous[iid], current[iid]
        dp, dv, dval, doi, du = (
            _pct(a["last"], b["last"]),
            _pct(a["volume"], b["volume"]),
            _pct(a["value"], b["value"]),
            _pct(a["oi"], b["oi"]),
            _pct(a["underlying_price"], b["underlying_price"]),
        )
        flags = []
        if dp is not None and dv is not None:
            if dp > 0 and dv > 0:
                flags.append("PRICE_UP_VOLUME_UP")
            elif dp < 0 and dv > 0:
                flags.append("PRICE_DOWN_VOLUME_UP")
        if dp is not None and doi is not None:
            if dp > 0 and doi > 0:
                flags.append("PRICE_UP_OI_UP")
            elif dp < 0 and doi > 0:
                flags.append("PRICE_DOWN_OI_UP")
            elif dp > 0 and doi < 0:
                flags.append("PRICE_UP_OI_DOWN")
            elif dp < 0 and doi < 0:
                flags.append("PRICE_DOWN_OI_DOWN")
        if dp is not None and du is not None:
            if dp > 0 and du < 0:
                flags.append("OPTION_UP_UNDERLYING_DOWN")
            elif dp < 0 and du > 0:
                flags.append("OPTION_DOWN_UNDERLYING_UP")
            elif dp > 0 and du > 0:
                flags.append("OPTION_UP_UNDERLYING_UP")
            elif dp < 0 and du < 0:
                flags.append("OPTION_DOWN_UNDERLYING_DOWN")

        if not flags:
            continue

        activity = max(
            [abs(x) for x in (dv, dval, doi) if x is not None] or [0.0]
        )
        events.append({
            "instrument_id": iid,
            "symbol": b["symbol"],
            "underlying_symbol": b["underlying_symbol"],
            "contract_type": b["contract_type"],
            "previous_last": a["last"],
            "current_last": b["last"],
            "last_change_pct": dp,
            "volume_change_pct": dv,
            "value_change_pct": dval,
            "oi_change_pct": doi,
            "underlying_change_pct": du,
            "flags": flags,
            "activity_magnitude": activity,
            "observation_from": prev.get("observation_retrieved_at"),
            "observation_to": cur.get("observation_retrieved_at"),
        })

    events.sort(key=lambda x: (len(x["flags"]), x["activity_magnitude"]), reverse=True)
    events = events[:max(1, int(limit))]

    return {
        "status": "PASS",
        "engine_version": ENGINE_VERSION,
        "source_of_truth": SOURCE_OF_TRUTH,
        "snapshot_count": len(snaps),
        "transition_count": len(set(previous) & set(current)),
        "previous_snapshot_sha256": prev.get("snapshot_sha256"),
        "current_snapshot_sha256": cur.get("snapshot_sha256"),
        "events": events,
        "rules": {
            "identity": "EXACT_INSTRUMENT_ID_ONLY",
            "no_prediction": True,
            "no_signal_generation": True,
            "missing_values": "NOT_INFERRED",
        },
    }


def format_behavior_report(result: dict[str, Any]) -> str:
    lines = [
        "🧠 تغییر رفتار بازار — TSETMC",
        "━━━━━━━━━━━━━━━━━━━━",
        f"وضعیت: {result.get('status')}",
        f"Snapshotها: {result.get('snapshot_count', 0)}",
        f"انتقال قابل مقایسه: {result.get('transition_count', 0)}",
    ]
    if result.get("status") != "PASS":
        lines.append(result.get("message", "داده کافی موجود نیست."))
        return "\n".join(lines)

    lines += [
        f"از: {result.get('previous_snapshot_sha256')}",
        f"به: {result.get('current_snapshot_sha256')}",
        "⚠️ این گزارش تغییر رفتار مشاهده‌شده را نشان می‌دهد و پیش‌بینی یا سیگنال خرید/فروش نیست.",
        "━━━━━━━━━━━━━━━━━━━━",
    ]
    for n, e in enumerate(result.get("events", []), 1):
        def pct(v):
            return "داده موجود نیست" if v is None else f"{v * 100:+.1f}%"
        lines += [
            f"{n}. {e.get('symbol') or 'داده موجود نیست'} | پایه: {e.get('underlying_symbol') or 'داده موجود نیست'}",
            f"قیمت: {pct(e.get('last_change_pct'))} | حجم: {pct(e.get('volume_change_pct'))} | ارزش: {pct(e.get('value_change_pct'))} | OI: {pct(e.get('oi_change_pct'))}",
            f"سهم پایه: {pct(e.get('underlying_change_pct'))}",
            "الگو: " + " + ".join(e.get("flags") or []),
            "━━━━━━━━━━━━━━━━━━━━",
        ]
    if not result.get("events"):
        lines.append("در این دو Snapshot، تغییر رفتاری قابل طبقه‌بندی مشاهده نشد.")
    return "\n".join(lines)
