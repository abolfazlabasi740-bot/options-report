#!/usr/bin/env python3

from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import os
import time
import requests
import json
from bale_transport import send_message as transport_send

MENU_MARKUP = {
    "inline_keyboard": [
        [{"text": "📊 گزارش ۱۵ فرصت برتر", "callback_data": "report_ranked_15"}],
        [{"text": "📌 پایه آپشن‌دار", "callback_data": "base_stocks"}],
        [{"text": "⚡ فرصت لحظه آخری آپشن", "callback_data": "report_last_minute_option_opportunity"}],
        [{"text": "📈 گزارش ۱۵ قرارداد فعال", "callback_data": "report_activity_15"}],
        [{"text": "🔎 انتخاب نماد", "callback_data": "symbols_page:0"}],
        [{"text": "📋 وضعیت سیستم", "callback_data": "system_status"}],
    ]
}

REPLY_MENU_MARKUP = {
    "keyboard": [
        [{"text": "📊 گزارش ۱۵ فرصت برتر"}],
        [{"text": "📌 سهم‌های پایه"}],
        [{"text": "⚡ فرصت لحظه آخری آپشن"}],
        [{"text": "📈 گزارش ۱۵ قرارداد فعال"}],
        [{"text": "🔎 انتخاب نماد"}],
        [{"text": "🧩 استراتژی‌ها"}],
        [{"text": "📋 وضعیت سیستم"}],
    ],
    "resize_keyboard": True,
    "one_time_keyboard": False,
}

REPLY_MENU_COMMANDS = {
    "📊 گزارش ۱۵ فرصت برتر": "گزارش",
    "📌 سهم‌های پایه": "سهم‌های پایه",
    "📌 سهمهای پایه": "سهم‌های پایه",
    "سهم‌های پایه": "سهم‌های پایه",
    "سهمهای پایه": "سهم‌های پایه",
    "⚡ فرصت لحظه آخری آپشن": "فرصت‌لحظه‌آخری‌آپشن",
    "📈 گزارش ۱۵ قرارداد فعال": "فعالیت",
    "🔎 انتخاب نماد": "نمادها",
    "📋 وضعیت سیستم": "وضعیت",
}

SYMBOLS_PER_PAGE = 12
SYMBOL_PAGE_PREFIX = "نمادها صفحه "
SYMBOL_SELECT_PREFIX = "نماد: "

# ثابت‌های پرتکرار/موردنظر کاربر در ابتدای فهرست نمادهای پایه.
# فقط نمادهایی که واقعاً در Universe فعلی TSETMC وجود داشته باشند نمایش داده می‌شوند.
PREFERRED_UNDERLYINGS = (
    "اهرم",
    "وبملت",
    "وتجارت",
    "وبصادر",
    "فزر",
    "تاصیکو",
    "فملی",
    "شستا",
    "خودرو",
    "خساپا",
    "ذوب",
    "شپنا",
    "خبهمن",
    "دارونو",
    "دزاگرس",
)

CALLBACK_COMMANDS = {
    "report_ranked_15": "گزارش",
    "base_stocks": "سهم‌های پایه",
    "report_activity_15": "فعالیت",
    "report_last_minute_option_opportunity": "فرصت‌لحظه‌آخری‌آپشن",
    "option_base_cards": "سهم‌های پایه دارای آپشن",
    "system_status": "وضعیت",
}

STRATEGY_CALLBACKS = {
    "strategy_bull_call_spread": "BULL_CALL_SPREAD",
}

STRATEGY_MENU_MARKUP = {
    "inline_keyboard": [
        [{"text": "📈 Bull Call Spread", "callback_data": "strategy_bull_call_spread"}],
    ]
}

from report_engine import build_tsetmc_report, save_tsetmc_report
from github_runtime_evidence import publish_latest_evidence
from tsetmc_first_source import build_tsetmc_snapshot
from behavior_engine import build_behavior_report, format_behavior_report
from last_minute_profit_engine import build_last_minute_ranking, analyze_underlying_context
from underlying_trend_engine import fetch_underlying_context
from bull_call_spread_engine import build_strategy_report
from bale_base_share_option_cards import render_page as render_option_base_cards

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "output"
REPORT_FILE = OUTPUT / "latest_report.txt"
STATE_FILE = OUTPUT / "bale_listener_state.json"

