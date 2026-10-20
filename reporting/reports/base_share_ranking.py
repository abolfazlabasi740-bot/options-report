from reporting.report_engine import BaseReport, register

@register
class BaseShareRankingReport(BaseReport):
    name     = "رتبه‌بندی سهم پایه"
    slug     = "base_share_ranking"
    columns  = ["ردیف","نماد","صنعت","قیمت پایه","P/E","ROE","نقدشوندگی",
                "حجم متوسط","تغییر","امتیاز","وضعیت"]
    required = ["symbol","score","status"]

    def envelope_kwargs(self):
        return {"scenario": "Ranking", "price_basis": "پایه", "market_open": True}

    def build_rows(self, shares):
        """shares: لیست سهم‌های پایه با داده بنیادی"""
        results = []
        for i, s in enumerate(shares, 1):
            row = {
                "ردیف": i, "نماد": s.get("symbol",""), "صنعت": s.get("industry",""),
                "قیمت پایه": s.get("price",""), "P/E": s.get("pe",""),
                "ROE": s.get("roe",""), "نقدشوندگی": s.get("liquidity",""),
                "حجم متوسط": s.get("avg_volume",""), "تغییر": s.get("change",""),
                "امتیاز": s.get("score",0), "وضعیت": s.get("status",""),
                "symbol": s.get("symbol",""), "score": s.get("score",0),
                "status": s.get("status",""),
            }
            results.append(row)
        return results, [], [], {}
