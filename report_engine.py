#!/usr/bin/env python3
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import os
import argparse
import hashlib
import json
import pandas as pd
import requests
from scoring_engine import ENGINE_VERSION, MIN_LEVERAGE, normalize_text, normalize_columns, numeric_columns
from opportunity_engine import run_shadow
from eligibility_shadow import classify_dataframe, opportunity_universe
from schema_audit import audit_schema
from replay_engine import verify_shadow_replay
from audit_integrity import verify_audit
from historical_snapshot import (
    append_snapshot,
    build_snapshot,
    dataframe_records,
    diff_snapshots,
    load_history,
)

ROOT = Path(__file__).resolve().parent
TEHRAN = ZoneInfo("Asia/Tehran")

OPTIONSCHOOL_URL = "https://s3.optionschool24.com/export/excel?type=1"
TOP_COUNT = int(os.getenv("TOP_COUNT", "15"))


def snapshot_id_for(path, df):
    """Return the source-file SHA when available; otherwise a deterministic test hash."""
    source = Path(path)
    if source.exists() and source.is_file():
        return hashlib.sha256(source.read_bytes()).hexdigest()
    canonical = df.copy()
    canonical = canonical.sort_index(axis=1)
    payload = canonical.to_csv(index=True, lineterminator="\n").encode("utf-8", errors="strict")
    return hashlib.sha256(payload).hexdigest()


def download_optionschool():
    data_dir = ROOT / "data"
    data_dir.mkdir(exist_ok=True)

    stamp = datetime.now(TEHRAN).strftime("%Y%m%d_%H%M%S_%f")
    path = data_dir / f"optionschool_{stamp}.xlsx"

    r = requests.get(OPTIONSCHOOL_URL, timeout=90)
    r.raise_for_status()

    if len(r.content) < 5000 or not r.content.startswith(b"PK"):
        raise RuntimeError("فایل دریافتی Optionschool معتبر نیست")

    path.write_bytes(r.content)
    return path


def find_column(df, names):
    normalized = {
        str(c).strip().replace(" ", "").replace("_", "").replace("‌", "").lower(): c
        for c in df.columns
    }

    for name in names:
        key = str(name).strip().replace(" ", "").replace("_", "").replace("‌", "").lower()
        if key in normalized:
            return normalized[key]

    return None


