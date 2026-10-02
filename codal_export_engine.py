#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Official Codal monthly-activity evidence for disclosed export sales and currencies."""
from __future__ import annotations

import hashlib
import json
import re
import time
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ENGINE_VERSION = "CODAL-EXPORT-EVIDENCE-1.0"
SEARCH_BASE = "https://search.codal.ir/api/search/v2/q"
CODAL_BASE = "https://www.codal.ir"
USER_AGENT = "Mozilla/5.0 OptimusAI/4.1"


def _digits(value: Any) -> str:
    text = str(value or "")
    table = str.maketrans(
        "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩",
        "01234567890123456789",
    )
    return text.translate(table).replace("ي", "ی").replace("ك", "ک").replace("\u200c", " ")


def _norm(value: Any) -> str:
    return " ".join(_digits(value).split()).strip()


def _number(value: Any) -> float | None:
    text = _norm(value)
    if not text or text in {"-", "—", "--"}:
        return None
    negative = text.startswith("(") and text.endswith(")")
    text = text.strip("()").replace(",", "").replace("٬", "").replace("٫", ".").replace(" ", "")
    try:
        result = float(text)
        return -result if negative else result
    except ValueError:
        return None


def _jalali_tuple(value: Any) -> tuple[int, int, int] | None:
    text = _norm(value)
    match = re.search(r"(\d{4})/(\d{1,2})/(\d{1,2})", text)
    if not match:
        return None
    return tuple(int(x) for x in match.groups())


def _publish_tuple(value: Any) -> tuple[int, ...]:
    text = _norm(value)
    match = re.search(r"(\d{4})/(\d{1,2})/(\d{1,2})\s+(\d{1,2}):(\d{1,2}):(\d{1,2})", text)
    if not match:
        return (0, 0, 0, 0, 0, 0)
    return tuple(int(x) for x in match.groups())


class _TableParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables: list[list[list[str]]] = []
        self.depth = 0
        self.rows: list[list[str]] = []
        self.row: list[str] | None = None
        self.cell: list[str] | None = None

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            if self.depth == 0:
                self.rows = []
            self.depth += 1
        elif self.depth and tag == "tr":
            self.row = []
        elif self.depth and tag in {"td", "th"}:
            self.cell = []

    def handle_data(self, data):
        if self.depth and self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if self.depth and tag in {"td", "th"} and self.cell is not None:
            if self.row is not None:
                self.row.append(_norm(" ".join(self.cell)))
            self.cell = None
        elif self.depth and tag == "tr" and self.row is not None:
            if self.row:
                self.rows.append(self.row)
            self.row = None
        elif tag == "table" and self.depth:
            self.depth -= 1
            if self.depth == 0:
                self.tables.append(self.rows)
                self.rows = []


def _parse_tables(html: str) -> list[list[list[str]]]:
    parser = _TableParser()
    parser.feed(html)
    return parser.tables


def _parse_product_exports(table: list[list[str]]) -> dict[str, Any]:
    start = next(
        (i for i, row in enumerate(table) if row and _norm(row[0]).startswith("فروش صادراتی")),
        None,
    )
    if start is None:
        return {"section_present": False, "products": [], "month_total_million_irr": None, "cumulative_total_million_irr": None}

    products = []
    total_row = None
    for row in table[start + 1:]:
        name = _norm(row[0]) if row else ""
        if not name:
            continue
        if name.startswith("جمع فروش صادراتی"):
            total_row = row
            break
        if name.endswith(":") or name.startswith("مصرف ") or name.startswith("خرید "):
            break
        if len(row) < 21:
            continue
        month_qty = _number(row[14])
        month_amount = _number(row[16])
        cumulative_qty = _number(row[18])
        cumulative_amount = _number(row[20])
        if month_qty is None and month_amount is None and cumulative_qty is None and cumulative_amount is None:
            continue
        products.append({
            "product": name,
            "unit": row[1] if len(row) > 1 else None,
            "month_sales_quantity": month_qty,
            "month_sales_amount_million_irr": month_amount,
            "cumulative_sales_quantity": cumulative_qty,
            "cumulative_sales_amount_million_irr": cumulative_amount,
        })

    if total_row and len(total_row) > 20:
        month_total = _number(total_row[16])
        cumulative_total = _number(total_row[20])
        total_basis = "CODAL_EXPLICIT_TOTAL_ROW"
    else:
        month_values = [x["month_sales_amount_million_irr"] for x in products if x["month_sales_amount_million_irr"] is not None]
        cumulative_values = [x["cumulative_sales_amount_million_irr"] for x in products if x["cumulative_sales_amount_million_irr"] is not None]
        month_total = sum(month_values) if month_values else None
        cumulative_total = sum(cumulative_values) if cumulative_values else None
        total_basis = "SUM_OF_DISCLOSED_PRODUCT_ROWS" if products else "UNAVAILABLE"

    return {
        "section_present": True,
        "products": products,
        "month_total_million_irr": month_total,
        "cumulative_total_million_irr": cumulative_total,
        "total_basis": total_basis,
    }


