let B=null;
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
load();