def build_report(path, top_count=None, symbol_prefix=None):
    limit = TOP_COUNT if top_count is None else top_count
    if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
        raise ValueError("تعداد قراردادها باید عدد صحیح مثبت باشد")
    df = pd.read_excel(path)
    source_schema_audit = audit_schema(df)

    # V4.1 scoring engine: GitHub six-block production candidate
    from scoring_engine import score_dataframe, shadow_score_dataframe
    from tsetmc_shadow_integration import enrich_shadow_with_tsetmc

    # Symbol-scoped reports must define the scoring population before any
    # cross-sectional percentile calculation. Schema validation is performed
    # first; no TSETMC identity is inferred from the symbol text.
    scoring_source = normalize_columns(df.copy())
    symbol_col = find_column(scoring_source, ["نماد", "Symbol"])
    if symbol_prefix:
        if symbol_col is None:
            raise RuntimeError("ستون نماد برای فیلتر تک‌نماد موجود نیست")
        prefix = normalize_text(symbol_prefix)
        symbol_values = scoring_source[symbol_col].astype("string").map(
            lambda value: normalize_text(value) if pd.notna(value) else value
        )
        scoring_source = scoring_source[
            symbol_values.str.startswith(prefix, na=False)
        ].copy()
        if scoring_source.empty:
            raise RuntimeError(
                f"هیچ رکوردی برای نماد «{prefix}» پس از اعتبارسنجی Schema پیدا نشد"
            )

    scored = score_dataframe(scoring_source)

    # Historical snapshot evidence is source-wide and must not depend on the
    # requested report scope. This prevents the same source SHA from producing
    # conflicting history records when both a full-market and symbol-scoped
    # report are generated from the same workbook.
    history_scored = None
    if symbol_prefix:
        history_scored = score_dataframe(normalize_columns(df.copy()))

    # Preserve a source-level eligibility view so expired/missing-leverage rows
    # remain auditable even though production scoring retains its existing gate.
    source_view = numeric_columns(normalize_columns(df.copy()))
    source_view["RemainingDays"] = (source_view["روزهای تقویمی"] - 1).clip(lower=0)
    source_view["FinalScore"] = pd.NA
    source_eligibility = classify_dataframe(source_view, min_leverage=MIN_LEVERAGE)
    opportunity_universe_view = opportunity_universe(source_view, min_leverage=MIN_LEVERAGE)
    shadow_scored = shadow_score_dataframe(source_view)

    # Optional evidence-only TSETMC enrichment. It requires explicit option
    # instrument IDs and never changes production scoring/ranking.
    shadow_scored, tsetmc_evidence = enrich_shadow_with_tsetmc(
        shadow_scored, df
    )

    # Shadow Opportunity Engine scans the full scored universe before symbol/Top-N
    # filtering. It never changes FinalScore, ranking, or report contents.
    snapshot_id = snapshot_id_for(path, df)
    shadow_scored["FinalScore_Production"] = pd.NA

    # Historical evidence store: source-local symbol identity is used until
    # an explicit TSETMC instrument identifier is available in the live path.
    history_file = ROOT / "output" / "historical_snapshots.jsonl"
    history_columns = [
        "نماد",
        "FinalScore",
        "DataConfidence",
        "RemainingDays",
        "BlockScore_Liquidity",
        "BlockScore_Valuation",
        "BlockScore_Payoff",
        "BlockScore_Time",
        "BlockScore_Greeks",
        "BlockScore_Market",
        "ExecutionPenalty",
        "DecayPenalty",
        "Score_BlackScholesDiff",
        "Score_BreakevenDistance",
    ]
    history_records = dataframe_records(
        history_scored if history_scored is not None else scored,
        history_columns,
    )
    current_history = build_snapshot(
        snapshot_id,
        history_records,
        source=Path(path).name,
        retrieved_at=datetime.now(TEHRAN).isoformat(),
        identity_mode="SOURCE_LOCAL_SYMBOL",
        metadata={"source_timestamp_status": "UNVERIFIED"},
    )
    prior_history = load_history(history_file)
    previous_history = prior_history[-1] if prior_history else None
    if previous_history and previous_history.get("snapshot_id") == snapshot_id and len(prior_history) > 1:
        previous_history = prior_history[-2]

    history_result = append_snapshot(history_file, current_history)
    history_sequence = load_history(history_file)
    history_diff = diff_snapshots(
        previous_history,
        current_history,
        identity_key="نماد",
    )

    memory_file = ROOT / "output" / "case_memory_shadow.json"
    lifecycle_file = ROOT / "output" / "case_lifecycle_shadow.jsonl"
    try:
        shadow = run_shadow(
            shadow_scored,
            snapshot_id,
            memory_path=memory_file,
            historical_previous=previous_history,
            historical_current=current_history,
            historical_sequence=history_sequence,
            lifecycle_path=lifecycle_file,
        )
    except Exception as exc:
        # Shadow analytical failure is explicitly non-blocking for Production.
        # Integrity/provenance failures remain blocking at Audit/Replay gates.
        shadow = {
            "status": "FAILED",
            "engine_version": "OPP-SHADOW-1.0",
            "snapshot_id": snapshot_id,
            "summary": {"failure_type": type(exc).__name__},
            "cases": [],
            "failure": {"error_type": type(exc).__name__},
        }

    if shadow.get("status") == "FAILED":
        replay = {
            "status": "SKIPPED_SHADOW_FAILURE",
            "engine_version": "REPLAY-SHADOW-1.1",
            "snapshot_id": snapshot_id,
            "replay_scope": "ANALYTICAL_CASE_ARTIFACT",
            "baseline_hash": None,
            "first_hash": None,
            "second_hash": None,
            "baseline_match": False,
            "deterministic": False,
        }
    else:
        replay = verify_shadow_replay(
            shadow_scored,
            snapshot_id,
            baseline_shadow=shadow,
            historical_previous=previous_history,
            historical_current=current_history,
            historical_sequence=history_sequence,
        )
        if not replay.get("deterministic"):
            raise RuntimeError(
                "Shadow replay mismatch; "
                f"baseline={replay.get('baseline_hash')} "
                f"first={replay.get('first_hash')} "
                f"second={replay.get('second_hash')}"
            )
    symbol = find_column(scored, ["نماد", "Symbol"])
    premium = find_column(scored, ["آخرین قیمت", "آخرین", "Last"])
    base = find_column(scored, ["قیمت سهم پایه", "Underlying"])
    leverage = find_column(scored, ["اهرم", "Leverage"])

    required = {
        "نماد": symbol,
        "آخرین قیمت": premium,
        "قیمت سهم پایه": base,
        "اهرم": leverage,
        "FinalScore": "FinalScore",
        "RemainingDays": "RemainingDays",
    }

    missing = [name for name, col in required.items() if col not in scored.columns]

    if missing:
        raise RuntimeError(
            "ستون‌های ضروری V4.1 موجود نیستند: " + ", ".join(missing)
        )

    work = pd.DataFrame(index=scored.index)
    work["نماد"] = scored[symbol].astype(str).str.strip()
    work["آخرین"] = pd.to_numeric(scored[premium], errors="coerce")
    work["پایه"] = pd.to_numeric(scored[base], errors="coerce")
    work["اهرم"] = pd.to_numeric(scored[leverage], errors="coerce")
    work["FinalScore"] = pd.to_numeric(scored["FinalScore"], errors="coerce")
    work["RemainingDays"] = pd.to_numeric(
        scored["RemainingDays"], errors="coerce"
    )

    # فیلدهای پایه گزارش ۱۱ ستونه
    strike = find_column(scored, ["قیمت اعمال"])
    breakeven = find_column(scored, ["سر به سر"])
    expiry = find_column(scored, ["تاریخ سررسید"])

    work["اعمال"] = (
        pd.to_numeric(scored[strike], errors="coerce")
        if strike else pd.NA
    )
    work["سر به سری"] = (
        pd.to_numeric(scored[breakeven], errors="coerce")
        if breakeven else pd.NA
    )
    work["فاصله سر به سری"] = (
        scored["BreakevenDistancePct"]
    )
    work["سررسید"] = (
        scored[expiry].astype("string").str.strip()
        if expiry else "داده موجود نیست"
    )

    volume = find_column(scored, ["حجم معاملات", "حجم کل", "Volume"])
    value = find_column(scored, ["ارزش معاملات", "ارزش کل", "TradeValue"])

    if volume:
        work["حجم"] = pd.to_numeric(scored[volume], errors="coerce")
    else:
        work["حجم"] = pd.NA

    if value:
        work["ارزش"] = pd.to_numeric(
            scored[value], errors="coerce"
        )
    else:
        work["ارزش"] = pd.NA

    # انتقال امتیازهای شش‌بلوک برای Audit / گزارش
    score_columns = [
        "BaseScore",
        "BlockScore_Liquidity",
        "BlockScore_Valuation",
        "BlockScore_Payoff",
        "BlockScore_Time",
        "BlockScore_Greeks",
        "BlockScore_Market",
        "ExecutionPenalty",
        "DecayPenalty",
        "DataConfidence",
    ]

    for col in score_columns:
        if col in scored.columns:
            work[col] = pd.to_numeric(scored[col], errors="coerce")
    work["AnalyticsFlags"] = scored["AnalyticsFlags"]
    work.attrs.update(scored.attrs)
    # pre_gate_rows is an internal DataFrame retained by scoring for diagnostics;
    # it must not leak into JSON audit artifacts.
    work.attrs.pop("pre_gate_rows", None)
    work.attrs["source_schema_audit"] = source_schema_audit
    work.attrs["unscorable_count"] = int(scored["FinalScore"].isna().sum())
    work.attrs["eligibility_gate_counts"] = scored.attrs.get("eligibility_gate_counts", {})
    work.attrs["production_min_leverage"] = scored.attrs.get("production_min_leverage", MIN_LEVERAGE)
    work.attrs["production_remaining_days_rule"] = scored.attrs.get("production_remaining_days_rule", "RemainingDays > 0")
    work.attrs["source_eligibility"] = source_eligibility
    work.attrs["opportunity_universe"] = opportunity_universe_view
    work.attrs["tsetmc_evidence"] = tsetmc_evidence
    work.attrs["shadow_scoring"] = {
        "status": "SUCCESS",
        "rows_scored": int(len(shadow_scored)),
        "production_gate_applied": False,
        "engine_version": shadow_scored.attrs.get("engine_version"),
    }

    # فقط قراردادهای فعال و واجد شرایط V4.1
    work = work[
        (work["آخرین"] > 0) &
        (work["پایه"] > 0) &
        (work["اهرم"] >= MIN_LEVERAGE) &
        (work["RemainingDays"] > 0) &
        work["FinalScore"].notna()
    ].copy()

    if work.empty:
        raise RuntimeError(
            "هیچ قرارداد دارای داده کافی برای امتیازدهی شش‌بلوک پیدا نشد"
        )

    # Symbol filtering has already been applied to the validated scoring
    # population above. Keeping no second text filter here prevents a
    # post-score population change from being mistaken for a pre-percentile gate.

    # رتبه‌بندی نهایی فقط بر اساس FinalScore موتور V4.1
    work = work.sort_values(
        ["FinalScore", "ارزش", "حجم", "نماد"],
        ascending=[False, False, False, True],
        na_position="last"
    )

    work = work.head(limit)

    # Keep shadow evidence attached to the report object for audit persistence.
    work.attrs["opportunity_shadow"] = shadow
    work.attrs["opportunity_shadow_summary"] = shadow.get("summary", {})
    work.attrs["replay_verification"] = replay
    work.attrs["historical_snapshot"] = {
        "status": history_result.get("status"),
        "snapshot_id": current_history.get("snapshot_id"),
        "records_hash": current_history.get("records_hash"),
        "previous_snapshot_id": previous_history.get("snapshot_id") if previous_history else None,
        "diff_summary": history_diff.get("summary", {}),
        "store_file": history_file.name,
    }

    return work

