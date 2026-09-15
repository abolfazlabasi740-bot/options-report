import json, math, time, logging
from datetime import datetime, timezone
from statistics import mean, pstdev
import requests

LOG=logging.getLogger(__name__)

def num(x):
    try: return float(x) if x is not None and x!='' else None
    except: return None

def safe_div(a,b): return a/b if a is not None and b not in (None,0) else None

def pct(a,b):
    x=safe_div(a,b); return x*100 if x is not None else None

def clip(x,a=0,b=100): return max(a,min(b,x)) if x is not None else None

def rsi(values, period=14):
    if len(values)<period+1: return None
    # values oldest -> newest
    gains=[]; losses=[]
    for i in range(1,len(values)):
        d=values[i]-values[i-1]; gains.append(max(d,0)); losses.append(max(-d,0))
    g=mean(gains[-period:]); l=mean(losses[-period:])
    if l==0: return 100.0 if g>0 else 50.0
    return 100-(100/(1+g/l))

class TSETMC:
    def __init__(self,cfg):
        self.base=cfg['api_base'].rstrip('/'); self.timeout=cfg['timeout_seconds']; self.retries=cfg['retries']
        self.s=requests.Session(); self.s.headers.update({'User-Agent':'Mozilla/5.0 underlying-intelligence/1.0','Accept':'application/json'})
    def get(self,path):
        url=self.base+path; last=None
        for i in range(self.retries):
            try:
                r=self.s.get(url,timeout=self.timeout); r.raise_for_status(); return r.json()
            except Exception as e:
                last=e; time.sleep(0.7*(i+1))
        raise RuntimeError(f'API failure: {url}: {last}')
    def search(self,symbol): return self.get('/Instrument/GetInstrumentSearch/'+symbol)
    def quote(self,code): return self.get('/ClosingPrice/GetClosingPriceInfo/'+code)
    def client(self,code): return self.get(f'/ClientType/GetClientType/{code}/1/0')
    def limits(self,code): return self.get('/BestLimits/'+code)
    def history(self,code): return self.get(f'/ClosingPrice/GetClosingPriceDailyList/{code}/0')
    def messages(self,code):
        try: return self.get('/Msg/GetMsgByInsCode/'+code)
        except Exception: return None

