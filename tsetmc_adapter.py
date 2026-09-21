#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Evidence-preserving TSETMC source adapter for V4.1."""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass
from typing import Any, Callable
from urllib.parse import quote
import urllib.request

DEFAULT_BASE_URL = "https://cdn.tsetmc.com/api"
USER_AGENT = "OptimusAI-V4.1-TSETMC-Adapter/1.0"
RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class TSETMCError(RuntimeError):
    pass


@dataclass(frozen=True)
class TSETMCResponse:
    endpoint: str
    payload: Any
    sha256: str
    retrieved_at: str


def _sha256_payload(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


class TSETMCAdapter:
    """Small, testable boundary around the TSETMC CDN JSON API."""

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = 20.0,
        retries: int = 2,
        sleep_fn: Callable[[float], None] = time.sleep,
        opener: Callable[..., Any] | None = None,
    ):
        self.base_url = (base_url or os.getenv("TSETMC_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        self.timeout = float(timeout)
        self.retries = int(retries)
        self.sleep_fn = sleep_fn
        self.opener = opener or urllib.request.urlopen

    def _request(self, path: str) -> TSETMCResponse:
        url = f"{self.base_url}/{path.lstrip('/')}"
        request = urllib.request.Request(
            url,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        )
        last_error: Exception | None = None

        for attempt in range(self.retries + 1):
            try:
                with self.opener(request, timeout=self.timeout) as response:
                    status = getattr(response, "status", 200)
                    body = response.read()
                if status in RETRYABLE_STATUS:
                    raise TSETMCError(f"retryable HTTP status: {status}")
                if status < 200 or status >= 300:
                    raise TSETMCError(f"TSETMC HTTP status: {status}")

                text_body = body.decode("utf-8", errors="replace")
                if any(marker in text_body for marker in
                       ("مسدود", "دسترسی شما", "General Error Detected")):
                    raise TSETMCError("TSETMC soft-block detected")
                try:
                    payload = json.loads(text_body)
                except json.JSONDecodeError as exc:
                    raise TSETMCError("TSETMC response is not valid JSON") from exc

                return TSETMCResponse(
                    endpoint=url,
                    payload=payload,
                    sha256=_sha256_payload(payload),
                    retrieved_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                )
            except Exception as exc:
                last_error = exc
                if attempt >= self.retries:
                    break
                self.sleep_fn(0.5 * (attempt + 1))

        raise TSETMCError(f"TSETMC request failed: {url}: {last_error}") from last_error

    @staticmethod
    def _unwrap(response: TSETMCResponse, key: str) -> dict[str, Any]:
        payload = response.payload
        if not isinstance(payload, dict):
            raise TSETMCError(f"unexpected TSETMC payload for {response.endpoint}")
        return {
            "source": "TSETMC",
            "endpoint": response.endpoint,
            "snapshot_sha256": response.sha256,
            "retrieved_at": response.retrieved_at,
            "data": payload.get(key),
        }

    def search_instrument(self, symbol: str) -> dict[str, Any]:
        if not str(symbol).strip():
            raise ValueError("symbol is required")
        r = self._request(f"Instrument/GetInstrumentSearch/{quote(str(symbol).strip(), safe='')}")
        return self._unwrap(r, "instrumentSearch")

    def instrument_info(self, ins_code: str) -> dict[str, Any]:
        r = self._request(f"Instrument/GetInstrumentInfo/{quote(str(ins_code), safe='')}")
        return self._unwrap(r, "instrumentInfo")

    def instrument_identity(self, ins_code: str) -> dict[str, Any]:
        r = self._request(f"Instrument/GetInstrumentIdentity/{quote(str(ins_code), safe='')}")
        return self._unwrap(r, "instrumentIdentity")

    def quote(self, ins_code: str) -> dict[str, Any]:
        r = self._request(f"ClosingPrice/GetClosingPriceInfo/{quote(str(ins_code), safe='')}")
        return self._unwrap(r, "closingPriceInfo")

    def order_book(self, ins_code: str) -> dict[str, Any]:
        r = self._request(f"BestLimits/{quote(str(ins_code), safe='')}")
        return self._unwrap(r, "bestLimits")

    def client_type(self, ins_code: str) -> dict[str, Any]:
        r = self._request(f"ClientType/GetClientType/{quote(str(ins_code), safe='')}/1/0")
        return self._unwrap(r, "clientType")

    def daily_history(self, ins_code: str, top: int = 0) -> dict[str, Any]:
        if int(top) < 0:
            raise ValueError("top must be non-negative")
        r = self._request(
            f"ClosingPrice/GetClosingPriceDailyList/{quote(str(ins_code), safe='')}/{int(top)}"
        )
        return self._unwrap(r, "closingPriceDaily")

    def market_overview(self, flow: int = 0) -> dict[str, Any]:
        if int(flow) < 0:
            raise ValueError("flow must be non-negative")
        r = self._request(f"MarketData/GetMarketOverview/{int(flow)}")
        return self._unwrap(r, "marketOverview")

    def canonical_instrument(self, ins_code: str) -> dict[str, Any]:
        """Merge only explicitly sourced fields; missing identity stays missing."""
        identity = self.instrument_identity(ins_code)
        info = self.instrument_info(ins_code)
        quote = self.quote(ins_code)

        identity_data = identity.get("data") or {}
        info_data = info.get("data") or {}
        quote_data = quote.get("data") or {}

        def first(*values):
            for value in values:
                if value not in (None, ""):
                    return value
            return None

        return {
            "instrument_id": str(ins_code),
            "symbol": first(
                identity_data.get("lVal18AFC"),
                info_data.get("lVal18AFC"),
                quote_data.get("lVal18AFC"),
            ),
            "underlying_id": first(
                identity_data.get("underlying_id"),
                identity_data.get("underlyingId"),
                identity_data.get("insCode"),
                info_data.get("underlying_id"),
                info_data.get("underlyingId"),
            ),
            "underlying_symbol": first(
                identity_data.get("underlying_symbol"),
                identity_data.get("underlyingSymbol"),
                info_data.get("underlying_symbol"),
                info_data.get("underlyingSymbol"),
            ),
            "contract_type": first(
                identity_data.get("contract_type"),
                identity_data.get("contractType"),
                info_data.get("contract_type"),
                info_data.get("contractType"),
            ),
            "strike": first(identity_data.get("strike"), info_data.get("strike")),
            "expiry": first(identity_data.get("expiry"), info_data.get("expiry")),
            "last_price": first(quote_data.get("pDrCotVal"), quote_data.get("pl")),
            "close_price": first(quote_data.get("pClosing"), quote_data.get("pc")),
            "volume": first(quote_data.get("qTotTran5J"), quote_data.get("zTotTran")),
            "trade_value": quote_data.get("qTotCap"),
            "trade_count": quote_data.get("zTotTran"),
            "source_refs": {"identity": identity, "info": info, "quote": quote},
        }