def format_report(work, source):
    source = Path(source)
    now = datetime.now(TEHRAN)

    lines = [
        f"📊 گزارش رتبه‌بندی اختیار معامله — {ENGINE_VERSION}",
        "━━━━━━━━━━━━━━━━━━━━",
        "📥 منبع: OptionSchool24",
        f"📄 فایل: {source.name}",
        f"⏱ زمان تولید: {now.strftime('%Y/%m/%d %H:%M:%S')}",
        f"📌 تعداد قراردادها: {len(work)}",
        "⚠️ زمان واقعی داده بازار در این ورودی تأیید نشده؛ زمان بالا فقط زمان تولید گزارش است.",
        "ℹ️ امتیاز، رتبه نسبی قراردادهاست؛ احتمال سود یا توصیه خرید/فروش نیست.",
        "ℹ️ روز باقی‌مانده طبق قرارداد فعلی منبع: روزهای تقویمی منهای یک.",
        f"ورودی: {work.attrs.get('input_count', 'نامشخص')} | حذف نامعتبر: {work.attrs.get('excluded_count', 'نامشخص')} | فاقد بلوک کامل: {work.attrs.get('unscorable_count', 'نامشخص')}",
        f"🔬 وضعیت Schema منبع: {work.attrs.get('source_schema_audit', {}).get('identity_readiness', 'نامشخص')} | Contract Type: {work.attrs.get('source_schema_audit', {}).get('contract_type_readiness', 'نامشخص')}",
        "━━━━━━━━━━━━━━━━━━━━",
    ]

    def fmt(v):
        if pd.isna(v):
            return "داده موجود نیست"
        return f"{float(v):,.2f}".replace(".00", "")

    def text(v):
        if pd.isna(v):
            return "داده موجود نیست"
        return str(v).strip()

    for rank, (_, row) in enumerate(work.iterrows(), 1):
        distance = row.get("فاصله سر به سری", pd.NA)
        distance_text = (
            "داده موجود نیست"
            if pd.isna(distance)
            else f"{float(distance):+.2f}%"
        )

        lines.extend([
            f"🔹 {rank}. {row['نماد']}",
            "",
            f"💰 اعمال: {fmt(row.get('اعمال', pd.NA))}",
            f"📌 آخرین: {fmt(row['آخرین'])}",
            f"🎯 سر‌به‌سر: {fmt(row.get('سر به سری', pd.NA))}",
            f"📈 پایه: {fmt(row['پایه'])}",
            f"⚖️ اهرم: {fmt(row['اهرم'])}",
            f"📏 فاصله سر‌به‌سر: {distance_text}",
            f"📅 سررسید: {text(row.get('سررسید', pd.NA))}",
            f"⏳ باقی‌مانده: {fmt(row['RemainingDays'])} روز",
            f"🏆 امتیاز: {fmt(row['FinalScore'])}",
            f"🔎 شاخص کامل‌بودن داده: {fmt(row.get('DataConfidence', pd.NA))}/100 (احتمال سود نیست)",
            f"کاهش بابت اجرا: {fmt(row.get('ExecutionPenalty', 0) * 100)}٪ | کاهش بابت سررسید: {fmt(row.get('DecayPenalty', 0) * 100)}٪",
            "⚠️ " + format_flags(row.get("AnalyticsFlags", "")),
            "",
            "━━━━━━━━━━━━━━━━━━━━",
        ])

    return "\n".join(lines)


