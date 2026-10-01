"""Shared Bale transport with no third-party HTTP dependency."""
from __future__ import annotations

import json
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


def send_message(token, chat_id, text, return_receipts=False, reply_markup=None):
    if not token or not str(chat_id).strip():
        raise ValueError("BALE_BOT_TOKEN و BALE_CHAT_ID باید تنظیم شوند")
    chunks = split_message(text)
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
