
cd ~/options_report

cat << 'EOF' > generate_report.py
import os
import requests
import pandas as pd
from datetime import datetime

EXCEL_URL = "https://s3.optionschool24.com/export/excel?type=1"
LOCAL_FILE = "options_data.xlsx"
HEADERS = {"User-Agent": "Mozilla/5.0"}

def download_data():
    resp = requests.get(EXCEL_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    with open(LOCAL_FILE, "wb") as f:
        f.write(resp.content)

def to_num(x):
    try:
        return float(str(x).replace(",", "").replace("٬", "").replace("٫", "."))
    except (ValueError, TypeError):
        return None

def fmt(x, dec=0):
    if x is None or pd.isna(x):
        return "-"
    s = f"{x:,.{dec}f}"
    return s.replace(",", "٬").replace(".", "٫")

def send_to_bale(text):
    token = os.getenv("BALE_BOT_TOKEN", "").strip()
    chat_id = os.getenv("BALE_CHAT_ID", "").strip()
    if not token or not chat_id:
        print("⚠️ BALE_BOT_TOKEN یا BALE_CHAT_ID تنظیم نشده است.")
        return
    try:
        requests.post(f"https://tapi.bale.ai/bot{token}/sendMessage",
                      json={"chat_id": chat_id, "text": text}, timeout=20)
    except Exception as e:
        print(f"❌ خطای ارسال: {e}")

def process_and_report():
    download_data()
    df = pd.read_excel(LOCAL_FILE)
    df.columns = [str(c).strip() for c in df.columns]

    # فیلتر اهرم حداقل ۳
    df["_lev"] = df["اهرم"].apply(to_num)
    df = df[df["_lev"] >= 3].copy()

    df["_be"]   = df["سر به سر"].apply(to_num)
    df["_und"]  = df["قیمت سهم پایه"].apply(to_num)
    df["_dist"] = df.apply(
        lambda r: (r["_be"] - r["_und"]) / r["_und"] * 100
        if r["_be"] and r["_und"] else None, axis=1)

    # امتیاز V3
    df["_score"] = df.apply(
        lambda r: max(0, 100 - max(0, 2 * (r["_lev"] or 0) - 1)
                      - abs(r["_dist"] or 0) * 1.5), axis=1)

    df = df.sort_values("_score", ascending=False).head(10)

    header = ("📊 رتبه‌بندی برترین قراردادهای اختیار معامله\n\n"
              "پروتکل V3 (منبع: Optionschool24)\n\n"
              "فیلتر: اهرم حداقل ۳\n"
              "━━━━━━━━━━━━━━━━━━\n\n")

    cards = []
    for i, (_, r) in enumerate(df.iterrows(), 1):
        dist = r["_dist"]
        dtxt = f"{'+' if dist > 0 else ''}{fmt(dist, 3)}٪" if dist is not None else "-"
        d = r.get("روزهای تقویمی")
        dd = int(d) if pd.notna(d) else None
        card = (
            f"🔹 {i}. {r['نماد']}\n"
            f"قیمت اعمال: {fmt(to_num(r['قیمت اعمال']))} | آخرین: {fmt(to_num(r['آخرین قیمت']))}\n"
            f"سر‌به‌سر: {fmt(r['_be'])} | پایه: {fmt(r['_und'])}\n"
            f"اهرم: {fmt(r['_lev'], 2)} | فاصله سر‌به‌سر: {dtxt}\n"
            f"سررسید: {r['تاریخ سررسید']} ({dd} روز)\n"
            f"امتیاز: {fmt(r['_score'], 2)}\n"
        )
        cards.append(card)

    full_report = header + "━━━━━━━━━━━━━━━━━━\n\n".join(cards)
    print(full_report)
    send_to_bale(full_report)

if __name__ == "__main__":
    process_and_report()
EOF

git add generate_report.py
git commit -m "Update generate_report with V3 card format"
git push origin main

    
