from pathlib import Path
import os
import requests

ROOT = Path(__file__).resolve().parent
REPORT = ROOT / "output" / "latest_report.txt"

TOKEN = os.getenv("BALE_BOT_TOKEN", "").strip()
CHAT_ID = os.getenv("BALE_CHAT_ID", "").strip()

if not TOKEN:
    raise RuntimeError("BALE_BOT_TOKEN تنظیم نشده است")

if not REPORT.exists():
    raise RuntimeError("latest_report.txt پیدا نشد")

# اگر Chat ID از قبل تنظیم نشده باشد، آخرین پیام دریافتی را پیدا می‌کنیم.
if not CHAT_ID:
    url = f"https://tapi.bale.ai/bot{TOKEN}/getUpdates"
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    data = r.json()

    updates = data.get("result", [])
    if not updates:
        raise RuntimeError("هیچ پیام دریافتی برای پیدا کردن Chat ID وجود ندارد")

    for update in reversed(updates):
        msg = update.get("message") or update.get("edited_message")
        if msg and msg.get("chat", {}).get("id") is not None:
            CHAT_ID = str(msg["chat"]["id"])
            break

if not CHAT_ID:
    raise RuntimeError("Chat ID پیدا نشد")

text = REPORT.read_text(encoding="utf-8")

url = f"https://tapi.bale.ai/bot{TOKEN}/sendMessage"

# Bale محدودیت طول پیام دارد؛ گزارش را قطعه‌بندی می‌کنیم.
chunks = [text[i:i+3500] for i in range(0, len(text), 3500)]

for i, chunk in enumerate(chunks, 1):
    payload = {
        "chat_id": CHAT_ID,
        "text": chunk
    }

    r = requests.post(url, data=payload, timeout=20)
    r.raise_for_status()

    result = r.json()
    if not result.get("ok"):
        raise RuntimeError(f"Bale error: {result}")

    print(f"SENT {i}/{len(chunks)}")

print("BALE_SEND_OK")
print("CHAT_ID =", CHAT_ID)
print("CHUNKS =", len(chunks))
