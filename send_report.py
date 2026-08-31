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
CHUNK_SIZE = 4000

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
        return "—"
    try:
        number = float(raw)
    except ValueError:
        return value.strip()
    if decimals == 0:
        return f"{number:,.0f}".replace(",", "٬")
    return f"{number:,.{decimals}f}".replace(",", "٬").replace(".", "٫")


def _fmt_percent(value: str) -> str:
    raw = _clean_number(value).replace("%", "")
    if raw in {"", "—", "-"}:
        return "—"
    try:
        number = float(raw)
    except ValueError:
        return value.strip()
    return f"{number:+.3f}".replace(".", "٫") + "%"


def format_top15(report_text: str) -> str:
    """Only the Top-15 option ranking is sent to Bale; summary and controls are suppressed."""
    lines = report_text.splitlines()
    rows = []
    in_table = False

    for line in lines:
        if line.startswith("| رتبه | نماد"):
            in_table = True
            continue
        if in_table and line.startswith("|---"):
            continue
        if in_table and line.startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) == 11:
                rows.append(cells)
                if len(rows) == 15:
                    break
        elif in_table and rows:
            break

    if not rows:
        # Compatibility with a report already generated in card format.
        start = next((i for i, line in enumerate(lines) if line.startswith("🔹 1.")), None)
        if start is None:
            raise RuntimeError("Top-15 ranking rows were not found in the generated report.")
        return "\n".join(lines[start:]).strip() + "\n"

    output = []
    for rank, symbol, strike, last, breakeven, base, leverage, distance, expiry, remaining, score in rows:
        output.extend([
            f"🔹 {rank}. {symbol}",
            f"قیمت اعمال: {_fmt_number(strike)} | آخرین: {_fmt_number(last)}",
            f"سر‌به‌سر: {_fmt_number(breakeven)} | پایه: {_fmt_number(base)}",
            f"اهرم: {_fmt_number(leverage, 2)} | فاصله سر‌به‌سر: {_fmt_percent(distance)}",
            f"سررسید: {expiry} ({_fmt_number(remaining)} روز)" if remaining not in {"", "—", "-"} else f"سررسید: {expiry}",
            f"امتیاز: {_fmt_number(score, 2)}",
            "━━━━━━━━━━━━━━━━━━",
            "",
        ])
    return "\n".join(output).rstrip() + "\n"


def send_chunk(token: str, chat_id: str, text: str) -> None:
    url = BALE_API_URL.format(token=token)
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    response = requests.post(url, json=payload, timeout=30)
    if not response.ok:
        raise RuntimeError(f"Send failed: {response.status_code} {response.text}")


def main() -> int:
    load_env_file(ENV_PATH)

    token = os.getenv("BALE_BOT_TOKEN", "").strip()
    chat_id = os.getenv("BALE_CHAT_ID", "").strip()

    if not token or not chat_id:
        print("Missing BALE_BOT_TOKEN or BALE_CHAT_ID in .env", file=sys.stderr)
        return 2

    report_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_REPORT_PATH
    raw_report = read_report_text(report_path)
    report_text = format_top15(raw_report)
    current_hash = sha256_text(report_text)
    last_hash = read_last_hash()

    if current_hash == last_hash:
        print("Top-15 report unchanged; skipping send.")
        return 0

    chunks = list(split_chunks(report_text))
    for chunk in chunks:
        send_chunk(token, chat_id, chunk)

    write_last_hash(current_hash)
    print("Only Top-15 report sent successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
