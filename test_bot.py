import requests

try:
    env = {}
    with open(".env", "r") as f:
        for line in f:
            if "=" in line and not line.startswith("#"):
                k, v = line.strip().split("=", 1)
                env[k] = v

    token = env.get("BALE_BOT_TOKEN")
    chat_id = env.get("BALE_CHAT_ID")

    if not token or not chat_id:
        print("خطا: توکن یا Chat ID در فایل .env یافت نشد.")
    else:
        url = f"https://tapi.bale.ai/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": "تست اتصال از سیستم Options"}
        response = requests.post(url, json=payload, timeout=10)
        print("Response:", response.status_code)
        print(response.text)

except Exception as e:
    print("System Error:", e)
