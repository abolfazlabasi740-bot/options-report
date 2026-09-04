#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TSETMC base-stock intelligence engine for the Options Report pipeline."""
from __future__ import annotations
import time
from dataclasses import dataclass
from typing import Any
import numpy as np
import pandas as pd
import requests

BASE_URL = "https://cdn.tsetmc.com/api"
HEADERS = {"User-Agent":"Mozilla/5.0","Accept":"application/json,text/plain,*/*"}
OPTION_ROOT_TO_BASE = {"ملت":"وبملت","جار":"وتجارت","صاد":"وبصادر","ساما":"بساما","ذوب":"ذوب","تاصیکو":"تاصیکو","شپنا":"شپنا","هرم":"اهرم","خود":"خودرو","سپا":"خساپا","شنا":"شینا","خاب":"اخابر","اطلس":"اطلس","توان":"توان","جوانه":"جوانه","خبهمن":"خبهمن","خسايا":"خسايا","شستا":"شستا","طعام":"طعام","فرابورس":"فرابورس","فزر":"فزر","ملی":"ملی","موج":"موج","همتراز":"همتراز"}

def option_symbol_to_base(symbol: str) -> tuple[str | None, str]:
    s = str(symbol).strip()
    if not s or s.lower() == "nan": return None, "OPTION_SYMBOL_MISSING"
    if s[0] not in {"ض","ط"}: return None, "OPTION_PREFIX_NOT_RECOGNIZED"
    import re
    root = re.sub(r"\d+$","",s[1:]).strip()
    return (OPTION_ROOT_TO_BASE[root],"MAPPED") if root in OPTION_ROOT_TO_BASE else (None,"BASE_MAPPING_NOT_FOUND")

@dataclass
class TSETMCClient:
    timeout:int=20; retries:int=3; pause:float=0.7
    def get_json(self,path:str)->dict:
        last_error=None
        for attempt in range(self.retries):
            try:
                r=requests.get(BASE_URL+path,headers=HEADERS,timeout=self.timeout); r.raise_for_status(); p=r.json()
                if not isinstance(p,dict): raise RuntimeError("TSETMC پاسخ JSON شیء برنگرداند.")
                return p
            except Exception as exc:
                last_error=exc
                if attempt+1<self.retries: time.sleep(self.pause*(attempt+1))
        raise RuntimeError(f"TSETMC API failure: {last_error}")
    def search_symbol(self,symbol:str)->dict|None:
        data=self.get_json(f"/Instrument/GetInstrumentSearch/{requests.utils.quote(symbol,safe='')}")
        rows=data.get("instrumentSearch") or data.get("instrumentSearchResult") or []
        if not isinstance(rows,list): return None
        exact=[r for r in rows if str(r.get("lVal18AFC","")).strip()==symbol]
        return exact[0] if exact else (rows[0] if rows else None)
    def quote(self,ins_code:str)->dict: return self.get_json(f"/ClosingPrice/GetClosingPriceInfo/{ins_code}").get("closingPriceInfo",{})
    def client_type(self,ins_code:str)->dict: return self.get_json(f"/ClientType/GetClientType/{ins_code}/1/0").get("clientType",{})
    def best_limits(self,ins_code:str)->list[dict]: return self.get_json(f"/BestLimits/{ins_code}").get("bestLimits") or []

def _first(d:dict,*keys:str)->Any:
    for k in keys:
        if k in d and d[k] not in (None,""): return d[k]
    return np.nan

def _num(v:Any)->float:
    try:
        if v is None or (isinstance(v,str) and not v.strip()): return np.nan
        return float(str(v).replace(",","").replace("٬",""))
    except Exception: return np.nan

def _best_limit_features(rows:list[dict])->dict:
    bids=[]; asks=[]
    for row in rows:
        d=_num(_first(row,"pMeDem")); a=_num(_first(row,"pMeOf")); q=_num(_first(row,"qTitMeDem","qTitMeOf","quantity","q"))
        if not np.isnan(d): bids.append((d,q))
        if not np.isnan(a): asks.append((a,q))
    return {"Base_BestBidPrice":bids[0][0] if bids else np.nan,"Base_BestBidVolume":bids[0][1] if bids else np.nan,"Base_BestAskPrice":asks[0][0] if asks else np.nan,"Base_BestAskVolume":asks[0][1] if asks else np.nan}

