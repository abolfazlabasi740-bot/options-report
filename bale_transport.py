"""Shared Bale transport with no third-party HTTP dependency."""
from __future__ import annotations

import json
import mimetypes
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def split_message(text, limit=3500):
    if limit <= 0:
        raise ValueError("limit must be positive")
    chunks, current = [], ""
    for index, section in enumerate(text.split("🔹 ")):
        if index:
            section = "🔹 " + section
        if current and len(current) + len(section) > limit:
            chunks.append(current)
            current = ""
        while len(section) > limit:
            cut = section.rfind("\n", 0, limit)
            cut = cut + 1 if cut >= 0 else limit
            chunks.append(section[:cut])
            section = section[cut:]
        current += section
    if current:
        chunks.append(current)
    return chunks



def _gregorian_to_jalali(gy, gm, gd):
    g_days = [31,28,31,30,31,30,31,31,30,31,30,31]
    j_days = [31,31,31,31,31,31,30,30,30,30,30,29]
    gy2, gm2, gd2 = gy - 1600, gm - 1, gd - 1
    day_no = 365 * gy2 + (gy2+3)//4 - (gy2+99)//100 + (gy2+399)//400
    for i in range(gm2):
        day_no += g_days[i]
    if gm2 > 1 and ((gy % 4 == 0 and gy % 100 != 0) or gy % 400 == 0):
        day_no += 1
    day_no += gd2
    j_no = day_no - 79
    j_np = j_no // 12053
    j_no %= 12053
    jy = 979 + 33*j_np + 4*(j_no//1461)
    j_no %= 1461
    if j_no >= 366:
        jy += (j_no-1)//365
        j_no = (j_no-1)%365
    i = 0
    while i < 11 and j_no >= j_days[i]:
        j_no -= j_days[i]
        i += 1
    return jy, i+1, j_no+1


def _with_report_timestamp_button(reply_markup=None):
    markup = dict(reply_markup) if isinstance(reply_markup, dict) else {}

    # Reply keyboards cannot be combined with inline keyboards.
    if "keyboard" in markup and "inline_keyboard" not in markup:
        return reply_markup

    now = datetime.now(ZoneInfo("Asia/Tehran"))
    jy, jm, jd = _gregorian_to_jalali(now.year, now.month, now.day)
    digits = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
    date_text = f"{jy:04d}/{jm:02d}/{jd:02d}".translate(digits)
    time_text = now.strftime("%H:%M").translate(digits)
    row = [{
        "text": f"📅 {date_text} | 🕒 {time_text}",
        "callback_data": "report_timestamp_info",
    }]
    markup["inline_keyboard"] = [row, *(markup.get("inline_keyboard") or [])]
    return markup



def _gregorian_to_jalali(gy, gm, gd):
    g_days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    j_days_in_month = [31, 31, 31, 31, 31, 31, 30, 30, 30, 30, 30, 29]
    gy2 = gy + 1 if gm > 2 else gy
    days = (
        365 * gy
        + (gy2 + 3) // 4
        - (gy2 + 99) // 100
        + (gy2 + 399) // 400
        - 80
        + gd
    )
    for i, dim in enumerate(g_days_in_month):
        if gm <= i + 1:
            break
        days += dim
    gy_prime = gy - 621
    j_day_no = days - 1
    j_np = j_day_no // 12053
    j_day_no %= 12053
    jy = 979 + 33 * j_np + 4 * (j_day_no // 1461)
    j_day_no %= 1461
    if j_day_no >= 366:
        jy += (j_day_no - 1) // 365
        j_day_no = (j_day_no - 1) % 365
    for i, dim in enumerate(j_days_in_month):
        if j_day_no < dim:
            break
        j_day_no -= dim
    return jy, i + 1, j_day_no + 1

def _get_tehran_shamsi_header():
    from datetime import datetime, timezone, timedelta
    tehran_tz = timezone(timedelta(hours=3, minutes=30))
    now = datetime.now(tehran_tz)
    jy, jm, jd = _gregorian_to_jalali(now.year, now.month, now.day)
    return f"🗓 تاریخ: {jy:04d}/{jm:02d}/{jd:02d}\n🕒 ساعت: {now.strftime('%H:%M:%S')}\n\n"

def send_message(token, chat_id, text, return_receipts=False, reply_markup=None):
    if text and not str(text).startswith("🗓 تاریخ:"):
        text = _get_tehran_shamsi_header() + str(text)
    if not token or not str(chat_id).strip():
        raise ValueError("BALE_BOT_TOKEN و BALE_CHAT_ID باید تنظیم شوند")
    chunks = split_message(text)
    reply_markup = _with_report_timestamp_button(reply_markup)
    receipts = []
    for chunk in chunks:
        payload = {"chat_id": chat_id, "text": chunk}
        if reply_markup:
            payload["reply_markup"] = json.dumps(reply_markup, ensure_ascii=False)
        request = Request(
            f"https://tapi.bale.ai/bot{token}/sendMessage",
            data=urlencode(payload).encode("utf-8"),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=30) as response:
                raw = response.read().decode("utf-8")
                status = getattr(response, "status", 200)
            if status < 200 or status >= 300:
                raise RuntimeError(f"ارسال بله ناموفق بود؛ HTTP_STATUS={status}")
            result = json.loads(raw)
            if not result.get("ok"):
                raise RuntimeError("ارسال بله ناموفق بود؛ REASON=API_REJECTED")
            if return_receipts:
                item = result.get("result") or {}
                receipts.append({
                    "message_id": item.get("message_id"),
                    "chat_id": (item.get("chat") or {}).get("id"),
                })
        except HTTPError as exc:
            raise RuntimeError(
                f"ارسال بله ناموفق بود؛ HTTP_STATUS={exc.code}؛ احتمال ارسال بخشی از گزارش وجود دارد"
            ) from None
        except URLError as exc:
            raise RuntimeError(
                f"ارسال بله ناموفق بود؛ NETWORK_ERROR={type(exc.reason).__name__ if exc.reason else 'URLError'}؛ احتمال ارسال بخشی از گزارش وجود دارد"
            ) from None
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise RuntimeError("ارسال بله ناموفق بود؛ REASON=INVALID_RESPONSE") from None
    return receipts if return_receipts else len(chunks)


def _boundary():
    """Return a multipart boundary string (no external uuid dependency)."""
    import os
    return "bale-" + os.urandom(16).hex()


def send_document(token, chat_id, file_path, caption=None):
    """Send a local file as a Bale document via multipart/form-data.

    Returns the Bale message_id of the sent document, or raises RuntimeError on
    any failure. Uses only the standard library.
    """
    if not token or not str(chat_id).strip():
        raise ValueError("BALE_BOT_TOKEN و BALE_CHAT_ID باید تنظیم شوند")
    path = Path(file_path)
    if not path.exists() or not path.is_file():
        raise RuntimeError(f"فایل برای ارسال پیدا نشد: {path}")

    boundary = _boundary()
    filename = path.name
    mime = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    with path.open("rb") as handle:
        file_bytes = handle.read()

    parts = []
    # chat_id field
    parts.append(f"--{boundary}".encode("utf-8"))
    parts.append(
        b'Content-Disposition: form-data; name="chat_id"'
        + b"\r\n\r\n" + str(chat_id).encode("utf-8")
    )
    # optional caption field
    if caption:
        parts.append(f"--{boundary}".encode("utf-8"))
        parts.append(
            b'Content-Disposition: form-data; name="caption"'
            + b"\r\n\r\n" + str(caption).encode("utf-8")
        )
    # document file part
    parts.append(f"--{boundary}".encode("utf-8"))
    parts.append(
        f'Content-Disposition: form-data; name="document"; filename="{filename}"'
        .encode("utf-8")
        + b"\r\n" + f"Content-Type: {mime}".encode("utf-8")
        + b"\r\n\r\n"
    )
    parts.append(file_bytes)
    # closing boundary
    parts.append(f"\r\n--{boundary}--\r\n".encode("utf-8"))

    body = b"".join(parts)
    request = Request(
        f"https://tapi.bale.ai/bot{token}/sendDocument",
        data=body,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Content-Length": str(len(body)),
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=60) as response:
            raw = response.read().decode("utf-8")
            status = getattr(response, "status", 200)
        if status < 200 or status >= 300:
            raise RuntimeError(f"ارسال فایل بله ناموفق بود؛ HTTP_STATUS={status}")
        result = json.loads(raw)
        if not result.get("ok"):
            raise RuntimeError("ارسال فایل بله ناموفق بود؛ REASON=API_REJECTED")
        return (result.get("result") or {}).get("message_id")
    except HTTPError as exc:
        raise RuntimeError(
            f"ارسال فایل بله ناموفق بود؛ HTTP_STATUS={exc.code}"
        ) from None
    except URLError as exc:
        raise RuntimeError(
            f"ارسال فایل بله ناموفق بود؛ NETWORK_ERROR={type(exc.reason).__name__ if exc.reason else 'URLError'}"
        ) from None
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise RuntimeError("ارسال فایل بله ناموفق بود؛ REASON=INVALID_RESPONSE") from None