def format_flags(flags):
    labels = {
        "MISSING_IV": "نوسان ضمنی موجود نیست",
        "MISSING_IV_HV": "نوسان تاریخی موجود نیست",
        "MISSING_BREAKEVEN": "سر‌به‌سر موجود نیست",
        "MISSING_DELTA": "دلتا موجود نیست",
        "ExtremeDelta": "قدر مطلق دلتا نزدیک حد نهایی است",
        "NEAR_EXPIRY": "نزدیک سررسید",
        "STATUS_MAPPING_NOT_APPROVED": "وضعیت بازار در امتیاز لحاظ نشده",
        "CONTRACT_TYPE_NOT_EXPLICIT": "عامل Moneyness لحاظ نشده",
        "MISSING_INTRADAY_RANGE": "دامنه روزانه موجود نیست",
    }
    return "؛ ".join(labels.get(flag, flag) for flag in str(flags).split("|") if flag) or "هشداری ثبت نشده"


def save_report(work, source):
    """Stage all report/audit artifacts and publish them only after integrity PASS."""
    report = format_report(work, source)
    output = ROOT / "output"
    output.mkdir(exist_ok=True)

    shadow = work.attrs.get("opportunity_shadow", {
        "status": "INSUFFICIENT_DATA",
        "engine_version": "OPP-SHADOW-1.0",
        "snapshot_id": None,
        "summary": {},
        "cases": [],
    })

    historical_diff = {
        "status": work.attrs.get("historical_snapshot", {}).get("status"),
        "snapshot_id": work.attrs.get("historical_snapshot", {}).get("snapshot_id"),
        "records_hash": work.attrs.get("historical_snapshot", {}).get("records_hash"),
        "previous_snapshot_id": work.attrs.get("historical_snapshot", {}).get("previous_snapshot_id"),
        "diff_summary": work.attrs.get("historical_snapshot", {}).get("diff_summary", {}),
        "store_file": work.attrs.get("historical_snapshot", {}).get("store_file"),
    }

    source_path = Path(source)
    source_sha256 = hashlib.sha256(source_path.read_bytes()).hexdigest()
    report_sha256 = hashlib.sha256(report.encode("utf-8")).hexdigest()
    selected = json.loads(work.to_json(orient="records", force_ascii=False))

    audit_attrs = dict(work.attrs)
    audit_attrs.pop("opportunity_shadow", None)
    audit_attrs.pop("pre_gate_rows", None)

    audit = {
        **audit_attrs,
        "historical_snapshot": {
            **historical_diff,
            "diff_file": "latest_historical_diff.json",
        },
        "replay_verification": {
            **work.attrs.get("replay_verification", {}),
            "artifact_file": "latest_replay_verification.json",
        },
        "tsetmc_evidence": work.attrs.get("tsetmc_evidence", {
            "status": "NOT_ATTACHED",
            "summary": {},
            "production_scoring_changed": False,
        }),
        "opportunity_shadow": {
            "status": shadow.get("status"),
            "engine_version": shadow.get("engine_version"),
            "snapshot_id": shadow.get("snapshot_id"),
            "summary": shadow.get("summary", {}),
            "case_file": "latest_opportunity_shadow.json",
        },
        "generated_at": datetime.now(TEHRAN).isoformat(),
        "source_file": source_path.name,
        "source_sha256": source_sha256,
        "source_sha256_recomputed": hashlib.sha256(source_path.read_bytes()).hexdigest(),
        "report_sha256": report_sha256,
        "market_data_timestamp": None,
        "freshness_status": "UNVERIFIED_SOURCE_TIMESTAMP_MISSING",
        "selected_count": len(work),
        "selected": selected,
    }
    audit["audit_integrity"] = verify_audit(audit)
    if audit["audit_integrity"]["status"] != "PASS":
        raise RuntimeError("Audit integrity verification failed")

    artifacts = {
        "latest_report.txt": report.encode("utf-8"),
        "latest_opportunity_shadow.json": json.dumps(
            shadow, ensure_ascii=False, indent=2, allow_nan=False
        ).encode("utf-8"),
        "latest_replay_verification.json": json.dumps(
            work.attrs.get("replay_verification", {}),
            ensure_ascii=False, indent=2, allow_nan=False
        ).encode("utf-8"),
        "latest_historical_diff.json": json.dumps(
            historical_diff, ensure_ascii=False, indent=2, allow_nan=False
        ).encode("utf-8"),
        "latest_audit.json": json.dumps(
            audit, ensure_ascii=False, indent=2, allow_nan=False
        ).encode("utf-8"),
    }

    temporary_paths = []
    try:
        for name, payload in artifacts.items():
            tmp = output / (name + ".tmp")
            tmp.write_bytes(payload)
            temporary_paths.append(tmp)

        for name in artifacts:
            tmp = output / (name + ".tmp")
            tmp.replace(output / name)
    except Exception:
        for tmp in temporary_paths:
            try:
                tmp.unlink()
            except FileNotFoundError:
                pass
        raise

    return report


