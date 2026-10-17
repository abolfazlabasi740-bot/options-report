# -*- coding: utf-8 -*-
"""ماژول گزارش تحلیل مدیریتی — نسخه ۲: خروجی تحلیل نوشتاری (نه لیست خام)"""
import json, os, glob

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MGMT_JSON = os.path.join(BASE_DIR, "output", "base_share",
                         "latest_management_analysis_report.json")

def latest_mgmt_report():
    """آخرین گزارش تحلیل مدیریتی + متادیتا (بدون fallback خاموش)"""
    out = {"json": MGMT_JSON if os.path.exists(MGMT_JSON) else None}
    if out["json"]:
        try:
            with open(out["json"], encoding="utf-8") as f:
                data = json.load(f)
            out["data"] = data
            out["ts"] = data.get("data_time_label") or "—"
            out["jalali"] = data.get("latest_history_date_jalali") or "—"
            out["generated_at"] = data.get("generated_at") or "—"
            out["top"] = data.get("top10") or []
            out["status"] = data.get("trade_permission") or "UNKNOWN"
        except Exception:
            out["data"] = {}
            out["ts"], out["jalali"], out["top"], out["status"] = "—", "—", [], "PARSE_ERROR"
    else:
        out["data"] = {}
        out["ts"], out["jalali"], out["top"], out["status"] = "—", "—", [], "NOT_GENERATED"
    return out

def mgmt_button_row():
    return [{"text": "📊 تحلیل مدیریتی",
             "callback_data": "send_latest_mgmt"}]

def mgmt_status_caption():
    r = latest_mgmt_report()
    return "📅 گزارش تحلیل مدیریتی — جلسه {j}\n🕒 داده: {ts} | وضعیت: {st}".format(
        j=r["jalali"], ts=r["ts"], st=r["status"])

def _fa_num(x):
    return str(x)

def _build_narrative(r):
    """تولید متن تحلیلی نوشتاری — فقط از فیلدهای واقعی JSON"""
    d = r["data"]
    top = r["top"]
    sep = "▬" * 22

    # ۱) سربرگ
    lines = ["📊 گزارش تحلیل مدیریتی — تحلیل نوشتاری",
             "📅 جلسه: {j}".format(j=r["jalali"]),
             "🕒 {ts}".format(ts=r["ts"]),
             "🧾 نسخه گزارش: {v} | تولید: {g}".format(
                 v=d.get("report_version", "—"),
                 g=d.get("generated_at", "—")[:16].replace("T", " ")),
             sep]

    # ۲) خلاصه مدیریتی
    n = d.get("universe_size")
    if top:
        scores = [s.get("final_score") for s in top if isinstance(s.get("final_score"), (int, float))]
        rets  = [s.get("return_20_sessions_pct") for s in top if isinstance(s.get("return_20_sessions_pct"), (int, float))]
        rsis  = [s.get("rsi_14") for s in top if isinstance(s.get("rsi_14"), (int, float))]
        a_cnt = sum(1 for s in top if s.get("classification") == "A")
        b_cnt = sum(1 for s in top if s.get("classification") == "B")
        obs   = [s.get("buy_sell_signal") for s in top if s.get("buy_sell_signal")]
        lines.append("🔍 خلاصه مدیریتی:")
        if n:
            lines.append("• دامنه پایش: {n} نماد؛ گزارش بر ۱۰ نماد برتر متمرکز است.".format(n=n))
        if scores:
            avg_sc = sum(scores) / len(scores)
            lines.append("• امتیاز کل ۱۰ نماد برتر بین {mn:.2f} تا {mx:.2f} با میانگین {av:.2f} است؛ غلظت کیفیت در بالای جدول بالاست.".format(
                mn=min(scores), mx=max(scores), av=avg_sc))
        if a_cnt or b_cnt:
            lines.append("• ترکیب طبقهبندی: {a} نماد رده A و {b} نماد رده B — عمده نامزدها در طبقه کیفی بالا قرار دارند.".format(a=a_cnt, b=b_cnt))
        if rets:
            pos = sum(1 for x in rets if x > 0)
            neg = len(rets) - pos
            avg_r = sum(rets) / len(rets)
            best = max(top, key=lambda s: s.get("return_20_sessions_pct") or -1e9)
            lines.append("• بازده ۲۰ جلسه اخیر: {p} نماد مثبت و {ng} نماد منفی؛ میانگین بازده {av:.2f}٪ — قویترین عملکرد متعلق به {sym} با {r:.2f}٪.".format(
                p=pos, ng=neg, av=avg_r, sym=best.get("symbol", "—"),
                r=best.get("return_20_sessions_pct", 0)))
        if rsis:
            overbought = [s.get("symbol") for s in top if isinstance(s.get("rsi_14"), (int, float)) and s.get("rsi_14") >= 70]
            near_ob    = [s.get("symbol") for s in top if isinstance(s.get("rsi_14"), (int, float)) and 65 <= s.get("rsi_14") < 70]
            lines.append("• RSI-14: میانگین {av:.1f}؛ {ob} نماد در ناحیه اشباع خرید (≥۷۰): {sy} — ریسک اصلاح کوتاه‌مدت.{nb}".format(
                av=sum(rsis)/len(rsis),
                ob=len(overbought),
                sy="، ".join(overbought) if overbought else "—",
                nb=(" نماد نزدیک اشباع (۶۵–۷۰): " + "، ".join(near_ob) + ".") if near_ob else ""))
        if obs and all(x == "NOT_GENERATED" for x in obs):
            lines.append("• سیگنال خرید/فروش برای هیچ‌یک از نمادها تولید نشده است (NOT_GENERATED) — لایه تصمیم هنوز مهر تأیید نگذاشته.")
    else:
        lines.append("⚠️ داده جدول برتر برای تحلیل موجود نیست.")
    lines.append(sep)

    # ۳) وضعیت داده‌ها
    lines.append("🗂 وضعیت داده‌ها:")
    lines.append("• نوع داده: {dt}".format(dt=d.get("data_type", "—")))
    fl = d.get("fundamental_layer")
    if fl:
        lines.append("• لایه بنیادی: {fl} — بنابراین تحلیل فعلاً صرفاً تکنیکال/روندی است و کیفیت سود و نسبت‌های مالی در آن لحاظ نشده.".format(fl=fl))
    lines.append("• ردگیر منبع: SHA-256 گزارش مبدأ ثبت شده ({sh:.12}…).".format(
        sh=d.get("source_report_sha256", "—")) if d.get("source_report_sha256") else "• ردگیر منبع: ندارد.")
    lines.append(sep)

    # ۴) روایت نمادها (نه لیست خام)
    if top:
        lines.append("📈 روایت ۱۰ نماد برتر:")
        for s in top[:10]:
            lines.append("• {sym} (رده {cls}) — امتیاز {sc:.2f} | بازده ۲۰ جلسه {r:+.2f}٪ | RSI-14 {rsi:.1f}: {note}".format(
                sym=s.get("symbol", "—"),
                cls=s.get("classification", "—"),
                sc=s.get("final_score", 0) if isinstance(s.get("final_score"), (int, float)) else 0,
                r=s.get("return_20_sessions_pct", 0) if isinstance(s.get("return_20_sessions_pct"), (int, float)) else 0,
                rsi=s.get("rsi_14", 0) if isinstance(s.get("rsi_14"), (int, float)) else 0,
                note=s.get("management_note", "بدون یادداشت")))
        lines.append(sep)

    # ۵) ارزیابی ریسک
    lines.append("⚠️ ارزیابی ریسک:")
    if top:
        rsis = [s.get("rsi_14") for s in top if isinstance(s.get("rsi_14"), (int, float))]
        if any(x >= 70 for x in rsis):
            lines.append("• ریسک اصلاح کوتاه‌مدت: نمادهای اشباع خرید در صدر جدول، مستعد تنبیه قیمتی هستند؛ ورود پلکانی با حدضرر توصیه میشود.")
        if fl:
            lines.append("• ریسک داده: فقدان لایه بنیادی یعنی تصمیم صرفاً بر بستر روند است؛ کیفیت سود و ارزش ذاتی سنجه نشده.")
        lines.append("• ریسک سیگنال: عدم تولید سیگنال قطعی (NOT_GENERATED) — تصمیمگیری مستقیم با Decision Engine باقی میماند.")
    lines.append(sep)

    # ۶) نتیجه‌گیری
    lines.append("🎯 نتیجه‌گیری:")
    lines.append("• وضعیت مجوز معامله: {st}".format(st=r["status"]))
    lines.append("• جمع‌بندی: فضای روندی ۱۰ نماد برتر مثبت است اما سیگنال قطعی مطابق منشور تولید نشده؛ ورود به معامله در این مرحله مجاز شمرده نمیشود.".format())
    lines.append(sep)
    lines.append("🔻 سطح اطمینان تحلیل: متوسط — داده تکنیکال EOD کامل، لایه بنیادی غایب.")
    lines.append("🤖 تولیدشده توسط OptimusAI — لایه گزارش مدیریتی")
    return "\n".join(lines)

