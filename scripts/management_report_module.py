# -*- coding: utf-8 -*-
"""ماژول گزارش تحلیل مدیریتی — قابل تزریق در هر بات بله موجود"""
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
            out["ts"] = data.get("data_time_label") or "—"
            out["jalali"] = data.get("latest_history_date_jalali") or "—"
            out["generated_at"] = data.get("generated_at") or "—"
            out["top"] = data.get("top10") or []
            out["status"] = data.get("trade_permission") or "UNKNOWN"
        except Exception:
            out["ts"], out["jalali"], out["top"], out["status"] = "—", "—", [], "PARSE_ERROR"
    else:
        out["ts"], out["jalali"], out["top"], out["status"] = "—", "—", [], "NOT_GENERATED"
    return out

def mgmt_button_row():
    """ردیف دکمه شیشه‌ای تحلیل مدیریتی (مستقل، برای ادغام در هر منو)"""
    return [{"text": "📊 تحلیل مدیریتی",
             "callback_data": "send_latest_mgmt"}]

def mgmt_status_caption():
    r = latest_mgmt_report()
    return "📅 گزارش تحلیل مدیریتی — جلسه {j}\n🕒 داده: {ts} | وضعیت: {st}".format(
        j=r["jalali"], ts=r["ts"], st=r["status"])

def send_mgmt_card(api_base, chat_id):
    """خروجی اصلی دکمه: کارت تحلیل با سربرگ شمسی و ساعت داده (EOD)."""
    import requests
    r = latest_mgmt_report()
    if not r["json"]:
        requests.post(api_base + "/sendMessage",
                      data={"chat_id": chat_id,
                            "text": "⚠️ هنوز گزارش تحلیل مدیریتی تولید نشده است."},
                      timeout=60)
        return
    lines = ["📊 گزارش تحلیل مدیریتی",
             "📅 جلسه: {j}".format(j=r["jalali"]),
             "🕒 داده (EOD): {ts}".format(ts=r["ts"]),
             "—" * 18]
    for i, s in enumerate(r["top"][:10], 1):
        sym = s.get("symbol", "—")
        score = s.get("score", "—")
        rsi = s.get("rsi14", s.get("rsi", "—"))
        lines.append("{i}. {sym} | امتیاز: {sc} | RSI-14: {rsi}".format(
            i=i, sym=sym, sc=score, rsi=rsi))
        if s.get("note"):
            lines.append("   💬 {n}".format(n=s["note"]))
    lines.append("—" * 18)
    lines.append("وضعیت داده: {st} | سیگنال خرید/فروش: NOT_GENERATED".format(st=r["status"]))
    requests.post(api_base + "/sendMessage",
                  data={"chat_id": chat_id, "text": "\n".join(lines)},
                  timeout=60)

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