def _parse_currency_exports(table: list[list[str]]) -> dict[str, Any]:
    currencies = []
    for row in table:
        if len(row) < 17 or _norm(row[0]) != "فروش صادراتی":
            continue
        currency = _norm(row[1]) if len(row) > 1 else ""
        if not currency:
            continue
        currencies.append({
            "currency": currency,
            "month_foreign_amount": _number(row[11]),
            "month_fx_rate_irr": _number(row[12]),
            "month_rial_amount_million_irr": _number(row[13]),
            "cumulative_foreign_amount": _number(row[14]),
            "cumulative_fx_rate_irr": _number(row[15]),
            "cumulative_rial_amount_million_irr": _number(row[16]),
        })
    return {
        "section_present": any(row and _norm(row[0]).startswith("فروش صادراتی") for row in table),
        "currencies": currencies,
    }


def parse_monthly_activity_html(html: str) -> dict[str, Any]:
    tables = _parse_tables(html)
    if not tables:
        return {"status": "PARSE_FAILED", "reason": "NO_HTML_TABLES"}
    product = _parse_product_exports(tables[0]) if tables else {"section_present": False}
    currency = _parse_currency_exports(tables[3]) if len(tables) > 3 else {"section_present": False, "currencies": []}
    product_amounts = [
        product.get("month_total_million_irr"),
        product.get("cumulative_total_million_irr"),
    ]
    currency_amounts = [
        x.get("month_rial_amount_million_irr") for x in currency.get("currencies", [])
    ] + [
        x.get("cumulative_rial_amount_million_irr") for x in currency.get("currencies", [])
    ]
    positive = any(x is not None and x > 0 for x in product_amounts + currency_amounts)
    if product.get("section_present") or currency.get("section_present"):
        status = "EXPORT_DISCLOSED" if positive else "NO_EXPORT_REVENUE_DISCLOSED"
    else:
        status = "EXPORT_SECTION_NOT_FOUND"
    return {
        "status": status,
        "product_sales": product,
        "foreign_currency_sales": currency,
        "table_count": len(tables),
        "units_note": "Product and currency rial amounts are in million IRR when the Codal table labels say so; foreign amounts retain the disclosed currency unit.",
    }


def _request(url: str, timeout: int = 20, accept: str = "application/json") -> bytes:
    req = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": accept,
            "Referer": "https://www.codal.ir/",
        },
    )
    with urlopen(req, timeout=timeout) as response:
        return response.read()


def _latest_monthly_letter(symbol: str) -> tuple[dict[str, Any] | None, str, str]:
    params = {
        "Symbol": symbol,
        "Category": "3",
        "LetterType": "-1",
        "PageNumber": "1",
        "search": "true",
        "Childs": "false",
        "Mains": "true",
        "Publisher": "false",
        "Audited": "true",
        "NotAudited": "true",
        "Consolidatable": "true",
        "NotConsolidatable": "true",
    }
    api_url = SEARCH_BASE + "?" + urlencode(params)
    raw = _request(api_url, timeout=20)
    payload = json.loads(raw.decode("utf-8"))
    letters = [
        x for x in payload.get("Letters", [])
        if "گزارش فعالیت ماهانه" in _norm(x.get("Title"))
    ]
    letters.sort(
        key=lambda x: (
            _jalali_tuple(x.get("Title")) or (0, 0, 0),
            _publish_tuple(x.get("PublishDateTime")),
        ),
        reverse=True,
    )
    selected = next((x for x in letters if x.get("HasExcel") and x.get("ExcelUrl")), None)
    api_sha = hashlib.sha256(raw).hexdigest()
    return selected, api_url, api_sha


