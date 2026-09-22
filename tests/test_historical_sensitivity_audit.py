import pandas as pd
from historical_sensitivity_audit import run_sensitivity

def _fixture():
    rows=[]
    for i in range(12):
        rows.append({"نماد":f"X{i:02d}","حجم معاملات":1000+i*100,"ارزش معاملات":10000+i*1000,
        "آخرین قیمت":100+i,"قیمت پایانی":100+i,"قیمت اعمال":100,"قیمت سهم پایه":100,
        "روزهای تقویمی":30,"روزهای معاملاتی":20,"اهرم":4+i*0.1,"موقعیت های باز":100+i,
        "سر به سر":100,"بلک شولز":10,"اختلاف تا بلک شولز":1+i,"ارزش زمانی":5+i,
        "نوسان ضمنی":20+i,"نوسان تاریخی":15+i,"شکاف قیمتی":1,"حجم بهترین تقاضا":100,
        "حجم بهترین عرضه":100,"دلتا":0.5,"تتا":-1,"گاما":0.1,"وگا":0.2,"رو":0.01,
        "بیشترین قیمت":101+i,"کمترین قیمت":99+i})
    return pd.DataFrame(rows)

def test_sensitivity_is_deterministic_and_evidence_only():
    a=run_sensitivity(_fixture(),top_n=5); b=run_sensitivity(_fixture(),top_n=5)
    assert a["status"]=="EVIDENCE_ONLY"
    assert a["production_mutation"] is False
    assert a["evidence_hash"]==b["evidence_hash"]
    assert len(a["blocks"])==6