def collect_symbol(client:TSETMCClient,symbol:str)->dict:
    result={"BaseSymbol":symbol,"BaseDataStatus":"UNKNOWN"}
    try:
        ins=client.search_symbol(symbol)
        if not ins: result["BaseDataStatus"]="SYMBOL_NOT_FOUND"; return result
        code=str(_first(ins,"insCode","inscode"))
        if not code or code=="nan": result["BaseDataStatus"]="INSCODE_MISSING"; return result
        q=client.quote(code); ct=client.client_type(code); lim=client.best_limits(code)
        last=_num(_first(q,"pDrCotVal","pl","last")); close=_num(_first(q,"pClosing","pc","close")); prev=_num(_first(q,"priceYesterday","py","prevClose"))
        bv=_num(_first(q,"qTotTran5J","tvol","volume")); val=_num(_first(q,"qTotCap","tval","value")); tr=_num(_first(q,"zTotTran","tno","count"))
        biv=_num(_first(ct,"buy_I_Volume","buyIVolume","buy_I_Vol")); siv=_num(_first(ct,"sell_I_Volume","sellIVolume","sell_I_Vol")); bnv=_num(_first(ct,"buy_N_Volume","buyNVolume","buy_N_Vol")); snv=_num(_first(ct,"sell_N_Volume","sellNVolume","sell_N_Vol"))
        bic=_num(_first(ct,"buy_CountI","buyICount","buy_I_Count")); sic=_num(_first(ct,"sell_CountI","sellICount","sell_I_Count")); bnc=_num(_first(ct,"buy_CountN","buyNCount","buy_N_Count")); snc=_num(_first(ct,"sell_CountN","sellNCount","sell_N_Count"))
        result.update({"BaseInsCode":code,"BaseSymbolResolved":str(_first(ins,"lVal18AFC")),"BaseLast":last,"BaseClose":close,"BasePrevClose":prev,"BasePriceChangePct":((last-prev)/prev*100) if pd.notna(last) and pd.notna(prev) and prev else np.nan,"BaseVolume":bv,"BaseValue":val,"BaseTradeCount":tr,"BaseRealBuyVolume":biv,"BaseRealSellVolume":siv,"BaseLegalBuyVolume":bnv,"BaseLegalSellVolume":snv,"BaseRealBuyCount":bic,"BaseRealSellCount":sic,"BaseLegalBuyCount":bnc,"BaseLegalSellCount":snc,"BaseRealNetMoneyProxy":biv-siv if pd.notna(biv) and pd.notna(siv) else np.nan,"BaseLegalNetMoneyProxy":bnv-snv if pd.notna(bnv) and pd.notna(snv) else np.nan,"BaseRealBuyerAvgVolume":biv/bic if pd.notna(biv) and pd.notna(bic) and bic>0 else np.nan,"BaseRealSellerAvgVolume":siv/sic if pd.notna(siv) and pd.notna(sic) and sic>0 else np.nan,"BaseRealBuyerPower":(biv/bic)/(siv/sic) if pd.notna(biv) and pd.notna(siv) and pd.notna(bic) and pd.notna(sic) and bic>0 and sic>0 and siv>0 else np.nan})
        result.update(_best_limit_features(lim)); result["BaseDataStatus"]="OK"
    except Exception as exc: result["BaseDataStatus"]="API_ERROR"; result["BaseDataError"]=str(exc)
    return result

def enrich_options_with_base(df:pd.DataFrame)->tuple[pd.DataFrame,dict]:
    df=df.copy()
    if "نماد" not in df.columns: raise RuntimeError("ستون نماد در فایل OptionSchool موجود نیست.")
    mapped=df["نماد"].map(option_symbol_to_base)
    df["BaseSymbol"]=mapped.map(lambda x:x[0]); df["BaseMappingStatus"]=mapped.map(lambda x:x[1])
    symbols=sorted({s for s in df["BaseSymbol"].dropna().tolist() if s})
    client=TSETMCClient(); rows=[]
    for symbol in symbols:
        rows.append(collect_symbol(client,symbol)); time.sleep(client.pause)
    if rows: df=df.merge(pd.DataFrame(rows),on="BaseSymbol",how="left",suffixes=("","_tsetmc"))
    else: df["BaseDataStatus"]="BASE_MAPPING_NOT_FOUND"
    base_status=df.get("BaseDataStatus",pd.Series(index=df.index,dtype=object))
    resolved_symbols=int(df.loc[base_status.eq("OK"),"BaseSymbol"].nunique()) if "BaseSymbol" in df.columns else 0
    failed_symbols=max(0,len(symbols)-resolved_symbols)
    return df,{"status":"OK" if resolved_symbols else ("TSETMC_NO_VALID_RESPONSE" if symbols else "BASE_MAPPING_NOT_FOUND"),"base_column":"نماد (OptionSchool) + Master Mapping","symbols":len(symbols),"resolved":resolved_symbols,"failed":failed_symbols,"mapping_not_found":int(df["BaseMappingStatus"].eq("BASE_MAPPING_NOT_FOUND").sum())}
