#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Evidence-preserving TSETMC source adapter for V4.1."""

from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import datetime
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
        timeout: float = 8.0,
        retries: int = 2,
        sleep_fn: Callable[[float], None] = time.sleep,
        opener: Callable[..., Any] | None = None,
    ):
        self.base_url = (base_url or os.getenv("TSETMC_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        self.timeout = float(timeout)
        self.retries = int(retries)
        self.sleep_fn = sleep_fn
        self.opener = opener or urllib.request.urlopen

    def _request(self, path: str, *, timeout: float | None = None, retries: int | None = None) -> TSETMCResponse:
        url = f"{self.base_url}/{path.lstrip('/')}"
        request = urllib.request.Request(
            url,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        )
        last_error: Exception | None = None

        for attempt in range(self.retries + 1):
            try:
                with self.opener(request, timeout=request_timeout) as response:
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
                if attempt >= request_retries:
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

    def option_market_watch(self, flow: int = 1) -> dict[str, Any]:
        """Fetch the TSETMC option market-watch payload without inferring fields."""
        if int(flow) < 0:
            raise ValueError("flow must be non-negative")
        r = self._request(f"Instrument/GetInstrumentOptionMarketWatch/{int(flow)}")
        return {
            "source": "TSETMC",
            "endpoint": r.endpoint,
            "snapshot_sha256": r.sha256,
            "retrieved_at": r.retrieved_at,
            "data": r.payload,
        }

    def option_market_watch_records(self, flow: int = 1) -> dict[str, Any]:
        """Normalize explicit option-market-watch identity records without inference."""
        result = self.option_market_watch(flow=flow)
        data = result.get("data") or {}
        raw_records = data.get("instrumentOptMarketWatch", [])
        records = []
        if isinstance(raw_records, list):
            for item in raw_records:
                if not isinstance(item, dict):
                    continue
                if not any(item.get(k) not in (None, "") for k in ("insCode_P", "insCode_C", "uaInsCode")):
                    continue
                records.append({
                    "option_put_id": str(item["insCode_P"]) if item.get("insCode_P") not in (None, "") else None,
                    "option_call_id": str(item["insCode_C"]) if item.get("insCode_C") not in (None, "") else None,
                    "underlying_id": str(item["uaInsCode"]) if item.get("uaInsCode") not in (None, "") else None,
                    "put_symbol": item.get("lVal18AFC_P"),
                    "call_symbol": item.get("lVal18AFC_C"),
                    "underlying_symbol": item.get("lval30_UA"),
                    "strike": item.get("strikePrice"),
                    "begin_date": item.get("beginDate"),
                    "end_date": item.get("endDate"),
                    "remaining_days": item.get("remainedDay"),
                })
        return {
            **{k: result.get(k) for k in ("source", "endpoint", "snapshot_sha256", "retrieved_at")},
            "records": records,
            "record_count": len(records),
            "raw_data": data,
        }

    def option_market_watch_instrument_records(self, flow: int = 1) -> dict[str, Any]:
        """Expand explicit P/C IDs into instrument records without inference."""
        result = self.option_market_watch_records(flow=flow)
        instruments = []
        for record in result.get("records", []):
            common = {
                "underlying_id": record.get("underlying_id"),
                "underlying_symbol": record.get("underlying_symbol"),
                "strike": record.get("strike"),
                "begin_date": record.get("begin_date"),
                "end_date": record.get("end_date"),
                "remaining_days": record.get("remaining_days"),
            }
            if record.get("option_put_id"):
                instruments.append({
                    **common,
                    "instrument_id": record["option_put_id"],
                    "symbol": record.get("put_symbol"),
                    "contract_type": "PUT",
                    "identity_source_field": "insCode_P",
                })
            if record.get("option_call_id"):
                instruments.append({
                    **common,
                    "instrument_id": record["option_call_id"],
                    "symbol": record.get("call_symbol"),
                    "contract_type": "CALL",
                    "identity_source_field": "insCode_C",
                })
        return {
            **{k: result.get(k) for k in ("source", "endpoint", "snapshot_sha256", "retrieved_at")},
            "records": instruments,
            "record_count": len(instruments),
            "raw_data": result.get("raw_data"),
        }


    def option_market_watch_universe(self, flows: tuple[int, ...] = (0, 1, 2, 4)) -> dict[str, Any]:
        """Discover the option universe across validated TSETMC flow values.

        Identity is always taken from explicit insCode_P/insCode_C fields.
        Results are de-duplicated by instrument_id; no symbol-prefix inference
        is used. Every attempted flow remains in the returned evidence.
        """
        normalized_flows = []
        for flow in flows:
            value = int(flow)
            if value < 0:
                raise ValueError("flow must be non-negative")
            if value not in normalized_flows:
                normalized_flows.append(value)

        all_instruments = []
        flow_evidence = []
        seen: set[str] = set()

        for flow in normalized_flows:
            try:
                result = self.option_market_watch_instrument_records(flow=flow)
                records = result.get("records", [])
                accepted = 0
                duplicates = 0
                for record in records:
                    instrument_id = record.get("instrument_id")
                    if not instrument_id:
                        continue
                    if str(instrument_id) in seen:
                        duplicates += 1
                        continue
                    seen.add(str(instrument_id))
                    all_instruments.append(record)
                    accepted += 1
                flow_evidence.append({
                    "flow": flow,
                    "status": "SUCCESS",
                    "endpoint": result.get("endpoint"),
                    "snapshot_sha256": result.get("snapshot_sha256"),
                    "retrieved_at": result.get("retrieved_at"),
                    "raw_record_count": len(records),
                    "accepted_unique_instruments": accepted,
                    "duplicate_instruments": duplicates,
                })
            except Exception as exc:
                flow_evidence.append({
                    "flow": flow,
                    "status": "FAILED",
                    "error_type": type(exc).__name__,
                })

        import hashlib
        import json
        aggregate = {
            "flows": normalized_flows,
            "flow_evidence": flow_evidence,
        }
        aggregate_sha256 = hashlib.sha256(
            json.dumps(aggregate, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        successful = [x for x in flow_evidence if x.get("status") == "SUCCESS"]
        return {
            "source": "TSETMC",
            "flows": normalized_flows,
            "records": all_instruments,
            "record_count": len(all_instruments),
            "flow_evidence": flow_evidence,
            "endpoint": "Instrument/GetInstrumentOptionMarketWatch/{flow}",
            "snapshot_sha256": aggregate_sha256,
            "retrieved_at": successful[-1].get("retrieved_at") if successful else None,
        }

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

        # TSETMC closingPriceInfo carries dEven (YYYYMMDD) and hEven (HHMMSS).
        # This is source-observation time, not adapter retrieval time and not
        # a guessed session-close timestamp. Preserve it only when both fields
        # are explicitly present and valid.
        source_market_timestamp = None
        source_market_timestamp_status = "UNAVAILABLE"
        try:
            d_even = int(quote_data.get("dEven"))
            h_even = int(quote_data.get("hEven"))
            hh = h_even // 10000
            mm = (h_even // 100) % 100
            ss = h_even % 100
            source_market_timestamp = datetime.strptime(
                f"{d_even:08d} {hh:02d}:{mm:02d}:{ss:02d}", "%Y%m%d %H:%M:%S"
            ).isoformat()
            source_market_timestamp_status = "AVAILABLE"
        except (TypeError, ValueError):
            pass

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
            "source_market_timestamp": source_market_timestamp,
            "source_market_timestamp_status": source_market_timestamp_status,
            "source_refs": {"identity": identity, "info": info, "quote": quote},
        }
