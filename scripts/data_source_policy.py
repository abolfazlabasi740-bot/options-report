# -*- coding: utf-8 -*-
"""سیاست منبع داده — نسخه V4 (مصوبه CHG-DATA-001)
TSETMC = منبع حاکم | Optionschool24 = مکمل/Schema | قرنطینه به‌جای حذف
"""
PRIMARY_SOURCE = "TSETMC"
FALLBACK_SOURCE = "Optionschool24"
POLICY_VERSION = "V4"
CHANGE_ID = "CHG-DATA-001"

# رژیم دوگانه
MARKET_OPEN = ("08:45", "12:30")
LIVE_TTL_MINUTES = 30

# قواعد قرنطینه (بدون حذف)
QUARANTINE_STALE_BASE = ["7960"]      # مبانی کهنه شناخته‌شده (ضملت پیش از افزایش سرمایه)
QUARANTINE_MIN_PREMIUM = 10           # پرمیوم زیر ۱۰ ریال = کف/بی‌معامله

def resolve_conflict(tsetmc_value, optionschool_value):
    """در تعارض، داده TSETMC حاکم است."""
    if tsetmc_value is not None:
        return tsetmc_value, PRIMARY_SOURCE
    return optionschool_value, FALLBACK_SOURCE

def needs_quarantine(base, premium):
    """تشخیص قرنطینه به‌جای حذف."""
    if str(base) in QUARANTINE_STALE_BASE:
        return True, f"مبنای کهنه {base} — ناسازگار با قیمت رسمی TSETMC (CHG-DATA-001/بند۳)"
    if premium is not None and premium < QUARANTINE_MIN_PREMIUM:
        return True, f"پرمیوم {premium} زیر کف {QUARANTINE_MIN_PREMIUM} — نقدشوندگی صفر"
    return False, ""


# ============================================================
# پچ تقویم (CHG-DATA-001 ادامه): رژیم بر اساس ساعت + روز هفته + تعطیلات
# بازار ایران: شنبه تا چهارشنبه | معامله ۸:۴۵ تا ۱۲:۳۰ | پنجشنبه/جمعه تعطیل
# ============================================================
IRAN_HOLIDAYS = set()  # تعطیلات رسمی به صورت "YYYY-MM-DD" — قابل بهروزرسانی

def get_data_mode(now=None):
    """LIVE فقط وقتی بازار واقعاً باز است؛ در غیر این صورت EOD."""
    import datetime as _dt
    tz = _dt.timezone(_dt.timedelta(hours=3, minutes=30))  # Asia/Tehran
    now = now or _dt.datetime.now(tz)
    if now.tzinfo is None:
        now = now.replace(tzinfo=tz)
    if now.weekday() in (3, 4):  # پنجشنبه=3، جمعه=4 (شنبه=5 و یکشنبه=6 روز معاملهاند)
        return "EOD", "تعطیل هفتگی — بازار بسته"
    if now.date().isoformat() in IRAN_HOLIDAYS:
        return "EOD", "تعطیل رسمی — بازار بسته"
    open_t  = now.replace(hour=8,  minute=45, second=0, microsecond=0)
    close_t = now.replace(hour=12, minute=30, second=0, microsecond=0)
    if open_t <= now <= close_t:
        return "LIVE", "ساعات معاملاتی — بازار باز"
    return "EOD", "خارج از ساعات معامله (%s تهران)" % now.strftime("%H:%M")
