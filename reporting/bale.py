#!/usr/bin/env python3
"""
bale.py — ماژول مشترک توزیع گزارش در Bale
بر اساس Master_Project_Book_v3.docx بخش ۱۵
ارسال فقط پس از تأیید validation_pass و run_id معتبر.
"""
import json, os, hashlib
from datetime import datetime, timezone, timedelta

IRST = timezone(timedelta(hours=3, minutes=30))


class BaleClient:
    """کلاینت مشترک ارسال به بله — همه گزارش‌ها از همین استفاده می‌کنند"""

    def __init__(self, token_path: str = "config/bale_token.json",
                 chat_id: str = ""):
        self.chat_id = chat_id
        self.token = ""
        self.enabled = False
        if os.path.exists(token_path):
            try:
                with open(token_path, encoding="utf-8") as f:
                    cfg = json.load(f)
                self.token   = cfg.get("token", "")
                self.chat_id = chat_id or cfg.get("chat_id", "")
                self.enabled = bool(self.token and self.chat_id)
            except Exception:
                self.enabled = False

    def _gate(self, json_data: dict) -> bool:
        """درگاه کنترلی — فقط اگر validation_pass=True و run_id موجود باشد"""
        if not json_data.get("validation_pass"):
            return False
        if not json_data.get("run_id"):
            return False
        return True

    def build_message(self, json_data: dict, max_rows: int = 10) -> str:
        """ساخت پیام مارک‌داون بهینه برای پیام‌رسان"""
        if not self._gate(json_data):
            return None

        lines = [
            f"📊 {json_data.get('report_name', 'گزارش')}",
            f"🆔 {json_data.get('run_id', '')}",
            f"🕐 {json_data.get('timestamp', '')}",
            f"📈 سناریو: {json_data.get('scenario', '—')}",
            f"💵 مبنای قیمت: {json_data.get('price_basis', '—')}",
            f"{'🟢 بازار باز' if json_data.get('market_open') else '🔴 بازار بسته'}",
            f"",
            f"✅ فرصت‌ها: {json_data.get('opportunities', 0)}",
            f"❌ نگاشت‌نشده: {json_data.get('total_calls', 0) - json_data.get('opportunities', 0)}",
        ]

        results = json_data.get("results", [])[:max_rows]
        if results:
            lines.append("")
            lines.append("🎯 فرصت‌های برتر:")
            for i, r in enumerate(results, 1):
                sym = r.get("symbol", r.get("نماد", "—"))
                score = r.get("score", r.get("امتیاز", "—"))
                status = r.get("status", r.get("وضعیت", "—"))
                lines.append(f"{i}. {sym} | امتیاز: {score} | {status}")

        if json_data.get("flags"):
            lines.append("")
            lines.append("⚠️ هشدارها:")
            for f in json_data["flags"][:3]:
                lines.append(f"• {f}")

        lines.append("")
        lines.append("OptimusAI V41")
        return "\n".join(lines)

    def send(self, json_data: dict, max_rows: int = 10) -> dict:
        """ارسال پیام به بله — خروجی dict با وضعیت"""
        msg = self.build_message(json_data, max_rows)
        if msg is None:
            return {"sent": False,
                    "reason": "validation_pass=False یا run_id نامعتبر"}

        if not self.enabled:
            return {"sent": False,
                    "reason": "Bale token/chat_id پیکربندی نشده",
                    "message_preview": msg[:200]}

        # در محیط Termux: از curl یا bale-bot استفاده شود
        # اینجا placeholder قرار داده‌ایم؛ اجرای واقعی به محیط وابسته است
        try:
            import subprocess
            url = f"https://tapi.bale.ai/bot{self.token}/sendMessage"
            result = subprocess.run(
                ["curl", "-s", "-X", "POST", url,
                 "-H", "Content-Type: application/json",
                 "-d", json.dumps({"chat_id": self.chat_id, "text": msg})],
                capture_output=True, text=True, timeout=30
            )
            resp = json.loads(result.stdout) if result.stdout else {}
            ok = resp.get("ok", False)
            return {"sent": ok,
                    "response": resp,
                    "run_id": json_data.get("run_id", "")}
        except Exception as e:
            return {"sent": False, "error": str(e),
                    "message_preview": msg[:200]}