def build_tsetmc_report(*, top_count=None, symbol_prefix=None, flow=1):
    """TSETMC-only validation report. No scoring/ranking is applied until field evidence gate closes."""
    from tsetmc_first_source import build_tsetmc_snapshot
    limit = TOP_COUNT if top_count is None else int(top_count)
    snapshot = build_tsetmc_snapshot(flow=flow, max_instruments=max(limit, 1))
    rows = []
    prefix = normalize_text(symbol_prefix) if symbol_prefix else None
    for item in snapshot.get("rows", []):
        canonical = item.get("canonical", {})
        symbol = normalize_text(canonical.get("نماد")) if canonical.get("نماد") else ""
        if prefix and not symbol.startswith(prefix):
            continue
        rows.append(item)

    def number(value):
        if value in (None, ""):
            return "داده موجود نیست"
        try:
            return f"{float(value):,.2f}".replace(".00", "")
        except (TypeError, ValueError):
            return str(value)

    limit = TOP_COUNT if top_count is None else int(top_count)
    rows = rows[:max(limit, 1)]
    lines = [
        "📊 گزارش اولیه بازار اختیار معامله — TSETMC-ONLY",
        "━━━━━━━━━━━━━━━━━━━━",
        "📥 منبع حقیقت: TSETMC",
        f"📌 تعداد رکوردهای Market-Watch: {snapshot.get('evidence', {}).get('market_watch', {}).get('record_count', 0)}",
        f"📌 تعداد قراردادهای قابل استخراج: {snapshot.get('row_count', 0)}",
        f"⏱ زمان دریافت: {snapshot.get('evidence', {}).get('market_watch', {}).get('retrieved_at', 'داده موجود نیست')}",
        f"🔐 Snapshot SHA256: {snapshot.get('snapshot_sha256')}",
        "⚠️ امتیازدهی شش‌بلوک و رتبه‌بندی تولیدی تا تکمیل شواهد ۳۸ فیلد فعال نشده است.",
        "⚠️ فیلدهای اثبات‌نشده عمداً «داده موجود نیست» باقی می‌مانند.",
        "━━━━━━━━━━━━━━━━━━━━",
    ]
    for idx, item in enumerate(rows, 1):
        canonical = item.get("canonical", {})
        identity = item.get("identity", {})
        lines.extend([
            f"🔹 {idx}. {canonical.get('نماد') or 'داده موجود نیست'}",
            f"نوع: {identity.get('contract_type') or 'داده موجود نیست'} | ID: {identity.get('instrument_id') or 'داده موجود نیست'}",
            f"پایه: {canonical.get('قیمت سهم پایه') if canonical.get('قیمت سهم پایه') is not None else 'داده موجود نیست'}",
            f"اعمال: {number(canonical.get('قیمت اعمال'))} | آخرین: {number(canonical.get('آخرین قیمت'))}",
            f"پایانی: {number(canonical.get('قیمت پایانی'))} | حجم: {number(canonical.get('حجم معاملات'))}",
            f"ارزش: {number(canonical.get('ارزش معاملات'))} | اندازه قرارداد: {number(canonical.get('اندازه قرارداد'))}",
            f"سررسید: {canonical.get('تاریخ سررسید') or 'داده موجود نیست'}",
            "━━━━━━━━━━━━━━━━━━━━",
        ])
    return "\n".join(lines), snapshot


