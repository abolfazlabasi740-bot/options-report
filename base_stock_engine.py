#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TSETMC base-stock intelligence engine for the Options Report pipeline.

Base mapping is driven by the OptionSchool option symbol and the project's
explicit mapping rules. It does not guess an underlying from price fields.
"""
from __future__ import annotations
import time
from dataclasses import dataclass
from typing import Any
import numpy as np
import pandas as pd
import requests

BASE_URL = "https://cdn.tsetmc.com/api"
HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json,text/plain,*/*"}

# Explicit project mapping for the option roots currently known in OptionSchool.
# The numeric contract suffix is removed before lookup. Unknown roots are not guessed.
OPTION_ROOT_TO_BASE = {
    "ملت": "وبملت",
    "جار": "وتجارت",
    "صاد": "وبصادر",
    "ساما": "بساما",
    "ذوب": "ذوب",
    "تاصیکو": "تاصیکو",
    "شپنا": "شپنا",
    "هرم": "اهرم",
    "خود": "خودرو",
    "سپا": "خساپا",
    "شنا": "شینا",
    "خاب": "اخابر",
    "اطلس": "اطلس",
    "توان": "توان",
    "جوانه": "جوانه",
    "خبهمن": "خبهمن",
    "خسايا": "خسايا",
    "شستا": "شستا",
    "طعام": "طعام",
    "فرابورس": "فرابورس",
    "فزر": "فزر",
    "ملی": "ملی",
    "موج": "موج",
    "همتراز": "همتراز",
}


def option_symbol_to_base(symbol: str) -> tuple[str | None, str]:
    """Return (base_symbol, status) from an OptionSchool option symbol.

    ض and ط identify call/put in the project's convention. The remaining root
    is matched only against the explicit mapping table above; no fuzzy matching.
    """
    s = str(symbol).strip()
    if not s or s.lower() == "nan":
        return None, "OPTION_SYMBOL_MISSING"
    if s[0] not in {"ض", "ط"}:
        return None, "OPTION_PREFIX_NOT_RECOGNIZED"
    root = s[1:]
    # Strip only the trailing contract number. Everything before it is preserved.
    import re
    root = re.sub(r"\d+$", "", root).strip()
    if root in OPTION_ROOT_TO_BASE:
        return OPTION_ROOT_TO_BASE[root], "MAPPED"
    return None, "BASE_MAPPING_NOT_FOUND"


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
            except Exception as exc:
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
        return exact[0] if exact else (rows[0] if rows else None)

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


def _best_limit_features(rows: list[dict]) -> dict:
    bids, asks = [], []
    for row in rows:
        demand = _num(_first(row, "pMeDem"))
        offer = _num(_first(row, "pMeOf"))
        qty = _num(_first(row, "qTitMeDem", "qTitMeOf", "quantity", "q"))
        if not np.isnan(demand): bids.append((demand, qty))
        if not np.isnan(offer): asks.append((offer, qty))
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
            "BaseLast": last, "BaseClose": close, "BasePrevClose": prev,
            "BasePriceChangePct": ((last-prev)/prev*100) if pd.notna(last) and pd.notna(prev) and prev else np.nan,
            "BaseVolume": volume, "BaseValue": value, "BaseTradeCount": trades,
            "BaseRealBuyVolume": buy_i_vol, "BaseRealSellVolume": sell_i_vol,
            "BaseLegalBuyVolume": buy_n_vol, "BaseLegalSellVolume": sell_n_vol,
            "BaseRealBuyCount": buy_i_count, "BaseRealSellCount": sell_i_count,
            "BaseLegalBuyCount": buy_n_count, "BaseLegalSellCount": sell_n_count,
            "BaseRealNetMoneyProxy": buy_i_vol-sell_i_vol if pd.notna(buy_i_vol) and pd.notna(sell_i_vol) else np.nan,
            "BaseLegalNetMoneyProxy": buy_n_vol-sell_n_vol if pd.notna(buy_n_vol) and pd.notna(sell_n_vol) else np.nan,
            "BaseRealBuyerAvgVolume": buy_i_vol/buy_i_count if pd.notna(buy_i_vol) and pd.notna(buy_i_count) and buy_i_count>0 else np.nan,
            "BaseRealSellerAvgVolume": sell_i_vol/sell_i_count if pd.notna(sell_i_vol) and pd.notna(sell_i_count) and sell_i_count>0 else np.nan,
            "BaseRealBuyerPower": (buy_i_vol/buy_i_count)/(sell_i_vol/sell_i_count) if pd.notna(buy_i_vol) and pd.notna(sell_i_vol) and pd.notna(buy_i_count) and pd.notna(sell_i_count) and buy_i_count>0 and sell_i_count>0 and sell_i_vol>0 else np.nan,
        })
        result.update(_best_limit_features(limits))
        result["BaseDataStatus"] = "OK"
    except Exception as exc:
        result["BaseDataStatus"] = "API_ERROR"
        result["BaseDataError"] = str(exc)
    return result


def enrich_options_with_base(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    df = df.copy()
    if "نماد" not in df.columns:
        raise RuntimeError("ستون نماد در فایل OptionSchool موجود نیست.")
    mapped = df["نماد"].map(option_symbol_to_base)
    df["BaseSymbol"] = mapped.map(lambda x: x[0])
    df["BaseMappingStatus"] = mapped.map(lambda x: x[1])
    symbols = sorted({s for s in df["BaseSymbol"].dropna().tolist() if s})
    client = TSETMCClient()
    rows = []
    for symbol in symbols:
        rows.append(collect_symbol(client, symbol))
        time.sleep(client.pause)
    if rows:
        base_df = pd.DataFrame(rows)
        df = df.merge(base_df, on="BaseSymbol", how="left", suffixes=("", "_tsetmc"))
    else:
        df["BaseDataStatus"] = "BASE_MAPPING_NOT_FOUND"
    ok = int((df.get("BaseDataStatus", pd.Series(index=df.index, dtype=object)) == "OK").sum())
    failed = int(len(symbols) - ok)
    status = "OK" if symbols and ok > 0 else ("TSETMC_NO_VALID_RESPONSE" if symbols else "BASE_MAPPING_NOT_FOUND")
    return df, {
        "status": status,
        "base_column": "نماد (OptionSchool) + Master Mapping",
        "symbols": len(symbols),
        "resolved": ok,
        "failed": failed,
        "mapping_not_found": int(df["BaseMappingStatus"].eq("BASE_MAPPING_NOT_FOUND").sum()),
    }
