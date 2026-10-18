import json,re
from pathlib import Path
from collections import Counter

p15=Path("output/base_share/daily_history/20261007.json")
p18=Path("output/base_share/latest_whole_market_opportunity_report.json")
out=Path("output/base_share/comparison_14050715_vs_14050718.txt")

def load(p):
    x=json.loads(p.read_text(encoding="utf-8"))
    if isinstance(x,list): return x
    for k in ("rows","data","items","results","candidates","opportunities"):
        if isinstance(x.get(k),list): return x[k]
    raise ValueError(f"ردیف‌ها پیدا نشدند: {p}")

def kind(r):
    s=str(r.get("symbol") or "").strip()
    meta=" ".join(str(r.get(k) or "") for k in ("name","instrument_classification","market_title","source")).casefold()
    if s.startswith(("ض","ط")) or any(w in meta for w in ("option","اختیار معامله","اختیارخرید","اختیرفروش")): return "OPTION"
    if re.search(r"[۲2]$",s): return "BLOCK_2"
    if re.search(r"[۳3]$",s): return "CLOSING_3"
    if re.search(r"\d$",s): return "OTHER_SUFFIX"
    return "ORDINARY"

def prepare(rows):
    d={}; counts=Counter(); duplicates=Counter()
    for r in rows:
        k=kind(r); counts[k]+=1
        if k!="ORDINARY": continue
        s=str(r.get("symbol") or "").strip()
        if not s: continue
        duplicates[s]+=1
        try: score=float(r["final_score"])
        except (KeyError,TypeError,ValueError): continue
        if r.get("instrument_id") is None: continue
        d[s]={"score":score,"id":str(r["instrument_id"]),"row":r}
    return d,counts,duplicates

a,ca,da=prepare(load(p15))
b,cb,db=prepare(load(p18))
common=sorted(s for s in set(a)&set(b) if a[s]["id"]==b[s]["id"])
mismatch=sorted(s for s in set(a)&set(b) if a[s]["id"]!=b[s]["id"])
only15=sorted(set(a)-set(b)); only18=sorted(set(b)-set(a))

ra={s:i+1 for i,(s,v) in enumerate(sorted(((s,a[s]["score"]) for s in common),key=lambda z:z[1],reverse=True))}
rb={s:i+1 for i,(s,v) in enumerate(sorted(((s,b[s]["score"]) for s in common),key=lambda z:z[1],reverse=True))}
changes=[(b[s]["score"]-a[s]["score"],ra[s]-rb[s],s) for s in common]

L=[
"مقایسه سهام عادی: ۱۵ مهر در برابر ۱۸ مهر",
f"ردیف خام: ۱۵ مهر={sum(ca.values())} | ۱۸ مهر={sum(cb.values())}",
f"تفکیک ۱۵ مهر: {dict(ca)}",
f"تفکیک ۱۸ مهر: {dict(cb)}",
f"سهام عادی دارای امتیاز: ۱۵ مهر={len(a)} | ۱۸ مهر={len(b)}",
f"نمادهای مشترک با شناسه یکسان={len(common)}",
f"نمادهای هم‌نام با شناسه متفاوت={len(mismatch)}",
f"فقط ۱۵ مهر={len(only15)} | فقط ۱۸ مهر={len(only18)}",
f"تکرار نماد عادی: ۱۵ مهر={sum(v>1 for v in da.values())} | ۱۸ مهر={sum(v>1 for v in db.values())}",
"","بیشترین افزایش امتیاز:"
]
for d,r,s in sorted(changes,key=lambda z:z[0],reverse=True)[:20]:
    L.append(f"{s}: {a[s]['score']:.2f} -> {b[s]['score']:.2f} ({d:+.2f}); رتبه در مجموعه مشترک {ra[s]} -> {rb[s]} ({r:+d})")
L += ["","بیشترین کاهش امتیاز:"]
for d,r,s in sorted(changes,key=lambda z:z[0])[:20]:
    L.append(f"{s}: {a[s]['score']:.2f} -> {b[s]['score']:.2f} ({d:+.2f}); رتبه در مجموعه مشترک {ra[s]} -> {rb[s]} ({r:+d})")
L += ["","فقط ۱۸ مهر: "+", ".join(only18[:60]),
      "فقط ۱۵ مهر: "+", ".join(only15[:60]),
      "هم‌نام با شناسه متفاوت: "+", ".join(mismatch[:60]),
      "هشدار: موتور امتیازدهی V2.1 به V2.2 تغییر کرده؛ تغییر امتیاز را نمی‌توان صرفاً به بازار نسبت داد.",
      "رتبه‌های بالا فقط در مجموعه مشترک با شناسه ابزار یکسان محاسبه شده‌اند."]
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text("\n".join(L),encoding="utf-8")
print("\n".join(L[:20]))
print("\nگزارش کامل:",out)