TOKEN = os.getenv("BALE_BOT_TOKEN", "").strip()
CHAT_ID = os.getenv("BALE_CHAT_ID", "").strip()

API = f"https://tapi.bale.ai/bot{TOKEN}"


def load_offset():
    if not STATE_FILE.exists():
        return None
    try:
        payload = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        value = payload.get("next_offset")
        return int(value) if value is not None else None
    except (OSError, ValueError, TypeError):
        raise RuntimeError("Bale listener state قابل خواندن نیست")


def save_offset(next_offset):
    OUTPUT.mkdir(exist_ok=True)
    temporary = STATE_FILE.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps({"next_offset": int(next_offset)}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary.replace(STATE_FILE)


def normalize_command(text):
    if not text:
        return ""

    return (
        str(text)
        .strip()
        .replace("ي", "ی")
        .replace("ك", "ک")
        .replace("‌", "")
    )


def send_message(chat_id, text, reply_markup=None):
    count = transport_send(TOKEN, chat_id, text, reply_markup=reply_markup)
    print(f"SENT {count}/{count}")


def system_status():
    audit_path = OUTPUT / "latest_audit.json"
    report_path = OUTPUT / "latest_report.txt"

    if not audit_path.exists():
        return "⚠️ وضعیت V4.1\n\nAudit موجود نیست؛ هنوز اجرای معتبر گزارش ثبت نشده است."

    try:
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return "⚠️ وضعیت V4.1\n\nفایل Audit قابل خواندن نیست."

    integrity = audit.get("audit_integrity", {})
    status = integrity.get("status") or audit.get("status") or "UNKNOWN"
    failures = integrity.get("failures") or []
    missing = integrity.get("missing_fields") or []

    lines = [
        "📊 وضعیت OptimusAI V4.1",
        "",
        f"Audit: {status}",
        f"Source: {audit.get('source_of_truth') or 'داده موجود نیست'}",
        f"Data Mode: {audit.get('data_mode') or 'داده موجود نیست'}",
        f"Refresh: {audit.get('live_refresh_status') or 'داده موجود نیست'}",
        f"Scoring: {audit.get('scoring_status') or 'داده موجود نیست'}",
        f"Ranking: {audit.get('ranking_status') or 'داده موجود نیست'}",
        f"Snapshot SHA: {audit.get('snapshot_sha256') or 'داده موجود نیست'}",
        f"Report SHA: {audit.get('report_sha256') or 'داده موجود نیست'}",
    ]

    if failures:
        lines.append("Audit Failures: " + ", ".join(str(x) for x in failures))
    else:
        lines.append("Audit Failures: 0")

    if missing:
        lines.append("Audit Missing Fields: " + ", ".join(str(x) for x in missing))
    else:
        lines.append("Audit Missing Fields: 0")

    if not report_path.exists():
        lines.append("Report File: MISSING")
    else:
        lines.append("Report File: READY")

    return "\n".join(lines)


def _gregorian_to_jalali(gy, gm, gd):
    """Convert Gregorian date to Jalali without external dependencies."""
    g_days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    j_days_in_month = [31, 31, 31, 31, 31, 31, 30, 30, 30, 30, 30, 29]
    gy2 = gy - 1600
    gm2 = gm - 1
    gd2 = gd - 1
    g_day_no = 365 * gy2 + (gy2 + 3) // 4 - (gy2 + 99) // 100 + (gy2 + 399) // 400
    for i in range(gm2):
        g_day_no += g_days_in_month[i]
    if gm2 > 1 and ((gy % 4 == 0 and gy % 100 != 0) or (gy % 400 == 0)):
        g_day_no += 1
    g_day_no += gd2
    j_day_no = g_day_no - 79
    j_np = j_day_no // 12053
    j_day_no %= 12053
    jy = 979 + 33 * j_np + 4 * (j_day_no // 1461)
    j_day_no %= 1461
    if j_day_no >= 366:
        jy += (j_day_no - 1) // 365
        j_day_no = (j_day_no - 1) % 365
    i = 0
    while i < 11 and j_day_no >= j_days_in_month[i]:
        j_day_no -= j_days_in_month[i]
        i += 1
    return jy, i + 1, j_day_no + 1


def _snapshot_datetime_label(snapshot):
    evidence = snapshot.get("evidence") or {}
    market_watch = evidence.get("market_watch") or {}
    raw = market_watch.get("latest_source_market_timestamp")
    if not raw:
        rows = snapshot.get("rows") or []
        timestamps = [r.get("source_market_timestamp") for r in rows if r.get("source_market_timestamp")]
        raw = max(timestamps) if timestamps else None
    if not raw:
        raw = snapshot.get("generated_at") or market_watch.get("retrieved_at")
    if not raw:
        return "داده موجود نیست"
    try:
        text = str(raw).replace("Z", "+00:00")
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is not None:
            dt = dt.astimezone(ZoneInfo("Asia/Tehran"))
        jy, jm, jd = _gregorian_to_jalali(dt.year, dt.month, dt.day)
        return f"{jy:04d}/{jm:02d}/{jd:02d} {dt:%H:%M:%S}"
    except (TypeError, ValueError, OverflowError):
        return str(raw)


def _base_discovery_report(underlying_context):
    """Rank base stocks separately from option contracts for opportunity discovery."""
    candidates = []
    for underlying_id, raw in (underlying_context or {}).items():
        if not isinstance(raw, dict) or raw.get("status") == "UNAVAILABLE":
            continue
        analysis = analyze_underlying_context(raw)
        available = []
        for key in ("momentum_score", "board_score", "volume_score"):
            value = analysis.get(key)
            if isinstance(value, (int, float)) and value > 0:
                available.append(float(value))
        if not available:
            continue
        base_score = sum(available) / len(available)
        early = raw.get("early_move") or {}
        prelock = early.get("pre_lock_sequence") or {}
        candidates.append({
            "underlying_id": underlying_id,
            "symbol": raw.get("underlying_symbol") or raw.get("symbol") or "",
            "score": round(base_score, 2),
            "momentum": round(float(analysis.get("momentum_score") or 0), 1),
            "board": round(float(analysis.get("board_score") or 0), 1),
            "volume": round(float(analysis.get("volume_score") or 0), 1),
            "trend": raw.get("trend_state") or "داده موجود نیست",
            "early_state": early.get("state") or "داده موجود نیست",
            "prelock_state": prelock.get("state") or "داده موجود نیست",
            "prelock_sequence": prelock.get("sequence") or "داده موجود نیست",
            "headroom": raw.get("upper_limit_headroom_pct"),
            "touched_upper": raw.get("touched_upper_limit_today"),
        })
    candidates.sort(key=lambda x: (x["score"], x["momentum"], x["volume"], x["symbol"]), reverse=True)
    return candidates[:10]


def generate_report(command):
    if command in ("رفتار", "تغییرات", "behavior"):
        return format_behavior_report(build_behavior_report(ROOT))
    if command in ("فرصت‌لحظه‌آخری‌آپشن", "فرصت لحظه آخری آپشن", "last_minute_option_opportunity"):
        snapshot = build_tsetmc_snapshot(flow=None, max_instruments=None, symbol_prefix=None)

        # Live data is preferred during market hours, but it is NOT required.
        # Outside market hours, the latest valid TSETMC snapshot is an accepted
        # data basis and must be clearly labeled in the report.
        source_rows = snapshot.get("rows", [])
        underlying_symbol_by_id = {}
        for row in source_rows:
            identity = row.get("identity") or {}
            underlying_id = str(identity.get("underlying_id") or "").strip()
            underlying_symbol = str(identity.get("underlying_symbol") or "").strip()
            if underlying_id and underlying_symbol:
                underlying_symbol_by_id[underlying_id] = underlying_symbol

        underlying_ids = sorted(underlying_symbol_by_id)
        underlying_context = fetch_underlying_context(underlying_ids)

        # Preserve the canonical underlying identity from the option snapshot.
        # The technical engine is keyed by instrument_id and may not carry the
        # display symbol forward. Base Discovery must never emit a blank symbol
        # when TSETMC supplied an explicit underlying_symbol.
        instruments = underlying_context.get("instruments", {})
        for underlying_id, raw in instruments.items():
            if isinstance(raw, dict):
                raw["underlying_id"] = underlying_id
                canonical_symbol = underlying_symbol_by_id.get(str(underlying_id).strip())
                if canonical_symbol:
                    raw["underlying_symbol"] = canonical_symbol

        result = build_last_minute_ranking(
            source_rows,
            top_count=15,
            underlying_context=underlying_context.get("instruments", {}),
            snapshot=snapshot,
        )

        snapshot_label = _snapshot_datetime_label(snapshot)
        base_watch = _base_discovery_report(underlying_context.get("instruments", {}))
        selected_symbols = {str(item.get("underlying_symbol") or "").strip() for item in result.get("ranking_rows", [])}
        lines = [
            "⚡ فرصت لحظه آخری آپشن",
            "TSETMC-ONLY | CURRENT-EVIDENCE OPTION OPPORTUNITY",
            "━━━━━━━━━━━━━━━━━━━━",
            f"📅 تاریخ/زمان دیتای Snapshot: {snapshot_label}",
            f"📊 وضعیت داده: {snapshot.get('data_mode') or 'داده موجود نیست'} | Refresh: {snapshot.get('live_refresh_status') or 'داده موجود نیست'}",
            "مبنای گزارش: ابتدا کشف سهم پایه قوی، سپس ارزیابی زنجیره آپشن همان سهم.",
            "انتخاب نهایی آپشن: امتیاز جهانی + سقف حداکثر ۳ قرارداد از هر سهم پایه؛ سقف ۳ سهم پایه را مجبور به پر کردن سهمیه نمی‌کند.",
            f"تعداد کاندیداهای معتبر آپشن: {result.get('candidate_count', 0)}",
            f"تعداد نمایش: {result.get('display_count', 0)}",
            "━━━━━━━━━━━━━━━━━━━━",
            "🔎 پایش سهم‌های پایه برتر",
        ]
        if base_watch:
            for index, base in enumerate(base_watch, 1):
                headroom = base.get("headroom")
                headroom_text = f"{headroom:.2f}%" if isinstance(headroom, (int, float)) else "داده موجود نیست"
                option_state = "آپشن در ۱۵ گزینه نهایی دارد" if base["symbol"] in selected_symbols else "در ۱۵ گزینه نهایی آپشن ندارد"
                lines.extend([
                    f"{index}. {base['symbol'] or 'داده موجود نیست'} | قدرت پایه: {base['score']:.1f} | روند: {base['trend']}",
                    f"   مومنتوم: {base['momentum']:.1f} | تابلو: {base['board']:.1f} | حجم/ارزش: {base['volume']:.1f} | فاصله سقف: {headroom_text}",
                    f"   توالی: {base['prelock_sequence']} | وضعیت پیش‌قفلی: {base['prelock_state']} | {option_state}",
                ])
        else:
            lines.append("داده کافی برای کشف سهم پایه موجود نیست.")
        lines.append("━━━━━━━━━━━━━━━━━━━━")

        if not result.get("ranking_rows"):
            lines.append("در این لحظه فرصت معتبر با شواهد کافی پیدا نشد.")
        else:
            for item in result["ranking_rows"]:
                components = item.get("score_components") or {}
                analysis = item.get("underlying_analysis") or {}
                lines.extend([
                    f"🔹 {item['rank']}. {item.get('symbol') or 'داده موجود نیست'} | امتیاز فرصت: {item.get('score')}",
                    f"پایه: {item.get('underlying_symbol') or 'داده موجود نیست'} | نوع: {item.get('contract_type') or 'داده موجود نیست'} | جهت: {item.get('direction') or 'داده موجود نیست'}",
                    f"قیمت پایه: {item.get('underlying_price')} | اعمال: {item.get('strike')} | قیمت آپشن: {item.get('current_option_price')}",
                    f"فاصله اعمال: {item.get('moneyness_pct'):.2f}% | روز باقی‌مانده: {item.get('days_to_expiry')}",
                    f"اهرم خام: {item.get('raw_leverage'):.2f}x | امتیاز نقدشوندگی: {components.get('option_liquidity'):.1f}",
                    f"قدرت پایه: {components.get('underlying_momentum'):.1f} | تابلو: {components.get('board_strength'):.1f} | حجم/ارزش: {components.get('volume_value'):.1f}",
                    f"فاصله تا سقف: {item.get('underlying_analysis', {}).get('upper_limit_headroom_pct') if item.get('underlying_analysis') else 'داده موجود نیست'}%",
                    f"شواهد پایه: {', '.join(analysis.get('evidence') or []) or 'داده موجود نیست'}",
                    "━━━━━━━━━━━━━━━━━━━━",
                ])
        return "\n".join(lines)
    if command in ("گزارش", "همه", "کل"):
        report, snapshot = build_tsetmc_report(
            top_count=15,
            flow=None,
            report_mode="RANKED",
        )
    elif command in ("فعالیت", "معاملات", "تاپ"):
        report, snapshot = build_tsetmc_report(
            top_count=15,
            flow=None,
            report_mode="TRADING_ACTIVITY",
        )
    else:
        report, snapshot = build_tsetmc_report(
            top_count=5,
            underlying_symbol=command,
            flow=None,
            report_mode="RANKED",
        )

    # Fail closed for every RANKED route, including symbol-specific Top-5.
    # A symbol report must use the same TSETMC economic ranking as the global
    # Top-15 report; only the universe is narrowed to the selected underlying.
    if snapshot.get("report_mode") == "RANKED":
        ranking = snapshot.get("ranking") or {}
        if ranking.get("mode") != "TSETMC_ECONOMIC_SCORING":
            raise RuntimeError(
                "REPORT_RANKING_MODE_MISMATCH: expected=TSETMC_ECONOMIC_SCORING; "
                f"actual={ranking.get('mode')}"
            )
        if ranking.get("status") != "PASS":
            raise RuntimeError(
                "REPORT_RANKING_STATUS_BLOCKED: "
                f"status={ranking.get('status')}"
            )
        if command not in ("گزارش", "همه", "کل") and snapshot.get("underlying_symbol") != command:
            raise RuntimeError(
                "REPORT_SYMBOL_ROUTE_MISMATCH: "
                f"expected={command}; actual={snapshot.get('underlying_symbol')}"
            )

    # Every Bale report must expose the exact data snapshot date/time before
    # the analytical body. The date belongs to the data, not the report request.
    snapshot_label = _snapshot_datetime_label(snapshot)
    report = (
        f"📅 تاریخ/زمان دیتای Snapshot: {snapshot_label}\\n"
        f"📊 وضعیت داده: {snapshot.get('data_mode') or 'داده موجود نیست'} | Refresh: {snapshot.get('live_refresh_status') or 'داده موجود نیست'}\\n"
        "━━━━━━━━━━━━━━━━━━━━\\n"
        + report
    )

    # Evidence publication is deliberately kept out of the Bale response path.
    # The user must receive the report first; audit publication is non-critical.
    save_tsetmc_report(report, snapshot)
    return report


def get_updates(offset=None):
    params = {
        "timeout": 30,
    }

    if offset is not None:
        params["offset"] = offset

    r = requests.get(
        f"{API}/getUpdates",
        params=params,
        timeout=40,
    )

    r.raise_for_status()

    data = r.json()

    if not data.get("ok"):
        raise RuntimeError(f"Bale getUpdates error: {data}")

    return data.get("result", [])


def answer_callback_query(callback_query_id):
    r = requests.post(
        f"{API}/answerCallbackQuery",
        data={"callback_query_id": callback_query_id},
        timeout=15,
    )
    r.raise_for_status()
    data = r.json()
    if not data.get("ok"):
        raise RuntimeError("Bale answerCallbackQuery rejected")


def _underlying_symbols():
    """Build selectable underlying symbols from the current TSETMC option universe."""
    snapshot = build_tsetmc_snapshot(flow=None, max_instruments=None, symbol_prefix=None)
    symbols = {
        str((row.get("identity") or {}).get("underlying_symbol") or "").strip()
        for row in snapshot.get("rows", [])
    }
    available = {symbol for symbol in symbols if symbol}
    preferred = [symbol for symbol in PREFERRED_UNDERLYINGS if symbol in available]
    remaining = sorted(
        available.difference(preferred),
        key=lambda value: value,
    )
    return preferred + remaining


def send_symbol_menu(chat_id, page=0):
    symbols = _underlying_symbols()
    total_pages = max(1, (len(symbols) + SYMBOLS_PER_PAGE - 1) // SYMBOLS_PER_PAGE)
    page = max(0, min(int(page), total_pages - 1))
    page_symbols = symbols[page * SYMBOLS_PER_PAGE:(page + 1) * SYMBOLS_PER_PAGE]
    keyboard = []
    for index in range(0, len(page_symbols), 2):
        keyboard.append([{"text": f"{SYMBOL_SELECT_PREFIX}{symbol}"} for symbol in page_symbols[index:index + 2]])
    navigation = []
    if page > 0:
        navigation.append({"text": f"{SYMBOL_PAGE_PREFIX}{page}"})
    if page < total_pages - 1:
        navigation.append({"text": f"{SYMBOL_PAGE_PREFIX}{page + 2}"})
    if navigation:
        keyboard.append(navigation)
    keyboard.append([{"text": "🏠 منوی اصلی"}])
    # Use Bale inline (glass) buttons for symbol selection so the user can
    # tap a symbol directly. Reply-keyboard support remains available through
    # the existing "🔎 انتخاب نماد" command.
    inline_keyboard = []
    for index in range(0, len(page_symbols), 2):
        inline_keyboard.append([
            {"text": symbol, "callback_data": f"symbol:{symbol}"}
            for symbol in page_symbols[index:index + 2]
        ])
    navigation = []
    if page > 0:
        navigation.append({"text": "◀️ صفحه قبل", "callback_data": f"symbols_page:{page - 1}"})
    if page < total_pages - 1:
        navigation.append({"text": "صفحه بعد ▶️", "callback_data": f"symbols_page:{page + 1}"})
    if navigation:
        inline_keyboard.append(navigation)
    inline_keyboard.append([{"text": "🏠 منوی اصلی", "callback_data": "main_menu"}])
    markup = {"inline_keyboard": inline_keyboard}
    send_message(
        chat_id,
        f"🔎 انتخاب نماد پایه\n\nتعداد نمادهای دارای اختیار معامله در TSETMC: {len(symbols)}\nصفحه {page + 1} از {total_pages}\n\nبا انتخاب هر نماد، ۵ قرارداد برتر همان نماد بر اساس Ranking اقتصادی TSETMC نمایش داده می‌شود:",
        reply_markup=markup,
    )


def send_strategy_menu(chat_id):
    send_message(
        chat_id,
        "🧩 استراتژی‌ها\n\nاستراتژی موردنظر را انتخاب کنید:",
        reply_markup=STRATEGY_MENU_MARKUP,
    )


def generate_strategy_report(strategy):
    if strategy != "BULL_CALL_SPREAD":
        raise RuntimeError("UNKNOWN_STRATEGY: " + str(strategy))

    snapshot = build_tsetmc_snapshot(
        flow=None,
        max_instruments=None,
        symbol_prefix=None,
    )
    rows = snapshot.get("rows") or []
    result = build_strategy_report(rows, top_count=15)

    lines = [
        "📈 Bull Call Spread",
        "TSETMC-ONLY",
        "📅 تاریخ/زمان دیتای Snapshot: " + _snapshot_datetime_label(snapshot),
        "📊 وضعیت داده: " + str(snapshot.get("data_mode") or "داده موجود نیست") + " | Refresh: " + str(snapshot.get("live_refresh_status") or "داده موجود نیست"),
        "━━━━━━━━━━━━━━━━━━━━",
        "وضعیت موتور: " + str(result.get("status") or "داده موجود نیست"),
        "تعداد کاندیدا: " + str(result.get("candidate_count", 0)),
        "Snapshot SHA: " + str(snapshot.get("snapshot_sha256") or "داده موجود نیست"),
        "━━━━━━━━━━━━━━━━━━━━",
    ]

    results = result.get("results") or []
    if not results:
        lines.append("کاندیدای معتبر Bull Call Spread پیدا نشد.")
        return "\n".join(lines)

    for index, item in enumerate(results, 1):
        lines.extend([
            "🔹 Spread " + str(index),
            "پایه: " + str(item.get("underlying_symbol") or "داده موجود نیست"),
            "سررسید: " + str(item.get("expiry") or "داده موجود نیست"),
            "Call خرید: " + str(item.get("long_call_symbol") or "داده موجود نیست") + " | Strike: " + str(item.get("lower_strike")),
            "Call فروش: " + str(item.get("short_call_symbol") or "داده موجود نیست") + " | Strike: " + str(item.get("higher_strike")),
            "Premium خرید: " + str(item.get("long_premium")),
            "Premium فروش: " + str(item.get("short_premium")),
            "Net Debit: " + str(item.get("net_debit")),
            "حداکثر زیان: " + str(item.get("max_loss")),
            "حداکثر سود: " + str(item.get("max_profit")),
            "نقطه سربه‌سر: " + str(item.get("breakeven")),
            "Liquidity Evidence: " + str(item.get("liquidity_evidence")),
            "Profit/Loss Efficiency: " + str(item.get("profit_loss_efficiency")),
            "سیگنال اجرا: False",
            "توصیه خرید/فروش: False",
            "━━━━━━━━━━━━━━━━━━━━",
        ])

    return "\n".join(lines)


def send_report_menu(chat_id):
    send_message(
        chat_id,
        "📋 منوی گزارش‌های OptimusAI V4.1\n\nاز منوی پایین، گزارش موردنظر را انتخاب کنید:",
        reply_markup=REPLY_MENU_MARKUP,
    )
    send_message(
        chat_id,
        "📌 رتبه‌بندی سهم‌های پایه دارای آپشن؛ هر سهم با امتیاز و دلایل امتیاز به‌صورت کارت نمایش داده می‌شود:",
        reply_markup={"inline_keyboard": [[{"text": "📊 کارت‌های سهم پایه آپشن‌دار", "callback_data": "option_base_cards:0"}]]},
    )


def main():
    if not TOKEN or not CHAT_ID:
        raise RuntimeError("BALE_BOT_TOKEN و BALE_CHAT_ID باید از قبل تنظیم شوند")

    print("====================================")
    print("OptimusAI V4.1 Bale Listener")
    print("====================================")
    print("منو -> دکمه‌های شیشه‌ای گزارش‌های از پیش تعریف‌شده")
    print("گزارش -> 15 فرصت برتر بر اساس رنکینگ 6 بلوکی TSETMC")
    print("نماد  -> 5 فرصت برتر همان نماد پایه بر اساس رنکینگ 6 بلوکی")
    print("فعالیت -> 15 قرارداد برتر از نظر فعالیت معاملاتی")
    print("====================================")

    send_report_menu(CHAT_ID)

    offset = load_offset()

    while True:
        try:
            updates = get_updates(offset)

            for update in updates:
                next_offset = int(update["update_id"]) + 1

                callback = update.get("callback_query") or {}
                if callback:
                    callback_message = callback.get("message") or {}
                    callback_chat = callback_message.get("chat") or {}
                    chat_id = callback_chat.get("id")

                    if not chat_id:
                        save_offset(next_offset)
                        offset = next_offset
                        continue

                    if CHAT_ID and str(chat_id) != str(CHAT_ID):
                        save_offset(next_offset)
                        offset = next_offset
                        continue

                    # Callback acknowledgement is best-effort. Bale may reject
                    # an old callback with HTTP 400 after its short response window;
                    # that must never prevent the requested report from executing.
                    try:
                        answer_callback_query(callback.get("id"))
                    except Exception as ack_error:
                        response = getattr(ack_error, "response", None)
                        status_code = getattr(response, "status_code", None)
                        print(
                            "CALLBACK_ACK_ERROR "
                            f"type={type(ack_error).__name__} "
                            f"http_status={status_code}"
                        )

                    try:
                        callback_data = str(callback.get("data") or "").strip()
                        command = CALLBACK_COMMANDS.get(callback_data)
                        strategy = STRATEGY_CALLBACKS.get(callback_data)

                        if callback_data.startswith("option_base_cards:"):
                            page = int(callback_data.split(":", 1)[1])
                            report, markup, count, current_page, total_pages = render_option_base_cards(page)
                            send_message(chat_id, report, reply_markup=markup)
                        elif callback_data.startswith("symbols_page:"):
                            page = int(callback_data.split(":", 1)[1])
                            send_symbol_menu(chat_id, page)
                        elif callback_data.startswith("symbol:"):
                            symbol = normalize_command(callback_data.split(":", 1)[1])
                            if not symbol:
                                raise RuntimeError("EMPTY_SYMBOL_CALLBACK")
                            report = generate_report(symbol)
                            send_message(chat_id, report)
                            try:
                                publish_latest_evidence()
                            except Exception as exc:
                                print("GITHUB_EVIDENCE_ERROR:", type(exc).__name__)
                            send_report_menu(chat_id)
                        elif callback_data == "main_menu":
                            send_report_menu(chat_id)
                        elif callback_data == "base_stocks":
                            report, markup, count, current_page, total_pages = render_option_base_cards(0)
                            send_message(chat_id, report, reply_markup=markup)
                        elif strategy:
                            report = generate_strategy_report(strategy)
                            send_message(chat_id, report)
                            send_strategy_menu(chat_id)
                            send_report_menu(chat_id)
                        elif command == "وضعیت":
                            send_message(chat_id, system_status())
                            send_report_menu(chat_id)
                        elif command:
                            report = generate_report(command)
                            send_message(chat_id, report)
                            try:
                                publish_latest_evidence()
                            except Exception as exc:
                                print("GITHUB_EVIDENCE_ERROR:", type(exc).__name__)
                            send_report_menu(chat_id)
                        else:
                            raise RuntimeError("UNKNOWN_CALLBACK")
                        print(
                            f"REPORT_OK callback={callback.get('data')}"
                        )
                        save_offset(next_offset)
                        offset = next_offset
                    except Exception as e:
                        print(
                            f"REPORT_ERROR type={type(e).__name__}"
                        )
                    continue

                message = (
                    update.get("message")
                    or update.get("edited_message")
                    or {}
                )

                chat = message.get("chat", {})
                chat_id = chat.get("id")

                text = normalize_command(
                    message.get("text", "")
                )

                if not chat_id or not text:
                    save_offset(next_offset)
                    offset = next_offset
                    continue

                if CHAT_ID and str(chat_id) != str(CHAT_ID):
                    save_offset(next_offset)
                    offset = next_offset
                    continue

                text = REPLY_MENU_COMMANDS.get(text, text)

                print(
                    f"COMMAND = {text} | CHAT_ID = {chat_id}"
                )

                try:
                    if text in ("منو", "menu", "/start", "/menu", "🏠 منوی اصلی"):
                        send_report_menu(chat_id)
                    elif text in ("استراتژی‌ها", "استراتژی ها", "استراتژی"):
                        send_strategy_menu(chat_id)
                    elif text in ("رفتار", "تغییرات", "behavior"):
                        send_message(chat_id, generate_report("رفتار"))
                        send_report_menu(chat_id)
                    elif text in ("سهم‌های پایه", "سهمهای پایه", "base_stocks"):
                        report, markup, count, current_page, total_pages = render_option_base_cards(0)
                        send_message(chat_id, report, reply_markup=markup)
                    elif text == "نمادها":
                        send_symbol_menu(chat_id, 0)
                    elif text.startswith(SYMBOL_PAGE_PREFIX):
                        page_number = int(text[len(SYMBOL_PAGE_PREFIX):].strip()) - 1
                        send_symbol_menu(chat_id, page_number)
                    elif text.startswith(SYMBOL_SELECT_PREFIX):
                        symbol = text[len(SYMBOL_SELECT_PREFIX):].strip()
                        if not symbol:
                            raise ValueError("نماد پایه خالی است")
                        report = generate_report(symbol)
                        send_message(chat_id, report)
                        send_report_menu(chat_id)
                    elif text in ("وضعیت", "استاتوس", "status"):
                        send_message(chat_id, system_status())
                        send_report_menu(chat_id)
                    else:
                        report = generate_report(text)
                        send_message(chat_id, report)
                        try:
                            publish_latest_evidence()
                        except Exception as exc:
                            print("GITHUB_EVIDENCE_ERROR:", type(exc).__name__)
                        send_report_menu(chat_id)

                    print(
                        f"REPORT_OK command={text}"
                    )
                    save_offset(next_offset)
                    offset = next_offset

                except Exception as e:
                    print(
                        f"REPORT_ERROR type={type(e).__name__}"
                    )

                    try:
                        send_message(
                            chat_id,
                            "⚠️ خطا در تولید گزارش V4.1\n\n"
                            + "داده یا ارتباط قابل تأیید نیست؛ تولید یا ارسال گزارش کامل نشد.",
                        )
                    except Exception as send_error:
                        print(
                            "ERROR_MESSAGE_SEND_FAILED:",
                            type(send_error).__name__,
                        )
                    else:
                        save_offset(next_offset)
                        offset = next_offset

        except KeyboardInterrupt:
            print("\nLISTENER_STOPPED")
            break

        except Exception as e:
            print("LISTENER_ERROR:", type(e).__name__)
            time.sleep(5)


if __name__ == "__main__":
    main()
