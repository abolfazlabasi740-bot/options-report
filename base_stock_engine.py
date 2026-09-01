#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TSETMC base-stock intelligence engine for the Options Report pipeline.

Design rules:
- Never infer a base symbol from an option symbol.
- Require an explicit base-symbol column in the OptionSchool workbook.
- Use TSETMC public JSON endpoints with conservative retry/backoff.
- Preserve missing data as NaN/None; never replace it with zero or a guessed value.
- Calculate raw, auditable features only. No new score/weight is injected into V3 here.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
import requests

BASE_URL = "https://cdn.tsetmc.com/api"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
    "Accept": "application/json,text/plain,*/*",
}

BASE_SYMBOL_COLUMNS = [
    "نماد سهم پایه", "نماد پایه", "نام سهم پایه", "Underlying", "UnderlyingSymbol",
    "BaseSymbol", "base_symbol", "نماد دارایی پایه",
]


@dataclass
class TSETMCClient:
    timeout: int = 20
    retries: int = 3
    pause: float = 0.7

    def get_json(self, path: str) -> dict:
        last_error: Exception | None = None
        for attempt in range(self.retries):
            try:
                response = requests.get(BASE_URL + path, headers=HEADERS, timeout=self.timeout)
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, dict):
                    raise RuntimeError("TSETMC پاسخ JSON شیء برنگرداند.")
                return payload
            except Exception as exc:  # network/API/blocking errors are retained as data-quality failures
                last_error = exc
                if attempt + 1 < self.retries:
                    time.sleep(self.pause * (attempt + 1))
        raise RuntimeError(f"TSETMC API failure: {last_error}")

    def search_symbol(self, symbol: str) -> dict | None:
        data = self.get_json(f"/Instrument/GetInstrumentSearch/{requests.utils.quote(symbol, safe='')}")
        rows = data.get("instrumentSearch") or data.get("instrumentSearchResult") or []
        if not isinstance(rows, list):
            return None
        exact = [r for r in rows if str(r.get("lVal18AFC", "")).strip() == symbol]
        if exact:
            return exact[0]
        return rows[0] if rows else None

    def quote(self, ins_code: str) -> dict:
        return self.get_json(f"/ClosingPrice/GetClosingPriceInfo/{ins_code}").get("closingPriceInfo", {})

    def client_type(self, ins_code: str) -> dict:
        return self.get_json(f"/ClientType/GetClientType/{ins_code}/1/0").get("clientType", {})

    def best_limits(self, ins_code: str) -> list[dict]:
        payload = self.get_json(f"/BestLimits/{ins_code}")
        rows = payload.get("bestLimits") or []
        return rows if isinstance(rows, list) else []


def _first(d: dict, *keys: str) -> Any:
    for key in keys:
        if key in d and d[key] not in (None, ""):
            return d[key]
    return np.nan


def _num(value: Any) -> float:
    try:
        if value is None or (isinstance(value, str) and not value.strip()):
            return np.nan
        return float(str(value).replace(",", "").replace("٬", ""))
    except Exception:
        return np.nan


def find_base_column(df: pd.DataFrame) -> str | None:
    normalized = {str(c).strip().lower(): c for c in df.columns}
    for candidate in BASE_SYMBOL_COLUMNS:
        if candidate.lower() in normalized:
            return normalized[candidate.lower()]
    return None


def _best_limit_features(rows: list[dict]) -> dict:
    # TSETMC best-limit rows use number/numberOfOrders-style fields depending on endpoint version.
    bids, asks = [], []
    for row in rows:
        price = _num(_first(row, "pMeDem", "pMeOf", "price", "p"))
        qty = _num(_first(row, "qTitMeDem", "qTitMeOf", "quantity", "q"))
        demand = _num(_first(row, "pMeDem"))
        offer = _num(_first(row, "pMeOf"))
        if not np.isnan(demand):
            bids.append((demand, qty))
        if not np.isnan(offer):
            asks.append((offer, qty))
        # Some payloads expose side explicitly.
        side = str(_first(row, "side", "Side", "type")).lower()
        if side in {"buy", "bid", "1"} and not np.isnan(price):
            bids.append((price, qty))
        if side in {"sell", "ask", "offer", "2"} and not np.isnan(price):
            asks.append((price, qty))

    return {
        "Base_BestBidPrice": bids[0][0] if bids else np.nan,
        "Base_BestBidVolume": bids[0][1] if bids else np.nan,
        "Base_BestAskPrice": asks[0][0] if asks else np.nan,
        "Base_BestAskVolume": asks[0][1] if asks else np.nan,
    }


