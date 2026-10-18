# -*- coding: utf-8 -*-
"""کارت‌ساز فرصت‌های اختیار معامله — خروجی کارتی به‌جای اکسل."""
import json, os, glob, time
from underlying_map import resolve_underlying

REPORT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "output", "reports", "lmp")

MAX_LEN = 3800  # سقف امن هر پیام در بله
SEP = "━━━━━━━━━━━━━━━━━━"

def _fmt(x, nd=0):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return "—"
    return f"{x:,.{nd}f}"

def _latest_urgent():
    files = sorted(glob.glob(os.path.join(REPORT_DIR, "urgent_closing*.json")), reverse=True)
    if not files:
        return None, None
    p = files[0]
    try:
        with open(p, encoding="utf-8") as fh:
            return json.load(fh), os.path.getmtime(p)
    except Exception:
        return None, None

def _is_otm(c):
    try:
        return float(c.get("intrinsic_now") or 0) <= 0
    except (TypeError, ValueError):
        return False

BASE_PLAUSIBLE = {'ملت': 1570.0}  # وبملت تأییدشده  # بعد از ریشه‌یابی: (نمادپایه, قیمت_معتبر) مثلاً ('وبملت', 1570)

def build_cards(max_cards=10, top_by="share_growth_pct_closing"):
    """کارت‌های متنی + سربرگ؛ مرتب‌سازی صعودی رشد لازم سهم."""
    d, mtime = _latest_urgent()
    if not d:
        return ["⚠️ داده‌ای برای ساخت کارت یافت نشد."], False
    cs = d.get("contracts") or []
    if not cs:
        return ["📭 در آخرین اسکن فرصتی ثبت نشد."], True
    def _k(c):
        try:
            return float(c.get(top_by) or 0)
        except (TypeError, ValueError):
            return 0
    total = len(cs)
    cs = sorted(cs, key=_k)[:max_cards]
    date_lbl = d.get("data_date") or (time.strftime("%Y-%m-%d", time.localtime(mtime)) if mtime else "—")
    hdr = (f"🎯 فرصت‌های اختیار معامله ({len(cs)} از {total} قرارداد)\n"
           f"🗓 {date_lbl} | 📌 داده آخرین جلسه (fallback)\n")
    parts, cur = [], hdr
    for c in cs:
        _u = str(c.get('underlying', ''))
        _b = float(c.get('base_closing') or 0)
        _ref = BASE_PLAUSIBLE.get(_u)
        if _ref and abs(_b - _ref) / _ref > 0.05:
            continue  # قرنطینه: پایه با منبع تأییدشده همخوان نیست
        growth_line = (f"📈 رشد لازم سهم: {_fmt(c.get('share_growth_pct_closing'), 2)}٪ | "
                       f"رشد پریمیوم: {_fmt(c.get('premium_growth_pct_closing'), 2)}٪\n"
                       if _is_otm(c) else
                       f"📈 رشد لازم سهم: {_fmt(c.get('share_growth_pct_closing'), 2)}٪ | وضعیت: در سود (ITM)\n")
        card = (f"{SEP}\n"
                f"🎯 {c.get('option_symbol', '—')} — {c.get('underlying', '—')}\n"
                f"💰 اجرا: {_fmt(c.get('strike'))} | پایه (پایانی): {_fmt(c.get('base_closing'))}\n"
                f"📊 پریمیوم: {_fmt(c.get('premium'))} | ذاتی: {_fmt(c.get('intrinsic_now'))}\n"
                f"🛡 حاشیه ایمنی: {_fmt(c.get('safety_margin'), 2)} | سقف فردا: {_fmt(c.get('ceiling_tomorrow'))}\n"
                f"🎯 تخفیف به ارزش ذاتی: {_fmt(max((c.get('intrinsic_now') or 0) - (c.get('premium') or 0), 0))} ریال\n"
                + growth_line +
                f"⏳ مانده: {_fmt(c.get('days_left'))} روز | حجم: {_fmt(c.get('volume'))}")
        if len(cur) + len(card) + 1 > MAX_LEN:
            parts.append(cur.rstrip())
            cur = ""
        cur += card + "\n"
    cur += f"\n⚠️ مبنای محاسبات قیمت پایانی؛ داده جلسه تعطیل (fallback)."
    parts.append(cur)
    return parts, True

if __name__ == "__main__":
    parts, ok = build_cards()
    print(f"[CHUNKS: {len(parts)}]")
    for p in parts:
        print(p)
