# قرارداد داده بنیادی

این پوشه فقط برای داده خام و point-in-time بنیادی است. هیچ مقدار نمونه یا مقدار صفرِ ساختگی وارد آن نشود.

حداقل شِمای هر نماد:

```json
{
  "symbol": "نماد سهم پایه",
  "profile": "non_financial | bank | holding | insurance",
  "sector": "peer-set",
  "decision_time": "2026-08-26T09:00:00+03:30",
  "source": "CODAL|TSETMC|SUPERVISOR_NEWS",
  "release_timestamp": "2026-08-25T18:00:00+03:30",
  "period_end": "2026-06-30",
  "metrics": {
    "recurring_eps_yoy": {
      "value": 0.25,
      "unit": "ratio",
      "source": "CODAL",
      "release_timestamp": "2026-08-25T18:00:00+03:30",
      "evidence_id": "codal-message-id"
    }
  }
}
```

اعداد مثال بالا قالب را نشان می‌دهند و داده واقعی نیستند. منبع، زمان انتشار و شناسه شواهد باید برای هر metric واقعی ثبت شود.