def send_mgmt_card(api_base, chat_id):
    """خروجی اصلی دکمه: گزارش تحلیلی نوشتاری (نه لیست خام)."""
    import requests
    r = latest_mgmt_report()
    if not r["json"]:
        requests.post(api_base + "/sendMessage",
                      data={"chat_id": chat_id,
                            "text": "⚠️ هنوز گزارش تحلیل مدیریتی تولید نشده است."},
                      timeout=60)
        return
    text = _build_narrative(r)
    # پاراف زیاد را بشکن (محدودیت طول پیام بله)
    while len(text) > 3800:
        cut = text.rfind("\n", 0, 3800)
        part, text = text[:cut], text[cut+1:]
        requests.post(api_base + "/sendMessage",
                      data={"chat_id": chat_id, "text": part}, timeout=60)
    requests.post(api_base + "/sendMessage",
                  data={"chat_id": chat_id, "text": text}, timeout=60)

def send_mgmt_files(api_base, chat_id):
    """ارسال PDF گزارش مدیریتی (در صورت وجود)."""
    import requests
    r = latest_mgmt_report()
    base = os.path.join(BASE_DIR, "output", "base_share")
    pdfs = sorted(glob.glob(os.path.join(base, "management_analysis_report*.pdf")))
    if not r["json"] or not pdfs:
        requests.post(api_base + "/sendMessage",
                      data={"chat_id": chat_id,
                            "text": "⚠️ فایل PDF گزارش مدیریتی موجود نیست."},
                      timeout=60)
        return
    cap = "📊 گزارش تحلیل مدیریتی | جلسه {j}".format(j=r["jalali"])
    with open(pdfs[-1], "rb") as f:
        requests.post(api_base + "/sendDocument",
                      data={"chat_id": chat_id, "caption": cap},
                      files={"document": (os.path.basename(pdfs[-1]), f)},
                      timeout=120)
