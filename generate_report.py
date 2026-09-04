#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Canonical V4 runner: OptionSchool -> scope -> mapping -> guard -> scoring -> report."""
import hashlib
import os
import sys
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import numpy as np
import pandas as pd
import rank_options_live as scoring_engine
from base_stock_engine import enrich_options_with_base
from v4_runtime_guard import enforce_v4_invariants, MIN_LEVERAGE, V4_PROTOCOL

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_REPORT = BASE_DIR / "output_options_report.md"
OUTPUT_TOP = BASE_DIR / "output_options_top15.csv"
OUTPUT_BASE = BASE_DIR / "output_base_stock.csv"
OPTIONSCHOOL_URL = "https://s3.optionschool24.com/export/excel?type=1"

def now_tehran():
    from zoneinfo import ZoneInfo
    return datetime.now(ZoneInfo("Asia/Tehran"))

def download_latest_optionschool():
    target = BASE_DIR / "optionschool24_latest.xlsx"
    started = now_tehran()
    req = Request(OPTIONSCHOOL_URL, headers={"User-Agent": "OptionsReport-V4/1.0"})
    try:
        with urlopen(req, timeout=60) as response:
            data = response.read()
    except (HTTPError, URLError) as exc:
        raise RuntimeError(f"دریافت Optionschool24 ناموفق بود: {exc}") from exc
    finished = now_tehran()
    if len(data) < 1024 or not data.startswith(b"PK"):
        raise RuntimeError("فایل XLSX دریافتی Optionschool24 معتبر نیست.")
    target.write_bytes(data)
    return target, {"source":"OptionSchool24","filename":target.name,"download_completed_display":finished.strftime("%Y-%m-%d %H:%M:%S %Z"),"bytes":len(data),"sha256":hashlib.sha256(data).hexdigest()}

def find_input(explicit=None):
    if explicit:
        p = Path(explicit)
        if not p.is_absolute(): p = BASE_DIR / p
        if not p.is_file(): raise RuntimeError(f"فایل ورودی یافت نشد: {p}")
        return p, {"source":"Explicit input","filename":p.name,"download_completed_display":"ثبت نشده","bytes":p.stat().st_size,"sha256":hashlib.sha256(p.read_bytes()).hexdigest()}
    return download_latest_optionschool()