def collect_symbol(client: TSETMCClient, symbol: str) -> dict:
    result: dict[str, Any] = {"BaseSymbol": symbol, "BaseDataStatus": "UNKNOWN"}
    try:
        instrument = client.search_symbol(symbol)
        if not instrument:
            result["BaseDataStatus"] = "SYMBOL_NOT_FOUND"
            return result
        ins_code = str(_first(instrument, "insCode", "inscode"))
        if not ins_code or ins_code == "nan":
            result["BaseDataStatus"] = "INSCODE_MISSING"
            return result
        result["BaseInsCode"] = ins_code
        result["BaseSymbolResolved"] = str(_first(instrument, "lVal18AFC"))

        quote = client.quote(ins_code)
        ct = client.client_type(ins_code)
        limits = client.best_limits(ins_code)

        last = _num(_first(quote, "pDrCotVal", "pl", "last"))
        close = _num(_first(quote, "pClosing", "pc", "close"))
        prev = _num(_first(quote, "priceYesterday", "py", "prevClose"))
        volume = _num(_first(quote, "qTotTran5J", "tvol", "volume"))
        value = _num(_first(quote, "qTotCap", "tval", "value"))
        trades = _num(_first(quote, "zTotTran", "tno", "count"))

        buy_i_vol = _num(_first(ct, "buy_I_Volume", "buyIVolume", "buy_I_Vol"))
        sell_i_vol = _num(_first(ct, "sell_I_Volume", "sellIVolume", "sell_I_Vol"))
        buy_n_vol = _num(_first(ct, "buy_N_Volume", "buyNVolume", "buy_N_Vol"))
        sell_n_vol = _num(_first(ct, "sell_N_Volume", "sellNVolume", "sell_N_Vol"))
        buy_i_count = _num(_first(ct, "buy_CountI", "buyICount", "buy_I_Count"))
        sell_i_count = _num(_first(ct, "sell_CountI", "sellICount", "sell_I_Count"))
        buy_n_count = _num(_first(ct, "buy_CountN", "buyNCount", "buy_N_Count"))
        sell_n_count = _num(_first(ct, "sell_CountN", "sellNCount", "sell_N_Count"))

        result.update({
            "BaseLast": last,
            "BaseClose": close,
            "BasePrevClose": prev,
            "BasePriceChangePct": ((last - prev) / prev * 100) if pd.notna(last) and pd.notna(prev) and prev else np.nan,
            "BaseVolume": volume,
            "BaseValue": value,
            "BaseTradeCount": trades,
            "BaseRealBuyVolume": buy_i_vol,
            "BaseRealSellVolume": sell_i_vol,
            "BaseLegalBuyVolume": buy_n_vol,
            "BaseLegalSellVolume": sell_n_vol,
            "BaseRealBuyCount": buy_i_count,
            "BaseRealSellCount": sell_i_count,
            "BaseLegalBuyCount": buy_n_count,
            "BaseLegalSellCount": sell_n_count,
            "BaseRealNetMoneyProxy": buy_i_vol - sell_i_vol if pd.notna(buy_i_vol) and pd.notna(sell_i_vol) else np.nan,
            "BaseLegalNetMoneyProxy": buy_n_vol - sell_n_vol if pd.notna(buy_n_vol) and pd.notna(sell_n_vol) else np.nan,
            "BaseRealBuyerAvgVolume": buy_i_vol / buy_i_count if pd.notna(buy_i_vol) and pd.notna(buy_i_count) and buy_i_count > 0 else np.nan,
            "BaseRealSellerAvgVolume": sell_i_vol / sell_i_count if pd.notna(sell_i_vol) and pd.notna(sell_i_count) and sell_i_count > 0 else np.nan,
            "BaseRealBuyerPower": (buy_i_vol / buy_i_count) / (sell_i_vol / sell_i_count) if pd.notna(buy_i_vol) and pd.notna(sell_i_vol) and pd.notna(buy_i_count) and pd.notna(sell_i_count) and buy_i_count > 0 and sell_i_count > 0 and sell_i_vol > 0 else np.nan,
        })
        result.update(_best_limit_features(limits))
        result["BaseDataStatus"] = "OK"
        return result
    except Exception as exc:
        result["BaseDataStatus"] = "API_ERROR"
        result["BaseDataError"] = str(exc)
        return result


def enrich_options_with_base(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    base_col = find_base_column(df)
    if base_col is None:
        # Do not infer from option symbols. The pipeline remains valid but base intelligence is explicitly unavailable.
        df = df.copy()
        for col in ["BaseSymbol", "BaseInsCode", "BaseLast", "BaseClose", "BasePrevClose", "BasePriceChangePct",
                    "BaseVolume", "BaseValue", "BaseTradeCount", "BaseRealBuyVolume", "BaseRealSellVolume",
                    "BaseLegalBuyVolume", "BaseLegalSellVolume", "BaseRealBuyCount", "BaseRealSellCount",
                    "BaseLegalBuyCount", "BaseLegalSellCount", "BaseRealNetMoneyProxy", "BaseLegalNetMoneyProxy",
                    "BaseRealBuyerAvgVolume", "BaseRealSellerAvgVolume", "BaseRealBuyerPower", "BaseBestBidPrice",
                    "BaseBestBidVolume", "BaseBestAskPrice", "BaseBestAskVolume"]:
            df[col] = np.nan
        df["BaseDataStatus"] = "EXPLICIT_BASE_COLUMN_MISSING"
        return df, {"status": "EXPLICIT_BASE_COLUMN_MISSING", "base_column": None, "symbols": 0}

    df = df.copy()
    df["BaseSymbol"] = df[base_col].astype(str).str.strip()
    symbols = [s for s in df["BaseSymbol"].dropna().unique().tolist() if s and s.lower() != "nan"]
    client = TSETMCClient()
    rows = []
    for symbol in symbols:
        rows.append(collect_symbol(client, symbol))
        time.sleep(client.pause)
    base_df = pd.DataFrame(rows)
    if base_df.empty:
        df["BaseDataStatus"] = "NO_BASE_DATA"
        return df, {"status": "NO_BASE_DATA", "base_column": base_col, "symbols": len(symbols)}
    df = df.merge(base_df, on="BaseSymbol", how="left", suffixes=("", "_tsetmc"))
    return df, {
        "status": "OK",
        "base_column": str(base_col),
        "symbols": len(symbols),
        "resolved": int((base_df["BaseDataStatus"] == "OK").sum()),
        "failed": int((base_df["BaseDataStatus"] != "OK").sum()),
    }
