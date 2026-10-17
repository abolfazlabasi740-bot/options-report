# PREMIUM FALLBACK ENGINE (holiday-safe, 3 layers)
import glob as _glob, os as _os
from datetime import datetime as _dt


def _num(x):
    """تبدیل امن به float: عدد، رشته، یا dict وبسرویس (p/pval/val) — ناموفق یعنی None."""
    if x is None:
        return None
    if isinstance(x, dict):
        for k in ("p", "pval", "val", "price", "last", "closing"):
            if k in x:
                return _num(x[k])
        return None
    if isinstance(x, (int, float)):
        return float(x)
    try:
        return float(str(x).replace(",", "").strip())
    except ValueError:
        return None

PREMIUM_SNAPSHOT_DIR = "output/reports/lmp"
_INS_CODE_CACHE = {}
_SNAPSHOT_PREMIUMS = None
_FALLBACK_STATS = {"L1": 0, "L2": 0, "L3": 0, "MISS": 0}

def _resolve_ins_code(key, requests, SEARCH_URL, HEADERS):
    if not key:
        return None
    if key in _INS_CODE_CACHE:
        return _INS_CODE_CACHE[key]
    ic = None
    try:
        r = requests.get(SEARCH_URL.format(key), headers=HEADERS, timeout=10)
        res = (r.json() or {}).get("instrumentSearch") or []
        if res:
            ic = str(res[0].get("insCode"))
    except Exception:
        pass
    _INS_CODE_CACHE[key] = ic
    return ic

def _load_snapshot_premiums():
    global _SNAPSHOT_PREMIUMS
    if _SNAPSHOT_PREMIUMS is not None:
        return _SNAPSHOT_PREMIUMS
    files = sorted(_glob.glob(_os.path.join(PREMIUM_SNAPSHOT_DIR, "lmp_*.json")), reverse=True)
    for f in files:
        try:
            with open(f, encoding="utf-8") as fh:
                data = json.load(fh)
            snaps = data.get("snapshots") or data.get("contracts") or []
            m = {}
            for s in snaps:
                last = _num(s.get("buyLastPrice")) or 0
                close = _num(s.get("buyClosingPrice")) or 0
                if last > 0 or close > 0:
                    m[s.get("buyInstrumentName")] = (close, last)
            if m:
                m["__data_date__"] = data.get("data_date") or _os.path.basename(f)[4:12]
                _SNAPSHOT_PREMIUMS = m
                return m
        except Exception:
            continue
    _SNAPSHOT_PREMIUMS = {}
    return _SNAPSHOT_PREMIUMS

def make_resolver(requests, SEARCH_URL, HEADERS, get_price_info):
    """resolve_premium را با وابستگیهای lmp_scanner میسازد (بدون import دایرهای)."""
    def resolve_premium(option):
        last = _num(option.get("buyLastPrice")) or 0
        close = _num(option.get("buyClosingPrice")) or 0
        if last > 0 or close > 0:
            _FALLBACK_STATS["L1"] += 1
            return (close or last, "live")
        name = option.get("buyInstrumentName")
        ic = _resolve_ins_code(option.get("buyInstrumentId") or name,
                               requests, SEARCH_URL, HEADERS)
        if ic:
            try:
                info = get_price_info(ic)
                if info:
                    p = _num(info.get("closing_price")) or _num(info.get("pClosing")) or 0
                    if p > 0:
                        _FALLBACK_STATS["L2"] += 1
                        return (p, "inscode_fallback")
            except Exception:
                pass
        snaps = _load_snapshot_premiums()
        if name and name in snaps:
            _FALLBACK_STATS["L3"] += 1
            return (snaps[name][0] or snaps[name][1], "snapshot_fallback")
        _FALLBACK_STATS["MISS"] += 1
        return (None, "none")
    return resolve_premium
