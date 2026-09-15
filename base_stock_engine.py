#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TSETMC underlying-stock intelligence engine for the Options Report pipeline.

This module enriches OptionSchool contracts with point-in-time underlying data.
It deliberately does NOT change V4.1 option scoring weights; it only supplies
validated underlying context and evidence.
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
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json,text/plain,*/*",
}

OPTION_ROOT_TO_BASE = {
    "ملت": "وبملت", "جار": "وتجارت", "صاد": "وبصادر", "ساما": "بساما",
    "ذوب": "ذوب", "تاصیکو": "تاصیکو", "شپنا": "شپنا", "هرم": "اهرم",
    "خود": "خودرو", "سپا": "خساپا", "شنا": "شینا", "خاب": "اخابر",
    "اطلس": "اطلس", "توان": "توان", "جوانه": "جوانه", "خبهمن": "خبهمن",
    "خسايا": "خسايا", "شستا": "شستا", "طعام": "طعام", "فرابورس": "فرابورس",
    "فزر": "فزر", "ملی": "ملی", "موج": "موج", "همتراز": "همتراز",
}


def option_symbol_to_base(symbol: str) -> tuple[str | None, str]:
    s = str(symbol).strip()
    if not s or s.lower() == "nan":
        return None, "OPTION_SYMBOL_MISSING"
    if s[0] not in {"ض", "ط"}:
        return None, "OPTION_PREFIX_NOT_RECOGNIZED"
    import re
    root = re.sub(r"\d+$", "", s[1:]).strip()
    if root in OPTION_ROOT_TO_BASE:
        return OPTION_ROOT_TO_BASE[root], "MAPPED"
    return None, "BASE_MAPPING_NOT_FOUND"


@dataclass
class TSETMCClient:
    timeout: int = 20
    retries: int = 3
    pause: float = 0.7

    def get_json(self, path: str) -> dict:
        last_error = None
        for attempt in range(self.retries):
            try:
                r = requests.get(BASE_URL + path, headers=HEADERS, timeout=self.timeout)
                r.raise_for_status()
                payload = r.json()
                if not isinstance(payload, dict):
                    raise RuntimeError("TSETMC پاسخ JSON شیء برنگرداند.")
                return payload
            except Exception as exc:
                last_error = exc
                if attempt + 1 < self.retries:
                    time.sleep(self.pause * (attempt + 1))
        raise RuntimeError(f"TSETMC API failure: {last_error}")

    def search_symbol(self, symbol: str) -> dict | None:
        from urllib.parse import quote
        data = self.get_json(f"/Instrument/GetInstrumentSearch/{quote(symbol, safe='')}")
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
        return self.get_json(f"/BestLimits/{ins_code}").get("bestLimits") or []

    def daily_history(self, ins_code: str) -> list[dict]:
        return self.get_json(f"/ClosingPrice/GetClosingPriceDailyList/{ins_code}/0").get("closingPriceDaily") or []

    def messages(self, ins_code: str) -> list[dict]:
        payload = self.get_json(f"/Msg/GetMsgByInsCode/{ins_code}")
        rows = payload.get("msg") or []
        return rows if isinstance(rows, list) else []


def _first(d: dict, *keys: str) -> Any:
    for key in keys:
        if key in d and d[key] not in (None, ""):
            return d[key]
    return np.nan


def _num(v: Any) -> float:
    try:
        if v is None or (isinstance(v, str) and not v.strip()):
            return np.nan
        return float(str(v).replace(",", "").replace("٬", ""))
    except Exception:
        return np.nan


def _rsi14(closes: list[float]) -> float:
    """RSI-14 using the same simple 14-period method as the legacy underlying engine.

    Direction is explicitly current minus previous; this avoids the sign inversion
    present in the older PowerShell implementation.
    """
    values = [float(x) for x in closes if pd.notna(x) and float(x) > 0]
    if len(values) < 15:
        return np.nan
    gains = 0.0
    losses = 0.0
    for i in range(1, 15):
        delta = values[i - 1] - values[i]
        # History is newest-first, so previous trading day's close is values[i].
        # Positive gain therefore occurs when the newer close is above the older close.
        if delta > 0:
            gains += delta
        else:
            losses += abs(delta)
    if losses == 0:
        return 100.0
    rs = (gains / 14.0) / (losses / 14.0)
    return 100.0 - (100.0 / (1.0 + rs))


def _history_features(history: list[dict], latest: float) -> dict:
    rows = [r for r in history if _num(_first(r, "pDrCotVal", "pl", "last")) > 0]
    rows.sort(key=lambda r: str(r.get("dEven", "")), reverse=True)
    closes = [_num(_first(r, "pDrCotVal", "pl", "last")) for r in rows]
    closes = [x for x in closes if pd.notna(x)]
    close5 = closes[5] if len(closes) >= 6 else np.nan
    sma5 = float(np.mean(closes[:5])) if len(closes) >= 5 else np.nan
    sma20 = float(np.mean(closes[:20])) if len(closes) >= 20 else np.nan
    ret5 = ((latest / close5) - 1.0) * 100.0 if pd.notna(latest) and pd.notna(close5) and close5 > 0 else np.nan
    rsi = _rsi14(closes)

    trend_points = 0
    if pd.notna(ret5):
        if ret5 > 3:
            trend_points += 1
        elif ret5 < -3:
            trend_points -= 1
    if pd.notna(sma5):
        trend_points += 1 if latest > sma5 else -1
    if pd.notna(sma20):
        trend_points += 1 if latest > sma20 else -1
    if pd.notna(rsi):
        if rsi >= 55:
            trend_points += 1
        elif rsi <= 45:
            trend_points -= 1
    bias = "BULLISH" if trend_points >= 2 else "BEARISH" if trend_points <= -2 else "NEUTRAL"

    return {
        "BaseReturn5D": ret5,
        "BaseSMA5": sma5,
        "BaseSMA20": sma20,
        "BaseRSI14": rsi,
        "BaseTrendPoints": trend_points,
        "BaseTrendBias": bias,
        "BaseHistoryRows": len(closes),
    }


def _best_limit_features(rows: list[dict]) -> dict:
    """Extract best bid/ask and their own quantities without mixing bid/ask fields."""
    best_bid_price = best_bid_volume = best_ask_price = best_ask_volume = np.nan
    for row in rows:
        bid_price = _num(_first(row, "pMeDem"))
        ask_price = _num(_first(row, "pMeOf"))
        bid_qty = _num(_first(row, "qTitMeDem"))
        ask_qty = _num(_first(row, "qTitMeOf"))
        if pd.notna(bid_price) and pd.isna(best_bid_price):
            best_bid_price, best_bid_volume = bid_price, bid_qty
        if pd.notna(ask_price) and pd.isna(best_ask_price):
            best_ask_price, best_ask_volume = ask_price, ask_qty
        if pd.notna(best_bid_price) and pd.notna(best_ask_price):
            break
    return {
        "Base_BestBidPrice": best_bid_price,
        "Base_BestBidVolume": best_bid_volume,
        "Base_BestAskPrice": best_ask_price,
        "Base_BestAskVolume": best_ask_volume,
    }


def _message_features(messages: list[dict]) -> dict:
    # Keep raw TSETMC evidence; do not infer positive/negative news sentiment.
    return {
        "BaseMessageCount": len(messages),
        "BaseMessages": messages[:5],
    }


def collect_symbol(client: TSETMCClient, symbol: str) -> dict:
    result = {"BaseSymbol": symbol, "BaseDataStatus": "UNKNOWN"}
    try:
        ins = client.search_symbol(symbol)
        if not ins:
            result["BaseDataStatus"] = "SYMBOL_NOT_FOUND"
            return result
        code = str(_first(ins, "insCode", "inscode"))
        if not code or code == "nan":
            result["BaseDataStatus"] = "INSCODE_MISSING"
            return result

        q = client.quote(code)
        ct = client.client_type(code)
        lim = client.best_limits(code)
        history = client.daily_history(code)
        try:
            messages = client.messages(code)
        except Exception:
            messages = []

        last = _num(_first(q, "pDrCotVal", "pl", "last"))
        close = _num(_first(q, "pClosing", "pc", "close"))
        prev = _num(_first(q, "priceYesterday", "py", "prevClose"))
        volume = _num(_first(q, "qTotTran5J", "tvol", "volume"))
        value = _num(_first(q, "qTotCap", "tval", "value"))
        trade_count = _num(_first(q, "zTotTran", "tno", "count"))

        real_buy_vol = _num(_first(ct, "buy_I_Volume", "buyIVolume", "buy_I_Vol"))
        real_sell_vol = _num(_first(ct, "sell_I_Volume", "sellIVolume", "sell_I_Vol"))
        legal_buy_vol = _num(_first(ct, "buy_N_Volume", "buyNVolume", "buy_N_Vol"))
        legal_sell_vol = _num(_first(ct, "sell_N_Volume", "sellNVolume", "sell_N_Vol"))
        real_buy_count = _num(_first(ct, "buy_CountI", "buyICount", "buy_I_Count"))
        real_sell_count = _num(_first(ct, "sell_CountI", "sellICount", "sell_I_Count"))
        legal_buy_count = _num(_first(ct, "buy_CountN", "buyNCount", "buy_N_Count"))
        legal_sell_count = _num(_first(ct, "sell_CountN", "sellNCount", "sell_N_Count"))

        real_net_volume = real_buy_vol - real_sell_vol if pd.notna(real_buy_vol) and pd.notna(real_sell_vol) else np.nan
        legal_net_volume = legal_buy_vol - legal_sell_vol if pd.notna(legal_buy_vol) and pd.notna(legal_sell_vol) else np.nan
        real_buyer_avg = real_buy_vol / real_buy_count if pd.notna(real_buy_vol) and pd.notna(real_buy_count) and real_buy_count > 0 else np.nan
        real_seller_avg = real_sell_vol / real_sell_count if pd.notna(real_sell_vol) and pd.notna(real_sell_count) and real_sell_count > 0 else np.nan
        real_buyer_power = real_buyer_avg / real_seller_avg if pd.notna(real_buyer_avg) and pd.notna(real_seller_avg) and real_seller_avg > 0 else np.nan

        result.update({
            "BaseInsCode": code,
            "BaseSymbolResolved": str(_first(ins, "lVal18AFC")),
            "BaseInstrumentName": str(_first(ins, "lVal30")),
            "BaseAsOf": str(_first(q, "dEven")),
            "BaseLast": last,
            "BaseClose": close,
            "BasePrevClose": prev,
            "BasePriceChangePct": ((last - prev) / prev * 100) if pd.notna(last) and pd.notna(prev) and prev else np.nan,
            "BaseVolume": volume,
            "BaseValue": value,
            "BaseTradeCount": trade_count,
            "BaseRealBuyVolume": real_buy_vol,
            "BaseRealSellVolume": real_sell_vol,
            "BaseLegalBuyVolume": legal_buy_vol,
            "BaseLegalSellVolume": legal_sell_vol,
            "BaseRealBuyCount": real_buy_count,
            "BaseRealSellCount": real_sell_count,
            "BaseLegalBuyCount": legal_buy_count,
            "BaseLegalSellCount": legal_sell_count,
            "BaseRealNetVolume": real_net_volume,
            "BaseLegalNetVolume": legal_net_volume,
            "BaseRealBuyerAvgVolume": real_buyer_avg,
            "BaseRealSellerAvgVolume": real_seller_avg,
            "BaseRealBuyerPower": real_buyer_power,
        })
        result.update(_history_features(history, last))
        result.update(_best_limit_features(lim))
        result.update(_message_features(messages))
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
        df = df.merge(pd.DataFrame(rows), on="BaseSymbol", how="left", suffixes=("", "_tsetmc"))
    else:
        df["BaseDataStatus"] = "BASE_MAPPING_NOT_FOUND"

    base_status = df.get("BaseDataStatus", pd.Series(index=df.index, dtype=object))
    resolved_symbols = int(df.loc[base_status.eq("OK"), "BaseSymbol"].nunique()) if "BaseSymbol" in df.columns else 0
    failed_symbols = max(0, len(symbols) - resolved_symbols)
    mapping_missing = int(df["BaseMappingStatus"].eq("BASE_MAPPING_NOT_FOUND").sum())

    return df, {
        "status": "OK" if resolved_symbols else ("TSETMC_NO_VALID_RESPONSE" if symbols else "BASE_MAPPING_NOT_FOUND"),
        "base_column": "نماد (OptionSchool) + Master Mapping",
        "symbols": len(symbols),
        "resolved": resolved_symbols,
        "failed": failed_symbols,
        "mapping_not_found": mapping_missing,
    }