class Analyzer:
    def __init__(self,cfg): self.api=TSETMC(cfg); self.cfg=cfg
    def analyze(self,symbol):
        captured=datetime.now(timezone.utc).isoformat()
        search=self.api.search(symbol)
        code=self._code(search)
        if not code: raise RuntimeError('insCode not found')
        q=self.api.quote(code); c=self.api.client(code); lim=self.api.limits(code); hist=self.api.history(code)
        msg=self.api.messages(code)
        h=self._history(hist)
        quote=self._quote(q); flow=self._flow(c); book=self._book(lim,quote.get('last')); tech=self._tech(h); quality=self._quality(quote,flow,book,tech)
        score=self._score(tech,flow,book,quality)
        events=self._events(quote,flow,book,tech)
        return {'captured_at_utc':captured,'symbol':symbol,'ins_code':str(code),'quote':quote,'flow':flow,'order_book':book,'technical':tech,'messages':self._messages(msg),'quality':quality,'research_score':score,'events':events}
    def _code(self,x):
        if isinstance(x,dict):
            for k in ('insCode','InsCode','instrumentId','InstrumentId'):
                if x.get(k): return x[k]
            for v in x.values():
                z=self._code(v)
                if z:return z
        if isinstance(x,list):
            for v in x:
                z=self._code(v)
                if z:return z
        return None
    def _quote(self,x):
        d=x if isinstance(x,dict) else (x[0] if isinstance(x,list) and x else {})
        def f(*keys):
            for k in keys:
                if k in d:return num(d[k])
            return None
        return {'last':f('pDrCotVal','PDrCotVal'),'close':f('pClosing','PClosing'),'prev_close':f('priceYesterday','PriceYesterday'),'volume':f('qTotTran5J','QTotTran5J'),'value':f('qTotCap','QTotCap'),'trades':f('zTotTran','ZTotTran'),'low':f('priceMin','PriceMin'),'high':f('priceMax','PriceMax')}
    def _flow(self,x):
        d=x if isinstance(x,dict) else (x[0] if isinstance(x,list) and x else {})
        def f(*keys):
            for k in keys:
                if k in d:return num(d[k])
            return None
        rbv=f('Buy_I_Volume','buy_I_Volume'); rs=f('Sell_I_Volume','sell_I_Volume'); lbv=f('Buy_N_Volume','buy_N_Volume'); ls=f('Sell_N_Volume','sell_N_Volume')
        rc=f('Buy_CountI','buy_CountI'); sc=f('Sell_CountI','sell_CountI')
        return {'real_buy_volume':rbv,'real_sell_volume':rs,'legal_buy_volume':lbv,'legal_sell_volume':ls,'real_net_volume':None if rbv is None or rs is None else rbv-rs,'legal_net_volume':None if lbv is None or ls is None else lbv-ls,'real_buy_count':rc,'real_sell_count':sc,'real_buyer_power':safe_div(rbv,rc),'real_seller_power':safe_div(rs,sc),'real_buy_sell_ratio':safe_div(rbv,rs)}
    def _book(self,x,last):
        rows=x if isinstance(x,list) else x.get('bestLimits',[]) if isinstance(x,dict) else []
        if not rows:return {'best_bid':None,'best_ask':None,'bid_qty':None,'ask_qty':None,'spread_pct':None}
        r=rows[0]
        def f(*ks):
            for k in ks:
                if k in r:return num(r[k])
        bid=f('pMeDem','PMeDem'); ask=f('pMeOf','PMeOf'); bq=f('qTitMeDem','QTitMeDem'); aq=f('qTitMeOf','QTitMeOf')
        return {'best_bid':bid,'best_ask':ask,'bid_qty':bq,'ask_qty':aq,'spread_pct':pct(ask-bid,last) if ask is not None and bid is not None and last else None}
    def _history(self,x):
        rows=x if isinstance(x,list) else x.get('closingPriceDailyList',[]) if isinstance(x,dict) else []
        out=[]
        for r in rows:
            close=num(r.get('pClosing',r.get('PClosing'))); date=r.get('dEven',r.get('DEven'))
            if close is not None: out.append({'date':date,'close':close,'volume':num(r.get('qTotTran5J',r.get('QTotTran5J'))),'value':num(r.get('qTotCap',r.get('QTotCap')))})
        out.sort(key=lambda z:str(z['date']))
        return out[-self.cfg.get('history_days',120):]
    def _tech(self,h):
        p=[r['close'] for r in h]; vols=[r['volume'] for r in h if r['volume'] is not None]
        sma=lambda n: mean(p[-n:]) if len(p)>=n else None
        def ret(n): return pct(p[-1]-p[-1-n],p[-1-n]) if len(p)>n and p[-1-n] else None
        vol20=(pstdev(p[-20:])/mean(p[-20:])*100) if len(p)>=20 and mean(p[-20:]) else None
        hi=max(p[-20:]) if p else None; lo=min(p[-20:]) if p else None
        pos=pct(p[-1]-lo,hi-lo) if p and hi!=lo else None
        r=rsi(p)
        trend=0
        if sma(5) and sma(20): trend += 1 if sma(5)>sma(20) else -1
        if sma(20) and sma(60): trend += 1 if sma(20)>sma(60) else -1
        return {'history_rows':len(p),'return_5d_pct':ret(5),'return_20d_pct':ret(20),'sma5':sma(5),'sma20':sma(20),'sma60':sma(60),'rsi14':r,'volatility20_pct':vol20,'high20':hi,'low20':lo,'position20_pct':pos,'trend_points':trend,'avg_volume20':mean(vols[-20:]) if len(vols)>=20 else None}
    def _quality(self,q,f,b,t):
        groups=[q,f,b,t]; present=sum(bool(g) for g in groups); missing=[]
        checks={'quote':q.get('last') is None or q.get('close') is None,'flow':f.get('real_net_volume') is None,'order_book':b.get('best_bid') is None or b.get('best_ask') is None,'technical':t.get('rsi14') is None}
        missing=[k for k,v in checks.items() if v]
        return {'confidence':round(max(0,100-len(missing)*12.5),1),'missing_groups':missing,'group_count':present}
    def _score(self,t,f,b,q):
        vals=[]; weights=self.cfg['research_score']['weights']
        def add(name,val):
            if val is not None: vals.append((weights[name],clip(val)))
        trend=((t.get('trend_points') or 0)+2)/4*100; add('trend',trend)
        flow=50
        if f.get('real_buy_sell_ratio') is not None: flow=clip(50+(f['real_buy_sell_ratio']-1)*25)
        add('flow',flow)
        mom=t.get('return_5d_pct'); add('momentum',clip(50+(mom or 0)*4))
        rv=t.get('rsi14'); add('rsi',clip(rv if rv is not None else None))
        sp=b.get('spread_pct'); add('liquidity',clip(100-(sp*5 if sp is not None else 30)))
        if not vals:return None
        return round(sum(w*v for w,v in vals)/sum(w for w,v in vals),2)
    def _messages(self,x):
        if not x:return {'count':0,'latest':None}
        rows=x if isinstance(x,list) else x.get('msgList',[]) if isinstance(x,dict) else []
        return {'count':len(rows),'latest':rows[:5]}
    def _events(self,q,f,b,t):
        e=[]
        if t.get('rsi14') is not None and t['rsi14']>=70:e.append({'type':'rsi_overbought','rsi':t['rsi14']})
        if t.get('rsi14') is not None and t['rsi14']<=30:e.append({'type':'rsi_oversold','rsi':t['rsi14']})
        if f.get('real_buy_sell_ratio') is not None and f['real_buy_sell_ratio']>=1.5:e.append({'type':'real_buy_pressure','ratio':f['real_buy_sell_ratio']})
        if b.get('spread_pct') is not None and b['spread_pct']>=5:e.append({'type':'wide_spread','spread_pct':b['spread_pct']})
        return e
