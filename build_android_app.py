# -*- coding: utf-8 -*-
"""OptimusAI Stock - ساخت اپ آفلاین (نسخه نهایی و تمام‌شدنی)"""
from pathlib import Path
import shutil

WWW = Path("android_app/www")
WWW.mkdir(parents=True, exist_ok=True)

HTML = """<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#0d1117">
<title>OptimusAI Stock</title>
<link rel="manifest" href="manifest.json">
<style>
*{box-sizing:border-box;margin:0;padding:0;font-family:Tahoma,sans-serif}
body{background:#0d1117;color:#e6edf3;padding:12px}
header{border-bottom:2px solid #238636;padding:10px 4px;margin-bottom:12px}
h1{font-size:18px;color:#3fb950}
.meta{font-size:12px;color:#8b949e;margin-top:4px}
.tabs{display:flex;gap:6px;margin-bottom:10px}
.tab{flex:1;padding:10px;text-align:center;background:#161b22;border:1px solid #30363d;border-radius:8px;font-size:13px;cursor:pointer}
.tab.active{background:#238636;color:#fff;border-color:#238636;font-weight:bold}
table{width:100%;border-collapse:collapse;font-size:12px}
th{background:#161b22;color:#58a6ff;padding:8px 4px;position:sticky;top:0;text-align:center}
td{padding:7px 4px;border-bottom:1px solid #21262d;text-align:center;white-space:nowrap}
tr:nth-child(even){background:#161b22}
.up{color:#3fb950;font-weight:bold}.down{color:#f85149;font-weight:bold}
.sym{color:#e3b341;font-weight:bold;font-size:13px}
.bar{height:4px;border-radius:2px;background:#238636;margin-top:2px}
.empty{text-align:center;padding:30px;color:#8b949e}
</style>
</head>
<body>
<header>
<h1>📈 OptimAI Stock — دیده‌بان بازار</h1>
<div class="meta" id="meta">در حال بارگذاری...</div>
</header>
<div class="tabs">
<div class="tab active" onclick="show('gainers')">بیشترین رشد</div>
<div class="tab" onclick="show('losers')">بیشترین افت</div>
<div class="tab" onclick="show('value')">بیشترین ارزش</div>
</div>
<div id="content"></div>
<script src="app.js"></script>
</body></html>"""

APPJS = """let B=null;
const fa=n=>n!=null?Number(n).toLocaleString('fa-IR'):'—';
const pct=v=>v==null?'—':(v>=0?'+':'')+Number(v).toFixed(2)+'%';
const cls=v=>v>=0?'up':'down';
async function load(){
 try{const r=await fetch('market_analytics_bundle.json');B=await r.json();}
 catch(e){document.getElementById('content').innerHTML='<div class="empty">❌ باندل یافت نشد</div>';return;}
 const h=B.header||B.meta||{};
 document.getElementById('meta').textContent='📅 '+(h.shamsi_date||h.date||'')+' | ⏰ '+(h.tehran_time||h.time||'')+' | '+(B.total_symbols||'—')+' نماد';
 show('gainers');
}
function show(k){
 document.querySelectorAll('.tab').forEach((t,i)=>t.classList.toggle('active',['gainers','losers','value'][i]===k));
 const el=document.getElementById('content');
 let rows=B[k]||B.top_gainers&&B[k]||[];
 if(!Array.isArray(rows)||!rows.length){el.innerHTML='<div class="empty">داده‌ای موجود نیست</div>';return;}
 const isVal=k==='value';
 let html='<table><tr><th>#</th><th>نماد</th><th>آخرین</th><th>'+(isVal?'ارزش (میلیارد تومان)':'رشد آخرین')+'</th><th>رشد پایانی</th></tr>';
 rows.slice(0,20).forEach((r,i)=>{
  const g=r.pl_pct??r.gain_pct, f=r.pc_pct??r.final_pct, v=r.value_b??r.tval_b;
  html+=`<tr><td>${i+1}</td><td class="sym">${r.symbol||r.sym||'—'}</td><td>${fa(r.pl??r.last)}</td>`+
   `<td class="${cls(isVal?1:g)}">${isVal?fa(v):pct(g)}</td><td class="${cls(f??0)}">${pct(f)}</td></tr>`;
 });
 el.innerHTML=html+'</table>';
}
load();"""

MANIFEST = """{"name":"OptimusAI Stock","short_name":"OptimusAI","start_url":"./index.html","display":"standalone","background_color":"#0d1117","theme_color":"#0d1117","lang":"fa"}"""

(WWW/"index.html").write_text(HTML, encoding="utf-8")
(WWW/"app.js").write_text(APPJS, encoding="utf-8")
(WWW/"manifest.json").write_text(MANIFEST, encoding="utf-8")

# همگام‌سازی باندل (در صورت نبودش از خروجی موتور کپی کن)
src = Path("output/reports/market_analytics_bundle.json")
dst = WWW/"market_analytics_bundle.json"
if src.exists() and not dst.exists():
    shutil.copy2(src, dst)

print("✅ اپ آفلاین ساخته شد:", WWW.resolve())
print("▶ اجرا: python -m http.server 8080 --directory android_app/www")
