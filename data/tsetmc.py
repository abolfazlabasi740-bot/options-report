# -*- coding: utf-8 -*-
# data/tsetmc.py — موتور دریافت و تفکیک داده TSETMC (لایه ۱: داده)
# منبع: MarketWatchPlus.aspx?h=0&r=0 — داده خام، بدون دستکاری، با زمان دریافت
# خروجی: مخزن واحد — لیست سهام، لیست اختیار معامله، سایر ابزارها + نسخه خام
# قواعد: هیچ عدد فرضی؛ هر خروجی دارای run_id و generated_at؛ تفکیک لحظه‌ای
import gzip
import argparse
import hashlib
import json
import os
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

# === PATCH: transparent gzip decode + real MarketWatchPlus validation (1405/07/24) ===
import gzip as _gzip
import re as _re

class _GzipAwareResponse:
    """Wraps a urllib response and auto-decompresses gzip payloads (magic \x1f\x8b).
    Confirmed: old.tsetmc.com ALWAYS returns gzip even with Accept-Encoding: identity."""
    def __init__(self, resp):
        self._resp = resp
        self.status = getattr(resp, 'status', None) or resp.getcode()
        self.headers = resp.headers
        self.url = getattr(resp, 'url', '')
        raw = resp.read()
        if raw[:2] == b'\x1f\x8b':
            raw = _gzip.decompress(raw)
        self._raw = raw
        try: resp.close()
        except Exception: pass
    def read(self):
        return self._raw
    def close(self):
        pass
    def __enter__(self):
        return self
    def __exit__(self, *exc):
        return False


def _mw_is_valid(text):
    """Validate the structural signature of a MarketWatchPlus payload.

    Do not require a fixed byte size: valid snapshots can vary by market state.
    Reject HTML/error pages by requiring section separators and instrument IDs.
    """
    return (
        isinstance(text, str)
        and text.count('@') >= 2
        and bool(_re.search(r'(?<!\d)\d{15,}(?!\d)', text))
    )

try:
    from zoneinfo import ZoneInfo
    _TZ = ZoneInfo('Asia/Tehran')
except Exception:
    _TZ = timezone(timedelta(hours=3, minutes=30))

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

try:
    from reporting.repository import now_tehran
except Exception:
    def now_tehran():
        return datetime.now(_TZ)

# نگاشت جهان اختیار معامله — سازگار با اجرای مستقیم و پکیجی
try:
    from .underlying_map import resolve_underlying
except ImportError:
    from underlying_map import resolve_underlying

MARKETWATCH_URLS = [
    # Primary: old.tsetmc.com (verified live: ~413KB raw MarketWatchPlus on 1405/07/24;
    # cdn.tsetmc.com now returns an 824-byte React SPA shell instead of raw data)
    'https://old.tsetmc.com/tsev2/data/MarketWatchPlus.aspx?h=0&r=0',
    'https://cdn.tsetmc.com/tsev2/data/MarketWatchPlus.aspx?h=0&r=0',
    'https://www.tsetmc.com/tsev2/data/MarketWatchPlus.aspx?h=0&r=0',
]

HEADERS = {
    'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                   'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36'),
    'Accept': '*/*',
    'Accept-Language': 'fa,en;q=0.8',
}

LISTS = {
    'stocks': 'لیست سهام بازار',
    'options': 'لیست اختیار معامله',
    'others': 'سایر ابزارها (صندوق، اسناد، حق تقدم و غیره)',
}

def _is_fa(ch):
    return 0x0600 <= ord(ch) <= 0x06FF

def _fa_fields(fields):
    return [x for x in fields if any(_is_fa(c) for c in x)]

def _looks_like_instrument(row):
    f = row.split(',')
    has_id = any(x.isdigit() and len(x) >= 10 for x in f)
    return has_id and bool(_fa_fields(f))

def _extract(fields):
    ins = next((x for x in fields if x.isdigit() and len(x) >= 10), None)
    fa = _fa_fields(fields)
    if ins is None or not fa:
        return None
    nospace = [x for x in fa if ' ' not in x]
    symbol = min(nospace or fa, key=len)
    title = max(fa, key=len)
    if title == symbol:
        title = ''
    isin = ''
    for x in fields:
        rest = x[2:]
        if (x.startswith('IR') and 11 <= len(x) <= 12
                and all(c.isascii() and c.isalnum() for c in rest)):
            isin = x
            break
    return {'ins_code': ins, 'isin': isin, 'symbol': symbol.strip(),
            'title': title.strip()}

