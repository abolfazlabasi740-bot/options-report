```python
import time
import requests

TOKEN = "1442176990:2mQnmSfsH-r6v8bwQpqH6pc6i_KV4VbS4nA"
BASE_URL = f"https://tapi.bale.ai/bot{TOKEN}/"
CHAT_ID = 1442176990

def send_message(chat_id, text):
    requests.post(
        BASE_URL + "sendMessage",
        json={"chat_id": chat_id, "text": text},
        timeout=30
    )

def main():
    offset = 0
    print("Bot is running...")

    while True:
        try:
            response = requests.get(
                BASE_URL + "getUpdates",
                params={"offset": offset, "timeout": 25},
                timeout=35
            ).json()

            for update in response.get("result", []):
                offset = update["update_id"] + 1
                message = update.get("message", {})
                chat_id = message.get("chat", {}).get("id")
                text = message.get("text", "")

                if chat_id != CHAT_ID:
                    continue

                if text == "/start":
                    send_message(chat_id, "ربات فعال است.")
                elif text:
                    send_message(chat_id, "پیام دریافت شد.")

        except Exception as error:
            print("Error:", error)
            time.sleep(5)

if __name__ == "__main__":
    main()
```
