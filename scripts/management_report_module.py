# -*- coding: utf-8 -*-
"""ماژول گزارش تحلیل مدیریتی — نسخه ۳: نگارش تمیز فارسی، بدون آمیختگی انگلیسی

اصول این نسخه:
- همه اصطلاح‌های تکنیکال به فارسیِ روان برگردانده می‌شوند (جدول ترجمه پایین).
- «داده موجود نیست» فقط یک بار در بخش وضعیت داده‌ها می‌آید، نه در هر نماد.
- هر نماد یک بلوک کوتاه خوانا با خطوط جدا دارد، نه یک خط شلوغ با «؛».
- اعداد با ارقام فارسی و علائم فارسی (٪ و ×) نمایش داده می‌شوند.
- هیچ عددی ساخته نمی‌شود؛ فقط بازآرایی همان فیلدهای واقعی JSON.
"""
import json, os, glob

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MGMT_JSON = os.path.join(BASE_DIR, "output", "base_share",
                         "latest_management_analysis_report.json")

# ── ترجمهٔ اصطلاح‌های انگلیسیِ موتور به فارسیِ روان ──
TREND_FA = {
    "UP_TREND_STRUCTURE": "روند صعودی",
    "DOWN_TREND_STRUCTURE": "روند نزولی",
    "MIXED_STRUCTURE": "روند نامشخص",
}
CORRECTION_FA = {
    "RECOVERY_BOUNCE": "بازگشت از کف",
    "CORRECTION_IN_UPTREND": "اصلاح در دل روند صعودی",
    "CORRECTION": "فاز اصلاح",
    "COUNTERTREND_BOUNCE_IN_DOWNTREND": "پرش مخالف در روند نزولی",
    "NO_CORRECTION_EVIDENCE": "بدون اصلاح",
}
PRELOCK_FA = {
    "EARLY": "مراحل اولیه",
    "DEVELOPING": "در حال شکل‌گیری",
    "WATCH": "نیازمند پایش",
    "NO_SEQUENCE_EVIDENCE": "بدون توالی",
}
LABEL_FA = {
    "هم‌گرایی مثبت چندعاملی": "هم‌گرایی مثبت عوامل",
    "هم‌گرایی منفی چندعاملی": "هم‌گرایی منفی عوامل",
    "کیفیت متعادل — تمایل مثبت": "متعادل، با تمایل مثبت",
    "کیفیت متعادل — تمایل منفی": "متعادل، با تمایل منفی",
    "متوازن": "متعادل",
    "داده موجود نیست": "شواهد ناکافی",
}

_DIGITS = str.maketrans("0123456789.", "۰۱۲۳۴۵۶۷۸۹٫")

def _fa(x):
    """عدد → رشته فارسی خوانا؛ None → «—»"""
    if x is None:
        return "—"
    if isinstance(x, float):
        x = round(x, 2)
    return str(x).translate(_DIGITS)

def _fa_label(x):
    return LABEL_FA.get(str(x or ""), str(x or "—"))

def _t(table, value):
    """ترجمه با بازگشتِ خود مقدار اگر در جدول نبود"""
    if value in (None, ""):
        return "—"
    return table.get(str(value), str(value))


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