def run_v4_pipeline(input_path, output_md="output_options_report.md", symbol_prefix=""):
    df_raw = pd.read_excel(input_path)
    total_initial = len(df_raw)
    if "نماد" not in df_raw.columns: raise RuntimeError("ستون «نماد» در فایل OptionSchool موجود نیست.")
    df_raw["نماد"] = df_raw["نماد"].astype(str).str.strip()

    if symbol_prefix:
        before = len(df_raw)
        df_raw = df_raw[df_raw["نماد"].str.startswith(symbol_prefix.strip(), na=False)].copy()
        print(f"Scope={symbol_prefix} | before={before} | after={len(df_raw)}")
        if df_raw.empty: raise RuntimeError(f"برای «{symbol_prefix}» قراردادی در فایل OptionSchool یافت نشد.")
    else:
        print("Scope=کل بازار")

    df_filtered, guard = enforce_v4_invariants(df_raw, leverage_key="اهرم", drop_invalid=True)
    print(f"V4 Guard: input={guard['input_rows']} | passed={guard['output_rows']} | dropped={guard['dropped_rows']}")
    if df_filtered.empty: raise RuntimeError(f"هیچ قراردادی با اهرم >= {MIN_LEVERAGE} باقی نماند.")

    df_enriched, base_audit = enrich_options_with_base(df_filtered)
    base_cols = [c for c in ["BaseSymbol","BaseInsCode","BaseLast","BaseClose","BasePrevClose","BasePriceChangePct","BaseVolume","BaseValue","BaseTradeCount","BaseRealBuyVolume","BaseRealSellVolume","BaseLegalBuyVolume","BaseLegalSellVolume","BaseRealBuyCount","BaseRealSellCount","BaseLegalBuyCount","BaseLegalSellCount","BaseRealNetMoneyProxy","BaseLegalNetMoneyProxy","BaseRealBuyerAvgVolume","BaseRealSellerAvgVolume","BaseRealBuyerPower","Base_BestBidPrice","Base_BestBidVolume","Base_BestAskPrice","Base_BestAskVolume","BaseDataStatus"] if c in df_enriched.columns]
    if base_cols:
        df_enriched[base_cols].drop_duplicates(subset=["BaseSymbol"] if "BaseSymbol" in df_enriched.columns else None).to_csv(OUTPUT_BASE,index=False,encoding="utf-8-sig")

    scored = scoring_engine.score_dataframe(df_enriched) if hasattr(scoring_engine,"score_dataframe") else df_enriched
    if "FinalScore" not in scored.columns: raise RuntimeError("FinalScore توسط موتور V4 تولید نشد.")
    try: top_count = int(os.getenv("REPORT_TOP_COUNT","15"))
    except ValueError: raise RuntimeError("REPORT_TOP_COUNT نامعتبر است.")
    if top_count < 1: raise RuntimeError("REPORT_TOP_COUNT باید حداقل 1 باشد.")
    top = scored.sort_values(["FinalScore","حجم معاملات"],ascending=[False,False]).head(top_count).copy()
    top.insert(0,"رتبه",range(1,len(top)+1))

    generated = now_tehran()
    scope = symbol_prefix or "کل بازار"
    lines = [
        "# گزارش تحلیل و رتبه‌بندی قراردادهای اختیار معامله — V4",
        f"**پروتکل:** `{V4_PROTOCOL}` | **حداقل اهرم:** `{MIN_LEVERAGE}` | **دامنه:** `{scope}`",
        "",
        "| رتبه | نماد | قیمت اعمال | آخرین قیمت | سر به سر | قیمت پایه | اهرم | فاصله تا سر به سر | سررسید | روزهای تقویمی | امتیاز |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---|---:|---:|"
    ]
    for _, r in top.iterrows():
        lines.append(f"| {r.get('رتبه','')} | {r.get('نماد','')} | {r.get('قیمت اعمال','')} | {r.get('آخرین قیمت','')} | {r.get('سر به سر','')} | {r.get('قیمت سهم پایه','')} | {r.get('اهرم','')} | {r.get('اختلاف تا سر به سر','')} | {r.get('تاریخ سررسید','')} | {r.get('روزهای تقویمی','')} | {r.get('FinalScore','')} |")

    audit = "\n## شناسنامه گزارش\n" + f"- منبع: {metadata['source']}\n- فایل مبنا: {metadata['filename']}\n- زمان پایان دریافت: {metadata['download_completed_display']}\n- حجم فایل: {metadata['bytes']} bytes\n- SHA-256: `{metadata['sha256']}`\n- ردیف اولیه: {total_initial}\n- ردیف پس از Scope: {guard['input_rows']}\n- ردیف پس از Guard: {guard['output_rows']}\n- قراردادهای گزارش‌شده: {len(top)}\n- زمان تولید: {generated.strftime('%Y-%m-%d %H:%M:%S %Z')}\n"
    base = "\n## سهم پایه\n" + f"- وضعیت: {base_audit.get('status','UNKNOWN')}\n- نمادهای پایه: {base_audit.get('symbols',0)}\n- پاسخ معتبر TSETMC: {base_audit.get('resolved',0)}\n- بدون پاسخ معتبر: {base_audit.get('failed',0)}\n"
    report = "\n".join(lines) + audit + base
    Path(output_md).write_text(report,encoding="utf-8")
    top.to_csv(OUTPUT_TOP,index=False,encoding="utf-8-sig")
    print(f"[OK] V4 report: {output_md} | rows={len(top)}")
    return report

if __name__ == "__main__":
    explicit = sys.argv[1] if len(sys.argv)>1 else None
    prefix = os.getenv("REPORT_SYMBOL_PREFIX","").strip()
    input_path, metadata = find_input(explicit)
    print(f"Canonical input: {input_path.name}")
    print(run_v4_pipeline(input_path,symbol_prefix=prefix))
