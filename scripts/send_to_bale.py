#!/usr/bin/env python3
"""Send a generated report document to a Bale bot chat."""

from __future__ import annotations

import argparse
import os
import time
from pathlib import Path
from typing import Any


def _response_json(response: Any) -> dict[str, Any]:
    try:
        payload = response.json()
    except Exception as exc:  # pragma: no cover - defensive network handling
        raise RuntimeError(
            f"Bale returned HTTP {response.status_code} with a non-JSON response."
        ) from exc
    if not isinstance(payload, dict):
        raise RuntimeError("Bale returned an unexpected response shape.")
    return payload


def send_document(
    document_path: Path,
    token: str,
    chat_id: str,
    caption: str,
    api_base: str,
    retries: int = 3,
) -> dict[str, Any]:
    try:
        import requests
    except ImportError as exc:  # pragma: no cover - exercised in CI
        raise SystemExit("requests is required. Install it with: pip install requests") from exc

    if not document_path.is_file():
        raise FileNotFoundError(document_path)
    if document_path.stat().st_size > 50 * 1024 * 1024:
        raise ValueError("Bale document uploads must be smaller than 50 MB.")
    if not token.strip() or not chat_id.strip():
        raise ValueError("Both BALE_BOT_TOKEN and BALE_CHAT_ID are required.")

    endpoint = f"{api_base.rstrip('/')}/bot{token}/sendDocument"
    last_error = "unknown error"
    for attempt in range(1, retries + 1):
        try:
            with document_path.open("rb") as handle:
                response = requests.post(
                    endpoint,
                    data={"chat_id": chat_id, "caption": caption[:1024]},
                    files={
                        "document": (
                            document_path.name,
                            handle,
                            "application/pdf"
                            if document_path.suffix.lower() == ".pdf"
                            else "application/octet-stream",
                        )
                    },
                    timeout=90,
                )
            payload = _response_json(response)
            if response.ok and payload.get("ok") is True:
                return payload

            description = str(payload.get("description", response.text[:300]))
            last_error = f"HTTP {response.status_code}: {description}"
            retry_after = payload.get("parameters", {}).get("retry_after")
            if response.status_code == 429 and retry_after:
                time.sleep(min(60, max(1, int(retry_after))))
            elif response.status_code >= 500 and attempt < retries:
                time.sleep(2**attempt)
            else:
                break
        except requests.RequestException as exc:
            last_error = str(exc)
            if attempt < retries:
                time.sleep(2**attempt)

    raise RuntimeError(f"Bale sendDocument failed after {retries} attempts: {last_error}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", required=True, type=Path)
    parser.add_argument("--caption", default="گزارش خودکار Optionschool | موتور V4 کاندید")
    parser.add_argument("--token", default=os.getenv("BALE_BOT_TOKEN", ""))
    parser.add_argument("--chat-id", default=os.getenv("BALE_CHAT_ID", ""))
    parser.add_argument(
        "--api-base",
        default=os.getenv("BALE_API_BASE", "https://tapi.bale.ai"),
    )
    args = parser.parse_args()
    payload = send_document(
        args.file.resolve(),
        args.token,
        args.chat_id,
        args.caption,
        args.api_base,
    )
    result = payload.get("result", {})
    file_name = result.get("document", {}).get("file_name", args.file.name)
    print(f"Bale upload succeeded: {file_name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
