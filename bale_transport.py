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


def send_message(token, chat_id, text):
    if not token or not str(chat_id).strip():
        raise ValueError("BALE_BOT_TOKEN و BALE_CHAT_ID باید تنظیم شوند")
    chunks = split_message(text)
    for chunk in chunks:
        try:
            response = requests.post(
                f"https://tapi.bale.ai/bot{token}/sendMessage",
                data={"chat_id": chat_id, "text": chunk}, timeout=30,
            )
            response.raise_for_status()
            if not response.json().get("ok"):
                raise ValueError("Bale rejected message")
        except (requests.RequestException, ValueError):
            raise RuntimeError("ارسال بله ناموفق بود؛ احتمال ارسال بخشی از گزارش وجود دارد") from None
    return len(chunks)
