import json

def fa(x,d=2):
    if x is None:return 'داده موجود نیست'
    return f'{x:,.{d}f}'

def render(p):
    q=p['quote']; f=p['flow']; b=p['order_book']; t=p['technical']; qu=p['quality']
    lines=[f"📊 تحلیل مستقل سهم پایه — {p['symbol']}",f"زمان Snapshot (UTC): {p['captured_at_utc']}","━━━━━━━━━━━━━━━━","قیمت",f"آخرین: {fa(q['last'])} | پایانی: {fa(q['close'])} | حجم: {fa(q['volume'],0)} | ارزش: {fa(q['value'],0)}","","جریان حقیقی/حقوقی",f"خالص حجم حقیقی: {fa(f['real_net_volume'],0)} | نسبت خرید/فروش حقیقی: {fa(f['real_buy_sell_ratio'])}",f"قدرت خرید حقیقی: {fa(f['real_buyer_power'])} | قدرت فروش حقیقی: {fa(f['real_seller_power'])}","","تکنیکال",f"بازده ۵ روزه: {fa(t['return_5d_pct'])}% | بازده ۲۰ روزه: {fa(t['return_20d_pct'])}%",f"SMA5: {fa(t['sma5'])} | SMA20: {fa(t['sma20'])} | SMA60: {fa(t['sma60'])}",f"RSI14: {fa(t['rsi14'])} | نوسان ۲۰روزه: {fa(t['volatility20_pct'])}%",f"جایگاه در دامنه ۲۰روزه: {fa(t['position20_pct'])}% | Trend Points: {fa(t['trend_points'],0)}","","ساختار بازار",f"بهترین خرید: {fa(b['best_bid'])} | بهترین فروش: {fa(b['best_ask'])} | Spread: {fa(b['spread_pct'])}%","","کیفیت داده",f"Confidence: {fa(qu['confidence'],1)}% | موارد ناقص: {', '.join(qu['missing_groups']) if qu['missing_groups'] else 'ندارد'}",f"Research Score (آزمایشی): {fa(p['research_score'])}","","این امتیاز توصیه معاملاتی نیست و تا زمان اعتبارسنجی تاریخی وارد V4 نمی‌شود."]
    return '\n'.join(lines)