def fetch_symbol_export_evidence(symbol: str, root: Path | None = None) -> dict[str, Any]:
    root = root or Path(__file__).resolve().parent
    symbol = _norm(symbol)
    retrieved_at = datetime.now(timezone.utc).isoformat()
    try:
        letter, api_url, api_sha = _latest_monthly_letter(symbol)
        if not letter:
            return {
                "status": "NO_CODAL_MONTHLY_EXCEL_REPORT",
                "source": "CODAL",
                "symbol": symbol,
                "retrieved_at": retrieved_at,
                "api_url": api_url,
                "api_response_sha256": api_sha,
            }

        excel_url = letter["ExcelUrl"]
        html = _request(excel_url, timeout=30, accept="*/*").decode("utf-8", "replace")
        html_sha = hashlib.sha256(html.encode("utf-8")).hexdigest()
        parsed = parse_monthly_activity_html(html)
        tracing_no = str(letter.get("TracingNo") or "")
        safe_symbol = re.sub(r"[^\w.-]+", "_", symbol, flags=re.UNICODE)
        archive_dir = root / "output" / "history" / "codal"
        archive_dir.mkdir(parents=True, exist_ok=True)
        html_path = archive_dir / f"{safe_symbol}_{tracing_no}_{html_sha}.html"
        html_path.write_text(html, encoding="utf-8")

        report_url = CODAL_BASE + str(letter.get("Url") or "")
        evidence = {
            "status": parsed.get("status", "PARSE_FAILED"),
            "source": "CODAL",
            "symbol": symbol,
            "company_name": letter.get("CompanyName"),
            "tracing_no": letter.get("TracingNo"),
            "letter_code": letter.get("LetterCode"),
            "title": letter.get("Title"),
            "period_end_jalali": (
                "/".join(str(x) for x in (_jalali_tuple(letter.get("Title")) or ()))
                if _jalali_tuple(letter.get("Title")) else None
            ),
            "publish_datetime_jalali": letter.get("PublishDateTime"),
            "retrieved_at": retrieved_at,
            "search_api_url": api_url,
            "search_api_response_sha256": api_sha,
            "report_url": report_url,
            "excel_url": excel_url,
            "excel_html_sha256": html_sha,
            "excel_html_archive": str(html_path),
            "has_excel": bool(letter.get("HasExcel")),
            "parsed_export_evidence": parsed,
            "export_confirmed_by_explicit_codal_section": parsed.get("status") == "EXPORT_DISCLOSED",
            "usd_currency_disclosed": any(
                "دلار" in _norm(x.get("currency"))
                for x in (parsed.get("foreign_currency_sales") or {}).get("currencies", [])
            ),
        }
        canonical = json.dumps(evidence, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        archive_sha = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        evidence["evidence_sha256"] = archive_sha
        metadata_path = archive_dir / f"{safe_symbol}_{tracing_no}_{archive_sha}.json"
        metadata_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")
        evidence["metadata_archive"] = str(metadata_path)
        return evidence
    except Exception as exc:
        return {
            "status": "UNAVAILABLE",
            "source": "CODAL",
            "symbol": symbol,
            "retrieved_at": retrieved_at,
            "error_type": type(exc).__name__,
            "error": str(exc)[:500],
        }


def fetch_export_context(symbols: list[str], root: Path | None = None) -> dict[str, Any]:
    root = root or Path(__file__).resolve().parent
    results = {}
    for symbol in sorted({ _norm(x) for x in symbols if _norm(x) }):
        results[symbol] = fetch_symbol_export_evidence(symbol, root=root)
    statuses = [x.get("status") for x in results.values()]
    return {
        "status": "PASS" if results and all(x in {"EXPORT_DISCLOSED", "NO_EXPORT_REVENUE_DISCLOSED"} for x in statuses) else "PARTIAL",
        "engine_version": ENGINE_VERSION,
        "source": "CODAL",
        "symbol_count": len(results),
        "symbols": results,
        "rules": {
            "monthly_report_selection": "LATEST_PERIOD_THEN_LATEST_PUBLISH_TIME",
            "export_confirmation": "EXPLICIT_CODAL_EXPORT_SECTION_ONLY",
            "currency_exposure": "ONLY_EXPLICIT_DISCLOSED_CURRENCY_ROWS",
            "missing_data": "UNAVAILABLE_NOT_ZERO",
            "inference": "NO_GENERIC_DOLLAR_SENSITIVITY_INFERENCE",
        },
    }