def parse_marketwatch(text):
    # پارس دفاعی: بخش ابزارها به‌صورت خودکار شناسایی می‌شود (مقاوم به تغییر ترتیب)
    if not text or '@' not in text:
        raise ValueError('فرمت ناشناخته: پاسخ بدون جداکننده بخش (@)')
    sections = text.split('@')
    best_rows, best_score = None, 0
    for sec in sections:
        rows = [r for r in sec.split(';') if r.strip()]
        score = sum(1 for r in rows if _looks_like_instrument(r))
        if score > best_score:
            best_rows, best_score = rows, score
    if not best_rows or best_score == 0:
        raise ValueError('بخش ابزارها پیدا نشد — احتمالاً فرمت TSETMC تغییر کرده')
    instruments, skipped = [], 0
    for row in best_rows:
        rec = _extract(row.split(','))
        if rec is None:
            skipped += 1
            continue
        instruments.append(rec)
    seen, uniq = set(), []
    for rec in instruments:
        if rec['ins_code'] in seen:
            continue
        seen.add(rec['ins_code'])
        uniq.append(rec)
    deduped = len(instruments) - len(uniq)
    uniq.sort(key=lambda r: (r['symbol'], r['ins_code']))
    return {'instruments': uniq, 'skipped_rows': skipped, 'deduped': deduped,
            'rows_seen': best_score}

def classify(symbol, title):
    # تفکیک بر پایه قراردادهای نام‌گذاری بازار — بدون هیچ فرض عددی
    t = (title or '') + ' ' + (symbol or '')
    if (symbol or '')[:1] in ('ض', 'ط') or 'اختيار' in t or 'اختیار' in t:
        return 'options'
    if 'صندوق' in t:
        return 'funds'
    if 'اسناد' in t or 'صکوک' in t or 'صكوك' in t or 'گواهي' in t or 'گواهی' in t:
        return 'debt'
    if 'حق تقدم' in t or 'حقتقدم' in t:
        return 'rights'
    return 'equities'

def snapshot(text, source_label, repo_root=None):
    # دریافت → پارس → تفکیک → ذخیره مخزن + نسخه خام (قابل audit)
    root = repo_root or _ROOT
    parsed = parse_marketwatch(text)
    run_id = hashlib.sha256(text.encode('utf-8')).hexdigest()
    gen = now_tehran().isoformat()
    buckets = {'stocks': [], 'options': [], 'others': []}
    for rec in parsed['instruments']:
        c = classify(rec['symbol'], rec['title'])
        if c == 'options':
            # آپشن فقط در صورت تعلق به جهان ۲۶سهمی به سبد آپشن می‌رود
            rec['underlying'] = resolve_underlying(rec['symbol'])
            key = 'options' if rec['underlying'] else 'others'
        else:
            key = 'stocks' if c == 'equities' else 'others'
        buckets[key].append(rec)
    counts = {'stocks': len(buckets['stocks']), 'options': len(buckets['options']),
              'others': len(buckets['others']),
              'total_instruments': len(parsed['instruments']),
              'skipped_rows': parsed['skipped_rows'], 'deduped': parsed['deduped'],
              'options_by_underlying': {u: sum(1 for r in buckets['options'] if r['underlying'] == u)
                                        for u in sorted({r['underlying'] for r in buckets['options']})}}
    consistent = (counts['stocks'] + counts['options'] + counts['others']
                  == counts['total_instruments']
                  # هر آپشنِ سبد آپشن باید سهم پایه غیرتهی داشته باشد
                  and all(r.get('underlying') for r in buckets['options']))
    raw_dir = os.path.join(root, 'output', 'raw', 'tsetmc')
    os.makedirs(raw_dir, exist_ok=True)
    with open(os.path.join(raw_dir, 'marketwatch_latest.txt'), 'w', encoding='utf-8') as f:
        f.write(text)
    paths = {}
    for key in LISTS:
        env = {'report_type': key, 'title': LISTS[key], 'run_id': run_id,
               'generated_at': gen, 'source': 'TSETMC MarketWatchPlus',
               'source_detail': source_label, 'counts': counts,
               'validation_pass': consistent, 'records': buckets[key]}
        d = os.path.join(root, 'output', 'lists', key)
        os.makedirs(d, exist_ok=True)
        p = os.path.join(d, 'latest.json')
        with open(p, 'w', encoding='utf-8') as f:
            json.dump(env, f, ensure_ascii=False, indent=2)
        paths[key] = p
    preview = {k: [r['symbol'] for r in v[:5]] for k, v in buckets.items()}
    return {'ok': True, 'run_id': run_id, 'counts': counts, 'paths': paths,
            'consistent': consistent, 'preview': preview}

