import json
import hashlib
import urllib.request
import urllib.parse
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

OUT = Path("output/history/tsetmc_api_archive/universe")
OUT.mkdir(parents=True, exist_ok=True)

BASE = "https://cdn.tsetmc.com/api"
URLS = {
    "market_watch_cdn": (
        BASE + "/ClosingPrice/GetMarketWatch?"
        + urllib.parse.urlencode([
            ("market", "0"),
            ("industrialGroup", ""),
            ("paperTypes[0]", "1"),
            ("paperTypes[1]", "2"),
            ("paperTypes[2]", "3"),
            ("paperTypes[3]", "4"),
            ("paperTypes[4]", "5"),
            ("paperTypes[5]", "6"),
            ("paperTypes[6]", "7"),
            ("paperTypes[7]", "8"),
            ("paperTypes[8]", "9"),
            ("showTraded", "false"),
            ("withBestLimits", "false"),
            ("hEven", "0"),
            ("RefID", "0"),
        ])
    ),
    "market_watch_legacy": (
        "https://old.tsetmc.com/tsev2/excel/MarketWatchPlus.aspx?d=0"
    ),
    "instrument_search_foulad": (
        BASE + "/Instrument/GetInstrumentSearch/"
        + urllib.parse.quote("فولاد", safe="")
    ),
}

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.tsetmc.com/",
}

report = {
    "created_at": datetime.now(ZoneInfo("Asia/Tehran")).isoformat(),
    "source": "TSETMC",
    "scope": "FULL_MARKET_DISCOVERY",
    "production_signal": "OFF",
    "trading_signal_generation": "FORBIDDEN",
    "endpoints": {},
}

for name, url in URLS.items():
    result = {"url": url, "status": "FAILED"}
    try:
        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(request, timeout=12) as response:
            raw = response.read()
            result["http_status"] = response.status
            result["content_type"] = response.headers.get("Content-Type", "")
            result["final_url"] = response.geturl()

        digest = hashlib.sha256(raw).hexdigest()
        suffix = ".xlsx" if name == "market_watch_legacy" else ".response"
        path = OUT / f"{name}{suffix}"
        path.write_bytes(raw)

        result.update({
            "status": "RECEIVED",
            "bytes": len(raw),
            "sha256": digest,
            "raw_file": str(path),
            "retrieved_at": datetime.now(
                ZoneInfo("Asia/Tehran")
            ).isoformat(),
        })

        content_type = result["content_type"].lower()
        if "json" in content_type or raw.lstrip().startswith((b"{", b"[")):
            try:
                data = json.loads(raw.decode("utf-8-sig"))
                result["json_valid"] = True
                result["top_keys"] = (
                    list(data.keys())[:40] if isinstance(data, dict) else []
                )
                result["list_counts"] = (
                    {k: len(v) for k, v in data.items() if isinstance(v, list)}
                    if isinstance(data, dict)
                    else {"root_list": len(data)} if isinstance(data, list)
                    else {}
                )
                if name == "market_watch_cdn":
                    key = next(
                        (k for k in data if k.lower() == "marketwatch"),
                        None
                    ) if isinstance(data, dict) else None
                    result["market_rows"] = (
                        len(data[key]) if key and isinstance(data[key], list)
                        else None
                    )
                if name == "instrument_search_foulad":
                    key = next(
                        (k for k in data if k.lower() == "instrumentsearch"),
                        None
                    ) if isinstance(data, dict) else None
                    result["search_rows"] = (
                        len(data[key]) if key and isinstance(data[key], list)
                        else None
                    )
            except Exception as exc:
                result["json_valid"] = False
                result["parse_error"] = str(exc)
        else:
            result["json_valid"] = False
            result["format_note"] = "Non-JSON response saved raw; inspect before parsing"

        print(f"\n{name}: {result['status']}")
        print("HTTP:", result.get("http_status"))
        print("CONTENT_TYPE:", result.get("content_type"))
        print("BYTES:", result.get("bytes"))
        print("KEYS:", result.get("top_keys"))
        print("COUNTS:", result.get("list_counts"))
        print("SHA256:", digest)

    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        print(f"\n{name}: FAILED - {result['error']}")

    report["endpoints"][name] = result

report["market_watch_usable"] = any(
    report["endpoints"].get(name, {}).get("status") == "RECEIVED"
    and (
        report["endpoints"][name].get("market_rows", 0) > 0
        or (
            name == "market_watch_legacy"
            and report["endpoints"][name].get("bytes", 0) > 1000
        )
    )
    for name in ("market_watch_cdn", "market_watch_legacy")
)

report_path = OUT / "discovery_report.json"
report_path.write_text(
    json.dumps(report, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

print("\n========== DISCOVERY RESULT ==========")
print("REPORT:", report_path)
print("MARKET_WATCH_USABLE:", report["market_watch_usable"])
print("PRODUCTION_SIGNAL: OFF")
print("TRADING_SIGNAL_GENERATION: FORBIDDEN")
