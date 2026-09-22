"""Shared Bale transport; importing it never sends a message."""
import requests


def split_message(text, limit=3500):
    """Keep report cards intact when possible; otherwise split at newlines."""
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


def send_message(token, chat_id, text, return_receipts=False):
    if not token or not str(chat_id).strip():
        raise ValueError("BALE_BOT_TOKEN و BALE_CHAT_ID باید تنظیم شوند")
    chunks = split_message(text)
    receipts = []
    for chunk in chunks:
        try:
            response = requests.post(
                f"https://tapi.bale.ai/bot{token}/sendMessage",
                data={"chat_id": chat_id, "text": chunk}, timeout=30,
            )
            response.raise_for_status()
            payload = response.json()
            if not payload.get("ok"):
                raise ValueError("Bale rejected message")
            if return_receipts:
                result = payload.get("result") or {}
                receipts.append({
                    "message_id": result.get("message_id"),
                    "chat_id": (result.get("chat") or {}).get("id"),
                })
        except requests.HTTPError as exc:
            status = getattr(exc.response, "status_code", None)
            raise RuntimeError(
                f"ارسال بله ناموفق بود؛ HTTP_STATUS={status or "UNKNOWN"}؛ احتمال ارسال بخشی از گزارش وجود دارد"
            ) from None
        except requests.RequestException as exc:
            reason = type(exc).__name__
            raise RuntimeError(
                f"ارسال بله ناموفق بود؛ NETWORK_ERROR={reason}؛ احتمال ارسال بخشی از گزارش وجود دارد"
            ) from None
        except ValueError as exc:
            reason = "API_REJECTED" if str(exc) == "Bale rejected message" else "INVALID_RESPONSE"
            raise RuntimeError(
                f"ارسال بله ناموفق بود؛ REASON={reason}؛ احتمال ارسال بخشی از گزارش وجود دارد"
            ) from None
    return receipts if return_receipts else len(chunks)