class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None  # ریدایرکت را خودمان دنبال میکنیم

_NO_REDIRECT_OPENER = None

def _http_get(url, timeout=30, max_hops=5):
    """GET با دنبالکردن دستی ریدایرکت (حداکثر max_hops) + gzip شفاف"""
    global _NO_REDIRECT_OPENER
    if _NO_REDIRECT_OPENER is None:
        _NO_REDIRECT_OPENER = urllib.request.build_opener(_NoRedirect)
    hops = []
    for _ in range(max_hops + 1):
        req = urllib.request.Request(url, headers=HEADERS)
        resp = _NO_REDIRECT_OPENER.open(req, timeout=timeout)
        loc = resp.headers.get('Location')
        if resp.status in (301, 302, 303, 307, 308) and loc:
            from urllib.parse import urljoin
            hops.append(f'{resp.status} {url} -> {loc}')
            url = urljoin(url, loc)
            resp.close()
            continue
        raw = resp.read()
        if isinstance(raw, bytes) and raw[:2] == b'\x1f\x8b':
            raw = _gzip.decompress(raw)
        resp.close()
        text = raw.decode('utf-8', errors='replace') if isinstance(raw, bytes) else str(raw)
        if hops:
            print('ردیابی ریدایرکت: ' + ' ; '.join(hops))
        return text, url
    raise ConnectionError('حلقه ریدایرکت بیپایان (بیش از ' + str(max_hops) + ' پرش): ' + ' ; '.join(hops))

def fetch(timeout=30, urls=None):
    errors = []
    for url in (urls or MARKETWATCH_URLS):
        try:
            text, final_url = _http_get(url, timeout=timeout)
            if _mw_is_valid(text):
                return text, final_url
            errors.append(final_url + ': پاسخ نامعتبر')
        except Exception as e:
            errors.append(url + ': ' + str(e))
    raise ConnectionError('دریافت از همه میزبانها شکست خورد — ' + ' | '.join(errors))


def main(argv=None, repo_root=None):
    ap = argparse.ArgumentParser(description='دریافت و تفکیک داده TSETMC')
    ap.add_argument('--file', help='پارس از فایل خام ذخیره‌شده (بدون اینترنت)')
    ap.add_argument('--timeout', type=int, default=30)
    a = ap.parse_args(argv)
    if a.file:
        try:
            with open(a.file, encoding='utf-8') as f:
                text = f.read()
        except OSError as e:
            print('❌ فایل خام خوانده نشد: ' + str(e))
            return 1
        label = 'file: ' + a.file
    else:
        try:
            text, label = fetch(timeout=a.timeout)
        except ConnectionError as e:
            print('❌ ' + str(e))
            print('💡 بعداً با اینترنت دوباره اجرا کن: python3 -m data.tsetmc')
            return 1
    r = snapshot(text, label, repo_root=repo_root)
    c = r['counts']
    print('✅ منبع: ' + label)
    print('📊 کل: {} | سهام: {} | اختیار معامله: {} | سایر: {} | ردشده: {}'.format(
        c['total_instruments'], c['stocks'], c['options'], c['others'], c['skipped_rows']))
    print('🥇 نمونه سهام: ' + '، '.join(r['preview']['stocks']))
    print('🎯 نمونه آپشن: ' + '، '.join(r['preview']['options']))
    for k in ('stocks', 'options', 'others'):
        print('📄 ' + r['paths'][k])
    print('🧾 run_id: ' + r['run_id'][:16] + '…')
    return 0 if (r['ok'] and r['consistent']) else 2

if __name__ == '__main__':
    sys.exit(main())
