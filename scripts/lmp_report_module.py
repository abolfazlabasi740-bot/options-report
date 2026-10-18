# -*- coding: utf-8 -*-
"""ماژول گزارش فرصت‌های اختیار — قابل تزریق در هر بات بله موجود"""
import json, os, glob

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORT_DIR = os.path.join(BASE_DIR, "output", "reports", "lmp")

def latest_reports():
    """آخرین سه‌گانه گزارش LMP (json/xlsx/pdf) + متادیتا"""
    j = sorted(glob.glob(os.path.join(REPORT_DIR, "lmp_*.json")))
    out = {"json": j[-1] if j else None}
    if out["json"]:
        stem = out["json"][:-5]
        for ext in ("xlsx", "pdf"):
            if os.path.exists(stem + "." + ext):
                out[ext] = stem + "." + ext
        try:
            with open(out["json"], encoding="utf-8") as f:
                d = json.load(f)
            out["ts"] = d.get("timestamp", "—")
            out["opps"] = d.get("opportunities", "—")
            out["market_open"] = d.get("market_open")
        except Exception:
            out["ts"], out["opps"] = "—", "—"
    return out

def lmp_button_row():
    """ردیف دکمه شیشه‌ای برای ادغام در منوی موجود بات"""
    return [{"text": "🎯 فرصت‌های اختیار معامله",
             "callback_data": "send_latest_lmp"},
            {"text": "📊 تحلیل مدیریتی",
             "callback_data": "send_latest_mgmt"}]

def lmp_status_caption():
    r = latest_reports()
    src = "🟢 داده زنده" if r.get("market_open") else "📌 داده آخرین جلسه (fallback)"
    return "🕒 آخرین اسکن: {ts}\n🎯 فرصت‌ها: {opps} | {src}".format(
        ts=r.get("ts", "—"), opps=r.get("opps", "—"), src=src)

def send_lmp_files(api_base, chat_id):
    """ارسال PDF سپس Excel آخرین گزارش.
    api_base = رشته کامل آدرس بات، مثل: https://api.bale.ai/bot<TOKEN>"""
    import requests
    r = latest_reports()
    if not r.get("json"):
        requests.post(api_base + "/sendMessage",
                      data={"chat_id": chat_id,
                            "text": "⚠️ هنوز گزارش LMP تولید نشده است."},
                      timeout=60)
        return []
    cap = "📊 گزارش فرصت‌های اختیار | {ts} | فرصت: {opps}".format(
        ts=r["ts"], opps=r["opps"])
    sent = []
    for ext in ("pdf", "xlsx"):
        p = r.get(ext)
        if p:
            with open(p, "rb") as f:
                requests.post(api_base + "/sendDocument",
                              data={"chat_id": chat_id,
                                    "caption": cap if ext == "pdf" else ""},
                              files={"document": (os.path.basename(p), f)},
                              timeout=120)
            sent.append(ext)
    if not sent:
        requests.post(api_base + "/sendMessage",
                      data={"chat_id": chat_id,
                            "text": "ℹ️ فقط JSON موجود است (" + r["ts"] +
                                    ") — خروجی PDF/Excel هنوز ساخته نشده."},
                      timeout=60)
    return sent


def send_lmp_cards(api_base, chat_id):
    """ارسال کارت‌های متنی فرصت‌های اختیار (خروجی اصلی دکمه)."""
    import requests
    try:
        from lmp_cards import build_cards
    except ImportError:
        import importlib.util as _ilu
        _p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lmp_cards.py")
        _spec = _ilu.spec_from_file_location("lmp_cards", _p)
        _mod = _ilu.module_from_spec(_spec)
        _spec.loader.exec_module(_mod)
        build_cards = _mod.build_cards
    parts, ok = build_cards()
    if isinstance(parts, str):
        parts = [parts]
    n = len(parts)
    for i, chunk in enumerate(parts, 1):
        text = (("(%d/%d)\n" % (i, n)) + chunk) if n > 1 else chunk
        try:
            r = requests.post(api_base + "/sendMessage",
                              data={"chat_id": chat_id, "text": text}, timeout=60)
            r.raise_for_status()
        except Exception as exc:
            try:
                requests.post(api_base + "/sendMessage",
                              data={"chat_id": chat_id,
                                    "text": "LMP_CARD_FAIL(%d): %s" % (i, exc)},
                              timeout=30)
            except Exception:
                pass
    return ok
