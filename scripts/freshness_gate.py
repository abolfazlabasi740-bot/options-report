# -*- coding: utf-8 -*-
"""دروازه تازگی داده v2.2 — Proxy به data_source_policy (تکمنطق رژیم).
منطق تقویم/ساعت فقط در data_source_policy نگهداری میشود (پچ تقویم ۹/۹، V4).
v2.2: تشخیص مقاوم زمان snapshot (فیلد ISO/epoch/yyyymmdd یا نام فایل) + منطقه تهران."""
import json, os, re
from datetime import datetime, timezone, timedelta
from data_source_policy import get_data_mode as _resolve_mode, POLICY_VERSION

TZ = timezone(timedelta(hours=3, minutes=30))  # تهران +03:30

def market_is_open(now=None):
    return _resolve_mode(now)[0] == 'LIVE'

def get_data_mode(now=None):
    return _resolve_mode(now)[0]

def _resolve_snapshot_ts(snap, snap_path, base_ts_field='fetched_at'):
    """منبع زمان snapshot به ترتیب قطعیت:
    فیلد معیار → کلیدهای رایج (ISO/epoch/yyyymmdd) → الگوی نام فایل lmp_YYYYMMDD_HHMM.
    خروجی: (datetime آگاه از تهران یا None, نام منبع)"""
    if not isinstance(snap, dict):
        snap = {}
    keys = [base_ts_field] + [k for k in
        ("fetched_at", "fetchedAt", "timestamp", "ts", "time", "datetime", "updated_at")
        if k != base_ts_field]
    for key in keys:
        v = snap.get(key)
        if isinstance(v, str):
            try:
                dt = datetime.fromisoformat(v.strip())
            except ValueError:
                continue
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=TZ)
            return dt, key
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            if 20000101 <= int(v) <= 21001231:      # قالب yyyymmdd
                s = str(int(v))
                return datetime(int(s[:4]), int(s[4:6]), int(s[6:8]), tzinfo=TZ), key + "(yyyymmdd)"
            sec = float(v)
            if sec > 1e12:                          # میلی‌ثانیه
                sec /= 1000.0
            return datetime.fromtimestamp(sec, TZ), key + "(epoch)"
    m = re.search(r"(\d{8})_(\d{4})", os.path.basename(snap_path))
    if m:
        d, t = m.groups()
        return datetime(int(d[:4]), int(d[4:6]), int(d[6:8]),
                        int(t[:2]), int(t[2:4]), tzinfo=TZ), "filename"
    return None, "none"

def gate_snapshot(snap_path, base_ts_field='fetched_at', ttl_live_min=30):
    """LIVE: snapshot باید تازه باشد (≤ ttl دقیقه).
    EOD: snapshot پایان بازار همان روز کافی است — فقط برچسب EOD میخورد."""
    with open(snap_path, encoding='utf-8') as f:
        snap = json.load(f)
    mode, _reason = _resolve_mode()
    fetched, ts_source = _resolve_snapshot_ts(snap, snap_path, base_ts_field)
    if fetched is None:
        return {'pass': False, 'mode': mode, 'ts_source': 'none',
                'action': 'بازبینی ساختار snapshot — فیلد زمان یافت نشد',
                'reason': 'نه فیلد زمان معتبری در snapshot هست و نه الگوی زمان در نام فایل'}
    age_min = (datetime.now(TZ) - fetched).total_seconds() / 60
    out = {'pass': True, 'mode': mode, 'age_min': round(age_min, 1),
           'ts_source': ts_source, 'fetched_at': fetched.isoformat(),
           'policy_version': POLICY_VERSION,
           'basis': 'قیمت پایانی رسمی' if mode == 'EOD' else 'Pull زنده TSETMC'}
    if mode == 'LIVE' and age_min > ttl_live_min:
        out.update({'pass': False,
                    'action': 'python3 scripts/fetch_tsetmc_live.py',
                    'reason': 'داده کهنه در ساعت معامله — pull زنده اجباری'})
    return out
