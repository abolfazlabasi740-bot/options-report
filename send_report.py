#!/usr/bin/env python3
import hashlib
import os
import sys
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"
LAST_HASH_PATH = BASE_DIR / ".last_report_hash"
DEFAULT_REPORT_PATH = BASE_DIR / "output_options_report.md"
CHUNK_SIZE = 3500
BALE_API_URL = "https://tapi.bale.ai/bot{token}/sendMessage"


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def read_report_text(report_path: Path) -> str:
    if not report_path.exists():
        raise FileNotFoundError(f"Report file not found: {report_path}")
    return report_path.read_text(encoding="utf-8")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_last_hash() -> str:
    if LAST_HASH_PATH.exists():
        return LAST_HASH_PATH.read_text(encoding="utf-8").strip()
    return ""


def write_last_hash(value: str) -> None:
    LAST_HASH_PATH.write_text(value + "\n", encoding="utf-8")


def split_chunks(text: str, size: int = CHUNK_SIZE):
    for start in range(0, len(text), size):
        yield text[start:start + size]


def _clean_number(value: str) -> str:
    return value.strip().replace(",", "").replace("٬", "")


def _fmt_number(value: str, decimals: int = 0) -> str:
    raw = _clean_number(value)
    if raw in {"", "—", "-"}:
        return "داده موجود نیست"
    try:
        number = float(raw)
    except ValueError:
        return value.strip()
    if decimals == 0:
        text = f"{number:,.0f}".replace(",", "٬")
    else:
        text = f"{number:,.{decimals}f}".replace(",", "٬").replace(".", "٫")
    return text.translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))


def _fmt_percent(value: str) -> str:
    raw = _clean_number(value).replace("%", "")
    if raw in {"", "—", "-"}:
        return "داده موجود نیست"
    try:
        number = float(raw)
    except ValueError:
        return value.strip()
    sign = "+" if number > 0 else "−" if number < 0 else ""
    text = f"{abs(number):.3f}".replace(".", "٫")
    return sign + text.translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")) + "%"


def _persian_digits(text: str) -> str:
    return str(text).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))


def _parse_rows(report_text: str):
    rows = []
    for line in report_text.splitlines():
        if not line.startswith("|") or line.startswith("|---"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 11 and cells[0].isdigit():
            rows.append(cells)
    return rows


def format_v41_cards(report_text: str) -> str:
    """Render the canonical 11 report fields as compact Bale cards.

    No contract type, settlement method, cost, or other field is inferred.
    Missing source values remain explicitly missing.
    """
    rows = _parse_rows(report_text)
    if not rows:
        # A report already rendered as cards is passed through unchanged.
        if "🔹 1." in report_text or "🔹 ۱." in report_text:
            return report_text.strip() + "\n"
        raise RuntimeError("V4.1 ranking rows were not found in the generated report.")

    out = [
        "📊 گزارش رتبه‌بندی اختیار معامله — V4.1",
        f"تعداد قراردادها: {_persian_digits(len(rows))}",
        "",
    ]
    for rank, symbol, strike, last, breakeven, base, leverage, distance, expiry, remaining, score in rows:
        expiry_text = expiry if expiry not in {"", "—", "-"} else "داده موجود نیست"
        remaining_text = _fmt_number(remaining)
        out.extend([
            "━━━━━━━━━━━━━━━━",
            f"🔹 {_persian_digits(rank)}. {symbol}",
            "",
            f"قیمت اعمال: {_fmt_number(strike)} | آخرین: {_fmt_number(last)}",
            f"سر‌به‌سر: {_fmt_number(breakeven)} | پایه: {_fmt_number(base)}",
            f"اهرم: {_fmt_number(leverage, 2)} | فاصله سر‌به‌سر: {_fmt_percent(distance)}",
            f"سررسید: {expiry_text} ({remaining_text} روز)",
            f"امتیاز: {_fmt_number(score, 2)}",
            "",
        ])
    out.append("━━━━━━━━━━━━━━━━")
    return "\n".join(out) + "\n"


def send_chunk(token: str, chat_id: str, text: str) -> None:
    url = BALE_API_URL.format(token=token)
    payload = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": True,
    }
    response = requests.post(url, json=payload, timeout=30)
    if not response.ok:
        raise RuntimeError(f"Send failed: {response.status_code} {response.text}")
    data = response.json()
    if data.get("ok") is not True:
        raise RuntimeError(f"Bale API rejected message: {data}")


def main() -> int:
    load_env_file(ENV_PATH)
    token = os.getenv("BALE_BOT_TOKEN", "").strip()
    chat_id = os.getenv("BALE_CHAT_ID", "").strip()
    if not token or not chat_id:
        print("Missing BALE_BOT_TOKEN or BALE_CHAT_ID in .env", file=sys.stderr)
        return 2

    report_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_REPORT_PATH
    report_text = format_v41_cards(read_report_text(report_path))
    current_hash = sha256_text(report_text)
    last_hash = read_last_hash()
    if current_hash == last_hash:
        print("V4.1 report unchanged; skipping send.")
        return 0

    chunks = list(split_chunks(report_text))
    for chunk in chunks:
        send_chunk(token, chat_id, chunk)
    write_last_hash(current_hash)
    print(f"V4.1 Bale report sent successfully | chunks={len(chunks)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
