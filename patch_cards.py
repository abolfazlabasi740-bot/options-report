# -*- coding: utf-8 -*-
import shutil, sys, time, py_compile
from pathlib import Path

# ---- 1) lmp_report_module.py: افزودن send_lmp_cards ----
M = Path("scripts/lmp_report_module.py")
src = M.read_text(encoding="utf-8")
if "def send_lmp_cards" in src:
    print("MODULE_ALREADY")
else:
    bak = M.with_name("lmp_report_module.py.bak_" + time.strftime("%Y%m%d_%H%M%S"))
    shutil.copy2(M, bak); print("MODULE_BACKUP:", bak.name)
    func = '''

def send_lmp_cards(api_base, chat_id):
    """ارسال کارت‌های متنی فرصت‌های اختیار (خروجی اصلی دکمه)."""
    import requests
    try:
        from lmp_cards import build_cards
    except ImportError:
        import importlib.util as _ilu
        _p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lmp_cards.py")
        _spec = _ilu.spec_from_file_location("lmp_cards", _p)
        _mod = _ilu.module_from_spec(_spec)
        _spec.loader.exec_module(_mod)
        build_cards = _mod.build_cards
    parts, ok = build_cards()
    if isinstance(parts, str):
        parts = [parts]
    n = len(parts)
    for i, chunk in enumerate(parts, 1):
        text = (("(%d/%d)\\n" % (i, n)) + chunk) if n > 1 else chunk
        try:
            r = requests.post(api_base + "/sendMessage",
                              data={"chat_id": chat_id, "text": text}, timeout=60)
            r.raise_for_status()
        except Exception as exc:
            try:
                requests.post(api_base + "/sendMessage",
                              data={"chat_id": chat_id,
                                    "text": "LMP_CARD_FAIL(%d): %s" % (i, exc)},
                              timeout=30)
            except Exception:
                pass
    return ok
'''
    M.write_text(src.rstrip() + "\n" + func, encoding="utf-8")
    print("MODULE_PATCHED")
py_compile.compile(str(M), doraise=True)

# ---- 2) bale_listener.py: تعویض دو نقطه فراخوانی ----
B = Path("bale_listener.py")
lines = B.read_text(encoding="utf-8").split("\n")
if any("send_lmp_cards(API" in ln for ln in lines):
    print("LISTENER_ALREADY"); sys.exit(0)
bak = B.with_name("bale_listener.py.bak_" + time.strftime("%Y%m%d_%H%M%S"))
shutil.copy2(B, bak); print("LISTENER_BACKUP:", bak.name)

for i, ln in enumerate(lines):
    if "from lmp_report_module import" in ln and "send_lmp_files" in ln and "send_lmp_cards" not in ln:
        lines[i] = ln.rstrip() + ", send_lmp_cards"
        print("IMPORT_UPDATED_LINE:", i + 1)
        break
else:
    print("IMPORT_NOT_FOUND"); sys.exit(1)

n = 0
for i, ln in enumerate(lines):
    if "send_lmp_files(API, _lmp_chat)" in ln:
        lines[i] = ln.replace("send_lmp_files(API, _lmp_chat)", "send_lmp_cards(API, _lmp_chat)")
        n += 1; print("SWAP_LINE:", i + 1)
print("CALLS_SWAPPED:", n)
if n == 0:
    print("NO_CALL_SITES"); sys.exit(1)

B.write_text("\n".join(lines), encoding="utf-8")
py_compile.compile(str(B), doraise=True)
print("PATCH_OK")
