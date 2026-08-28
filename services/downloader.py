#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Option School Full Excel Downloader
خروجی: ~/options_report/data/optionschool24_all_YYYYMMDD_HHMMSS.xlsx
"""

from __future__ import annotations

import os
import re
import sys
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path.home() / "options_report"
DATA_DIR = ROOT / "data"
ENV_PATH = ROOT / ".env"

DATA_DIR.mkdir(parents=True, exist_ok=True)
load_dotenv(ENV_PATH)

BASE_URL = os.getenv("OPTIONSCHOOL_BASE_URL", "https://optionschool.ir").rstrip("/")
USERNAME = (os.getenv("OPTIONSCHOOL_USERNAME") or "").strip()
PASSWORD = (os.getenv("OPTIONSCHOOL_PASSWORD") or "").strip()
COOKIE = (os.getenv("OPTIONSCHOOL_COOKIE") or "").strip()
DOWNLOAD_URL = (os.getenv("OPTIONSCHOOL_DOWNLOAD_URL") or "").strip()
USER_AGENT = os.getenv(
    "OPTIONSCHOOL_USER_AGENT",
    "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
)

TIMEOUT = 90


def _now_tag() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _parse_cookie_header(cookie_str: str) -> dict:
    cookies = {}
    if not cookie_str:
        return cookies
    for part in cookie_str.split(";"):
        part = part.strip()
        if not part or "=" not in part:
            continue
        k, v = part.split("=", 1)
        cookies[k.strip()] = v.strip()
    return cookies


def _build_session() -> requests.Session:
    s = requests.Session()
    s.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept": "*/*",
            "Accept-Language": "fa-IR,fa;q=0.9,en-US;q=0.8,en;q=0.7",
            "Connection": "keep-alive",
            "Referer": f"{BASE_URL}/",
        }
    )
    if COOKIE:
        s.cookies.update(_parse_cookie_header(COOKIE))
        s.headers["Cookie"] = COOKIE
    return s


def _try_login(session: requests.Session) -> bool:
    """تلاش لاگین ساده (اگر endpoint سایت تغییر کرده باشد، از Cookie استفاده کن)."""
    if not USERNAME or not PASSWORD:
        return False

    candidates = [
        f"{BASE_URL}/login",
        f"{BASE_URL}/api/login",
        f"{BASE_URL}/auth/login",
        f"{BASE_URL}/user/login",
    ]

    payloads = [
        {"username": USERNAME, "password": PASSWORD},
        {"email": USERNAME, "password": PASSWORD},
        {"mobile": USERNAME, "password": PASSWORD},
        {"user": USERNAME, "pass": PASSWORD},
    ]

    for url in candidates:
        for payload in payloads:
            try:
                r = session.post(url, data=payload, timeout=TIMEOUT, allow_redirects=True)
                if r.status_code in (200, 302) and (
                    "token" in r.text.lower()
                    or "dashboard" in r.text.lower()
                    or len(session.cookies) > 0
                ):
                    print(f"[LOGIN] احتمالاً موفق: {url}")
                    return True
            except Exception as e:
                print(f"[LOGIN] fail {url}: {e}")
    return False


def _guess_download_urls() -> list[str]:
    urls = []
    if DOWNLOAD_URL:
        urls.append(DOWNLOAD_URL)

    # مسیرهای رایج export (اگر URL واقعی را از Network بگیری بهتر است)
    guesses = [
        f"{BASE_URL}/api/options/export",
        f"{BASE_URL}/api/option/export",
        f"{BASE_URL}/export/excel",
        f"{BASE_URL}/options/export",
        f"{BASE_URL}/ranking/export",
        f"{BASE_URL}/api/ranking/excel",
        f"{BASE_URL}/download/excel",
    ]
    for g in guesses:
        if g not in urls:
            urls.append(g)
    return urls


def _is_excel(content: bytes, content_type: str, filename: str) -> bool:
    ct = (content_type or "").lower()
    fn = (filename or "").lower()
    if content[:2] == b"PK":  # xlsx = zip
        return True
    if "sheet" in ct or "excel" in ct or "spreadsheet" in ct or "octet-stream" in ct:
        return True
    if fn.endswith(".xlsx") or fn.endswith(".xls"):
        return True
    return False


def _extract_filename(resp: requests.Response) -> str | None:
    cd = resp.headers.get("Content-Disposition", "") or ""
    m = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^\";]+)"?', cd, re.I)
    if m:
        return m.group(1).strip()
    return None


def download_excel() -> Path:
    session = _build_session()

    if not COOKIE and USERNAME and PASSWORD:
        print("[INFO] Cookie خالی است؛ تلاش برای لاگین...")
        _try_login(session)
    elif not COOKIE and not DOWNLOAD_URL:
        raise RuntimeError(
            "نه COOKIE داری نه DOWNLOAD_URL. "
            "باید از مرورگر Cookie و لینک دانلود اکسل را بگیری."
        )

    last_error = None
    for url in _guess_download_urls():
        print(f"[TRY] {url}")
        try:
            # بعضی endpointها GET و بعضی POST هستند
            for method in ("GET", "POST"):
                if method == "GET":
                    resp = session.get(url, timeout=TIMEOUT, allow_redirects=True)
                else:
                    resp = session.post(url, timeout=TIMEOUT, allow_redirects=True)

                print(f"  -> {method} status={resp.status_code} type={resp.headers.get('Content-Type')} size={len(resp.content)}")

                if resp.status_code != 200:
                    last_error = f"{method} {url} -> HTTP {resp.status_code}"
                    continue

                fname_hdr = _extract_filename(resp) or ""
                if not _is_excel(resp.content, resp.headers.get("Content-Type", ""), fname_hdr):
                    # احتمالاً HTML لاگین برگشته
                    snippet = resp.text[:200].replace("\n", " ")
                    last_error = f"{method} {url} -> پاسخ اکسل نیست | {snippet}"
                    print(f"  !! اکسل نیست: {snippet[:120]}")
                    continue

                out_name = f"optionschool24_all_{_now_tag()}.xlsx"
                out_path = DATA_DIR / out_name
                out_path.write_bytes(resp.content)
                print(f"[OK] ذخیره شد: {out_path}")
                print(f"[OK] حجم: {out_path.stat().st_size} bytes")
                return out_path

        except Exception as e:
            last_error = str(e)
            print(f"  !! error: {e}")

    raise RuntimeError(
        "دانلود ناموفق بود.\n"
        f"آخرین خطا: {last_error}\n\n"
        "حتماً OPTIONSCHOOL_COOKIE و OPTIONSCHOOL_DOWNLOAD_URL را از Network تب مرورگر پر کن."
    )


def main() -> int:
    print("=" * 60)
    print("Option School Downloader")
    print("DATA_DIR =", DATA_DIR)
    print("COOKIE set =", bool(COOKIE))
    print("DOWNLOAD_URL set =", bool(DOWNLOAD_URL))
    print("USERNAME set =", bool(USERNAME))
    print("=" * 60)

    try:
        path = download_excel()
        print("\nSUCCESS:", path)
        return 0
    except Exception as e:
        print("\nFAILED:", e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
