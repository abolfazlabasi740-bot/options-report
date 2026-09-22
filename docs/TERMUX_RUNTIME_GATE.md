# Termux Runtime Verification Gate

Run `python3 runtime_verification.py` from the active project directory on Termux.

The script checks critical file presence, Python compilation, repository SHA when available, presence-only environment flags, and the latest audit-integrity artifact when available.

It never writes secret values. It records only booleans for environment variables such as BALE_BOT_TOKEN and BALE_CHAT_ID.

PASS means the local verification checks succeeded. It is runtime evidence only after the script is actually executed on the target Termux instance.

## Gate 6 One-Shot Delivery Evidence

پس از اجرای موفق Report Engine روی Termux، برای ثبت Evidence واقعی ارسال همان گزارش به Bale:

```bash
cd ~/OptimusAI_V41_LIVE
python3 report_engine.py
python3 runtime_verification.py
python3 bale_runtime_verification.py
cat output/bale_delivery_verification.json
```

این ابزار هیچ تحلیل جدیدی انجام نمی‌دهد و `output/latest_report.txt` تولیدشده توسط Report Engine را مستقیماً ارسال می‌کند. Evidence شامل SHA-256 گزارش، SHA-256 منبع، زمان تولید، وضعیت Audit و تعداد Chunkهای ارسال‌شده است و Token را ثبت نمی‌کند.

موفقیت این ابزار به‌علاوه اجرای واقعی Listener یا ارسال مستقیم گزارش، Evidence موردنیاز برای Gate 6 را قابل ثبت می‌کند؛ GitHub CI به‌تنهایی جای Runtime Evidence را نمی‌گیرد.