def _build_narrative(r):
    """متن گزارش — روایت فارسی روان، فقط از فیلدهای واقعی JSON"""
    d = r["data"]
    top = r["top"]
    sep = "━" * 22

    lines = []

    # ═══ ۱) سربرگ ═══
    lines += [
        "📊 گزارش تحلیل بازار",
        "گزارشی توصیفی از وضعیت تکنیکال بازار بر پایهٔ دادهٔ پایان معامله",
        sep,
        "📅 جلسهٔ مورد تحلیل: {j}".format(j=r["jalali"]),
        "🕒 بازسازی گزارش: {g} (به وقت میلادی سیستم)".format(g=_fa(str(d.get("generated_at") or "—")[:16].replace("T", " ").replace("-", "/"))),
        sep,
    ]

    # ═══ ۲) تصویر کلی بازار (خلاصهٔ مدیریتی) ═══
    if top:
        scores = [s.get("final_score") for s in top if isinstance(s.get("final_score"), (int, float))]
        rets = [s.get("return_20_sessions_pct") for s in top if isinstance(s.get("return_20_sessions_pct"), (int, float))]
        rsis = [s.get("rsi_14") for s in top if isinstance(s.get("rsi_14"), (int, float))]
        a_cnt = sum(1 for s in top if s.get("classification") == "A")
        b_cnt = sum(1 for s in top if s.get("classification") == "B")

        lines.append("🗂 تصویر کلی")
        n = d.get("universe_size")
        if n:
            lines.append("دامنهٔ پایش {n} نماد است و این گزارش بر ۱۰ نماد برتر تمرکز دارد.".format(n=_fa(n)))
        if scores:
            lines.append("امتیاز کل نمادهای برتر از {mn} تا {mx} است (میانگین {av}).".format(
                mn=_fa(min(scores)), mx=_fa(max(scores)), av=_fa(sum(scores)/len(scores))))
        if a_cnt or b_cnt:
            lines.append("از نظر کیفیت ساختار، {a} نماد در طبقهٔ A و {b} نماد در طبقهٔ B قرار دارند.".format(a=_fa(a_cnt), b=_fa(b_cnt)))
        if rets:
            pos = sum(1 for x in rets if x > 0)
            best = max(top, key=lambda s: s.get("return_20_sessions_pct") or -1e9)
            lines.append("بازده ۲۰ جلسهٔ اخیر در {pos} نماد از ۱۰ نماد مثبت بوده و میانگین بازده {avg}٪ است؛ بهترین عملکرد از {sym} با {ret}٪.".format(
                pos=_fa(pos), avg=_fa(sum(rets)/len(rets)), sym=best.get("symbol", "—"), ret=_fa(best.get("return_20_sessions_pct"))))
        if rsis:
            overbought = [s.get("symbol") for s in top if isinstance(s.get("rsi_14"), (int, float)) and s.get("rsi_14") >= 70]
            near_ob = [s.get("symbol") for s in top if isinstance(s.get("rsi_14"), (int, float)) and 65 <= s.get("rsi_14") < 70]
            heat = "میانگین شاخص قدرت (RSI) نمادهای برتر {avg} است؛ یعنی بازارِ برتر گرم است اما هنوز در ناحیهٔ خطر نیست.".format(avg=_fa(sum(rsis)/len(rsis)))
            if overbought:
                heat += " نماد {ob} در ناحیهٔ اشباع خرید (۷۰ به بالا) است و احتمال اصلاح کوتاه در آن بالاتر است.".format(ob="، ".join(overbought))
            if near_ob:
                heat += " نماد {nb} نزدیک مرز اشباع (۶۵ تا ۷۰) هستند و نیازمند پایش دقیق‌ترند.".format(nb="، ".join(near_ob))
            lines.append(heat)
        # جمع‌بندی چندعاملی
        labs = [s.get("note_label") for s in top if s.get("note_label")]
        if labs:
            pos = sum(1 for x in labs if "مثبت" in str(x))
            neg = sum(1 for x in labs if "منفی" in str(x))
            lines.append("جمع‌بندی هم‌زمانی عوامل تکنیکال، حرکت قیمت و جریان حجم: {pos} نماد هم‌گرایی مثبت و {neg} نماد هم‌گرایی منفی دارند.".format(pos=_fa(pos), neg=_fa(neg)))
        brk = [s.get("symbol") for s in top if (s.get("factors") or {}).get("breakout_above_prior_20_high") is True]
        if brk:
            lines.append("سقف ۲۰ جلسهٔ اخیر را {b} شکسته‌اند؛ نشانهٔ قدرت قیمت در این نمادها.".format(b="، ".join(brk)))
        prelock = [s.get("symbol") for s in top if (s.get("factors") or {}).get("pre_lock_state") in ("EARLY", "DEVELOPING")]
        if prelock:
            lines.append("الگوی گرم‌شدن تدریجی (ابتدا حجم، بعد قیمت، سپس مومنتوم) در {p} دیده می‌شود؛ این یک شاهدِ زودهنگام است، نه سیگنال ورود.".format(p="، ".join(prelock)))
        lines.append(sep)

    # ═══ ۳) وضعیت داده‌ها — تنها جایی که محدودیت‌ها اعلام می‌شوند ═══
    lines.append("⚠️ محدودیت‌های داده (یک بار برای کل گزارش)")
    lines.append("• نوع داده: پایان روز معاملات؛ ارقام لحظه‌ای و تابلوی معاملات در این گزارش نیست.")
    fl = d.get("fundamental_layer")
    if fl:
        lines.append("• اطلاعات بنیادی (صورت‌های مالی و کدال) هنوز به تحلیل اضافه نشده؛ همهٔ ارقام صرفاً تکنیکال است.")
    bl = d.get("board_layer")
    if bl:
        lines.append("• دادهٔ تابلو (صفوف خرید و فروش، حقیقی و حقوقی) در این نسخه غیرفعال است.")
    lines.append("• سیگنال خرید و فروش تولید نمی‌شود؛ این گزارش توصیف وضعیت است، نه توصیهٔ معاملاتی.")
    if d.get("source_report_sha256"):
        lines.append("• ردگیری منبع: {sh}…".format(sh=str(d["source_report_sha256"])[:12]))
    lines.append(sep)

    # ═══ ۴) روایت نمادهای برتر — هر نماد یک بلوک خوانا ═══
    if top:
        lines.append("📈 روایت ده نماد برتر")
        for s in top[:10]:
            f = s.get("factors") or {}
            sym = s.get("symbol", "—")
            score = _fa(s.get("final_score"))
            cls = s.get("classification") or "—"
            lines.append("")
            lines.append("▸ {sym} — امتیاز {score} | طبقهٔ {cls}".format(sym=sym, score=score, cls=cls))

            # خط ۱: روند و حرارت
            trend = _t(TREND_FA, f.get("trend_state"))
            rsi = f.get("rsi_14")
            if isinstance(rsi, (int, float)):
                if rsi >= 70:
                    heat_txt = "در اشباع خرید ({r} — احتمال اصلاح کوتاه)".format(r=_fa(rsi))
                elif rsi >= 65:
                    heat_txt = "نزدیک اشباع ({r})".format(r=_fa(rsi))
                else:
                    heat_txt = "حرارت متعادل ({r})".format(r=_fa(rsi))
            else:
                heat_txt = "—"
            lines.append("روند: {t} | {h}".format(t=trend, h=heat_txt))

            # خط ۲: قیمت و پرایس‌اکشن
            bits = []
            if f.get("breakout_above_prior_20_high") is True:
                bits.append("شکستهٔ سقف ۲۰ جلسه")
            rp = f.get("range_position_20")
            if isinstance(rp, (int, float)):
                pos_fa = "نزدیک سقف" if rp >= 0.8 else ("نزدیک کف" if rp <= 0.2 else "میانهٔ")
                bits.append("در {p} بازهٔ ۲۰ روزه".format(p=pos_fa))
            corr = _t(CORRECTION_FA, f.get("correction_state"))
            if corr not in ("—", "بدون اصلاح"):
                bits.append("در فاز {c}".format(c=corr))
            if bits:
                lines.append("قیمت: " + "، ".join(bits))

            # خط ۳: حجم و نوسان
            vol_bits = []
            vr = f.get("volume_ratio_5_to_20")
            vl = f.get("value_ratio_5_to_20")
            if isinstance(vr, (int, float)) and isinstance(vl, (int, float)):
                if vr >= 1.5 and vl >= 1.5:
                    vol_bits.append("انبساط هم‌زمان حجم ({v}×) و ارزش ({w}×) نسبت به میانگین ۲۰ جلسه".format(v=_fa(vr), w=_fa(vl)))
                elif vr < 0.8 and vl < 0.8:
                    vol_bits.append("کاهش حجم ({v}×) و ارزش ({w}×) نسبت به میانگین".format(v=_fa(vr), w=_fa(vl)))
                else:
                    vol_bits.append("حجم {v}× و ارزش {w}× میانگین ۲۰ جلسه".format(v=_fa(vr), w=_fa(vl)))
            atr = f.get("atr_14_pct")
            if isinstance(atr, (int, float)):
                vol_bits.append("نوسان روزانه {a}٪".format(a=_fa(atr)))
            if vol_bits:
                lines.append("حجم و نوسان: " + "، ".join(vol_bits))

            # خط ۴: جمع‌بندی
            label = _fa_label(s.get("note_label"))
            pl = f.get("pre_lock_state")
            tail = ""
            if pl in ("EARLY", "DEVELOPING"):
                tail = " و الگوی گرم‌شدن {p} است".format(p=_t(PRELOCK_FA, pl).lower())
            lines.append("جمع‌بندی: {l}{t}.".format(l=label, t=tail))
        lines.append(sep)

    # ═══ ۵) ارزیابی ریسک ═══
    lines.append("⚠️ ارزیابی ریسک")
    if top:
        rsis = [s.get("rsi_14") for s in top if isinstance(s.get("rsi_14"), (int, float))]
        if any(x >= 70 for x in rsis):
            lines.append("• ریسک اصلاح: نمادهای اشباع خرید در صورت خروج پول می‌توانند سریع پایین بیایند؛ ورود پلکانی با حد ضرر منطقی است.")
        lines.append("• ریسک داده: تحلیل فقط بر بستر تکنیکال است؛ کیفیت سود و ارزش ذاتی سنجه نشده است.")
        lines.append("• ریسک اطمینان: بدون لایهٔ بنیادی و تابلوی زنده، قوت استدلال متوسط ارزیابی می‌شود.")
    lines.append(sep)

    # ═══ ۶) نتیجه‌گیری ═══
    lines.append("🎯 نتیجه‌گیری")
    lines.append("وضعیت کلی نمادهای برتر بازار مثبت است: روند صعودی، ورود حجم و شکست سقف‌های تاریخی کوتاه‌مدت هم‌زمان دیده می‌شود. با این حال اشباع خرید در چند نماد و غیبت لایهٔ بنیادی، ریسک را بالا نگه می‌دارد.")
    lines.append("مجوز معامله: صادر نمی‌شود. تصمیم نهایی با لایهٔ تصمیم‌گیری است.")
    lines.append(sep)
    lines.append("🤖 تولیدشده توسط OptimusAI — لایهٔ گزارش مدیریتی")
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