def save_tsetmc_report(report, snapshot):
    output = ROOT / "output" / "tsetmc_first"
    output.mkdir(parents=True, exist_ok=True)
    report_path = output / "latest_report.txt"
    snapshot_path = output / "latest_snapshot.json"
    audit_path = output / "latest_source_audit.json"
    report_path.write_text(report, encoding="utf-8")
    snapshot_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    audit = {
        "status": "PASS" if snapshot.get("status") == "SUCCESS" else "FAIL",
        "source_of_truth": snapshot.get("source_of_truth"),
        "external_comparison_source": snapshot.get("external_comparison_source"),
        "snapshot_sha256": snapshot.get("snapshot_sha256"),
        "row_count": snapshot.get("row_count"),
        "generated_at": snapshot.get("generated_at"),
        "market_watch": snapshot.get("evidence", {}).get("market_watch", {}),
        "scoring_status": "OFF_FIELD_EVIDENCE_GATE_OPEN",
        "ranking_status": "OFF",
    }
    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    return report_path



def main():
    parser = argparse.ArgumentParser(description="Generate V4.1.1 report without sending to Bale")
    parser.add_argument("--input", type=Path, help="Use an existing workbook; otherwise download")
    parser.add_argument("--symbol", help="Symbol prefix; filtered before Top-N")
    parser.add_argument("--top", type=int, default=None)
    args = parser.parse_args()
    if args.input is not None:
        raise RuntimeError("OptionSchool24 workbook input is retired from the active runtime; use TSETMC-only source.")
    report, snapshot = build_tsetmc_report(top_count=args.top, symbol_prefix=args.symbol, flow=1)
    report_path = save_tsetmc_report(report, snapshot)
    print(report)
    print("\nREPORT_FILE =", report_path)
    print("SOURCE_OF_TRUTH = TSETMC")
    print("SCORING_STATUS = OFF_FIELD_EVIDENCE_GATE_OPEN")


if __name__ == "__main__":
    main()
