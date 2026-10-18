import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = ROOT / "output" / "base_share"
SEED = BASE / "comparison_v22"
HISTORY = BASE / "trend_history"
LATEST = BASE / "latest_whole_market_opportunity_report.json"

INITIAL = [
    ("20261007", "1405/07/15", SEED / "base_share_14050715_v22.json"),
    ("20261010", "1405/07/18", SEED / "base_share_14050718_v22.json"),
]


def _read(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return None


def _sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _is_candidate_symbol(symbol):
    # Initial heuristic only; not verified instrument classification.
    return bool(symbol) and not re.search(r"[0-9۰-۹٠-٩]$", symbol.strip())


def _rank_rows(rows):
    valid = []
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        iid = str(row.get("instrument_id") or "").strip()
        symbol = str(row.get("symbol") or "").strip()
        try:
            score = float(row.get("final_score"))
        except (TypeError, ValueError):
            continue
        if not iid or not symbol or iid in seen:
            continue
        if not _is_candidate_symbol(symbol):
            continue
        seen.add(iid)
        valid.append({
            "instrument_id": iid,
            "symbol": symbol,
            "name": row.get("name"),
            "final_score": round(score, 4),
            "engine_version": row.get("engine_version") or row.get("score_engine"),
            "trend_state": row.get("trend_state"),
            "correction_state": row.get("correction_state"),
            "evidence_coverage_pct": row.get("evidence_coverage_pct"),
            "classification_policy": "SYMBOL_SUFFIX_HEURISTIC_ONLY",
        })
    valid.sort(key=lambda r: (-r["final_score"], r["instrument_id"]))
    for rank, row in enumerate(valid, 1):
        row["rank"] = rank
    return valid


def _write_snapshot(date_gregorian, date_jalali, source_path, source_obj, rows):
    HISTORY.mkdir(parents=True, exist_ok=True)
    target = HISTORY / (str(date_gregorian) + ".json")
    if target.exists():
        return False

    snapshot = {
        "schema_version": "1.0",
        "snapshot_type": "BASE_SHARE_TREND_HISTORY",
        "market_date": str(date_gregorian),
        "market_date_jalali": str(date_jalali or ""),
        "source_file": str(source_path.relative_to(ROOT)),
        "source_sha256": _sha(source_path),
        "source_generated_at": source_obj.get("generated_at"),
        "source_of_truth": source_obj.get("source_of_truth", "TSETMC"),
        "score_engine": source_obj.get("score_engine") or source_obj.get("engine_version"),
        "row_count": len(rows),
        "classification_policy": "SYMBOL_SUFFIX_HEURISTIC_ONLY; NOT VERIFIED",
        "missing_data_policy": "NO IMPUTATION",
        "buy_sell_signal": False,
        "rows": rows,
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    canonical = json.dumps(snapshot, ensure_ascii=False, sort_keys=True)
    snapshot["snapshot_sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    tmp = target.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    check = _read(tmp)
    if not check or check.get("snapshot_sha256") != snapshot["snapshot_sha256"]:
        tmp.unlink(missing_ok=True)
        raise RuntimeError("TREND_SNAPSHOT_VERIFY_FAILED")
    tmp.replace(target)
    return True


def _seed_initial_history():
    added = 0
    for gregorian, jalali, source in INITIAL:
        obj = _read(source)
        if not obj:
            continue
        rows = _rank_rows(obj.get("rows", []))
        if rows:
            added += int(_write_snapshot(gregorian, jalali, source, obj, rows))
    return added


def _ingest_latest_report():
    obj = _read(LATEST)
    if not obj:
        return "LATEST_REPORT_UNAVAILABLE"

    date_g = str(obj.get("latest_history_date") or obj.get("market_date") or "").strip()
    date_j = str(obj.get("latest_history_date_jalali") or obj.get("period_label") or "").strip()
    if not date_g.isdigit() or len(date_g) != 8:
        return "LATEST_REPORT_DATE_INVALID"

    HISTORY.mkdir(parents=True, exist_ok=True)
    existing_dates = [
        p.stem for p in HISTORY.glob("*.json")
        if p.stem.isdigit() and len(p.stem) == 8
    ]
    latest_archived = max(existing_dates) if existing_dates else ""
    if date_g <= latest_archived:
        return "NO_NEWER_MARKET_DATE"

    rows = _rank_rows(obj.get("rows", []))
    if not rows:
        return "LATEST_REPORT_HAS_NO_VALID_ROWS"

    if _write_snapshot(date_g, date_j, LATEST, obj, rows):
        return "NEW_SNAPSHOT:" + date_g
    return "SNAPSHOT_ALREADY_EXISTS"


def _snapshots():
    result = []
    for path in HISTORY.glob("*.json"):
        if not path.stem.isdigit() or len(path.stem) != 8:
            continue
        obj = _read(path)
        if obj and obj.get("snapshot_type") == "BASE_SHARE_TREND_HISTORY":
            result.append((path, obj))
    return sorted(result, key=lambda item: item[0].stem)


def _compare(previous, current):
    old = {str(r["instrument_id"]): r for r in previous.get("rows", [])}
    new = {str(r["instrument_id"]): r for r in current.get("rows", [])}
    changes = []
    for iid in old.keys() & new.keys():
        a, b = old[iid], new[iid]
        delta = round(float(b["final_score"]) - float(a["final_score"]), 4)
        changes.append({
            "instrument_id": iid,
            "symbol": b.get("symbol") or a.get("symbol"),
            "score_previous": a["final_score"],
            "score_current": b["final_score"],
            "score_delta": delta,
            "rank_previous": a.get("rank"),
            "rank_current": b.get("rank"),
            "rank_change": (a.get("rank", 0) - b.get("rank", 0)),
            "engine_previous": a.get("engine_version"),
            "engine_current": b.get("engine_version"),
        })
    changes.sort(key=lambda r: (-abs(r["score_delta"]), r["symbol"]))
    return old, new, changes


def build_trend_review_report():
    seeded = _seed_initial_history()
    ingestion = _ingest_latest_report()
    snapshots = _snapshots()

    lines = [
        "📈 بررسی روند سهام پایه",
        "━━━━━━━━━━━━━━━━━━━━",
        "آرشیو اولیه: ۱۵ و ۱۸ مهر ۱۴۰۵",
        f"ثبت snapshot اولیه جدید در این اجرا: {seeded}",
        f"وضعیت داده روزانه: {ingestion}",
        f"تعداد تاریخ‌های آرشیوشده: {len(snapshots)}",
        "روش تشخیص سهم عادی: تقریبی و مبتنی بر پسوند نماد",
        "سیگنال خرید/فروش: تولید نمی‌شود",
        "━━━━━━━━━━━━━━━━━━━━",
    ]

    if not snapshots:
        lines.append("گزارش تاریخچه در دسترس نیست؛ فایل‌های منبع را بررسی کنید.")
        return "\n".join(lines)

    current_path, current = snapshots[-1]
    lines.extend([
        f"آخرین تاریخ بازار: {current.get('market_date_jalali') or current.get('market_date')}",
        f"تعداد نمادهای ثبت‌شده: {current.get('row_count', 0)}",
        f"موتور امتیازدهی: {current.get('score_engine') or 'نامشخص'}",
        f"SHA-256 snapshot: {str(current.get('snapshot_sha256') or '')[:20]}...",
    ])

    if len(snapshots) >= 2:
        previous_path, previous = snapshots[-2]
        old, new, changes = _compare(previous, current)
        lines.extend([
            "",
            f"مقایسه با تاریخ قبل: {previous.get('market_date_jalali') or previous.get('market_date')}",
            f"نمادهای مشترک: {len(old.keys() & new.keys())}",
            f"فقط در تاریخ قبل: {len(old.keys() - new.keys())}",
            f"فقط در تاریخ فعلی: {len(new.keys() - old.keys())}",
            "",
            "🔺 بیشترین افزایش امتیاز:",
        ])
        increases = sorted((r for r in changes if r["score_delta"] > 0),
                           key=lambda r: -r["score_delta"])[:7]
        if increases:
            for r in increases:
                lines.append(
                    f"• {r['symbol']}: {r['score_previous']:.2f} → "
                    f"{r['score_current']:.2f} ({r['score_delta']:+.2f}) | "
                    f"رتبه {r['rank_previous']} → {r['rank_current']}"
                )
        else:
            lines.append("• افزایش امتیاز ثبت نشده")

        lines.extend(["", "🔻 بیشترین کاهش امتیاز:"])
        decreases = sorted((r for r in changes if r["score_delta"] < 0),
                           key=lambda r: r["score_delta"])[:7]
        if decreases:
            for r in decreases:
                lines.append(
                    f"• {r['symbol']}: {r['score_previous']:.2f} → "
                    f"{r['score_current']:.2f} ({r['score_delta']:+.2f}) | "
                    f"رتبه {r['rank_previous']} → {r['rank_current']}"
                )
        else:
            lines.append("• کاهش امتیاز ثبت نشده")

        engine_changes = sum(
            r["engine_previous"] != r["engine_current"] for r in changes
        )
        lines.extend([
            "",
            f"تغییر موتور در نمادهای مشترک: {engine_changes}",
            f"فایل مقایسه: {previous_path.name} ↔ {current_path.name}",
        ])
    else:
        lines.extend(["", "برای مقایسه تغییرات، حداقل دو تاریخ لازم است."])

    lines.extend([
        "",
        "محدودیت‌ها:",
        "• طبقه‌بندی نمادها بر اساس پسوند، قطعی و تأییدشده نیست.",
        "• مقایسه، امتیازهای ذخیره‌شده هر snapshot را استفاده می‌کند؛ داده قدیمی بازسازی زنده نشده است.",
        "• داده جدید فقط پس از تولید گزارش روزانه توسط سامانه اصلی وارد آرشیو می‌شود.",
        "• تغییر موتور یا کیفیت داده می‌تواند مقایسه امتیازها را تحت تأثیر قرار دهد.",
        "• این گزارش توصیه خرید یا فروش نیست.",
    ])
    return "\n".join(lines)


if __name__ == "__main__":
    print(build_trend_review_report())
