from reporting.report_engine import BaseReport, register

@register
class LMPReport(BaseReport):
    name     = "LMP اسکنر آپشن"
    slug     = "lmp"
    columns  = ["ردیف","نماد","نوع","قیمت پایه","قیمت اعمال","سقف قیمت",
                "پرمیوم","سود خام","سربه‌سر","امتیاز","وضعیت"]
    required = ["symbol","strike","premium","break_even","score","status"]

    def envelope_kwargs(self):
        return {"scenario": "LMP", "price_basis": "پایه", "market_open": True}

    def build_rows(self, options, lookup, market_open=True, fixed_growth=None):
        """
        options: لیست آپشن‌ها از fetch_options()
        lookup:  دیکشنری از build_stock_lookup()
        خروجی: (results, unmatched, no_ceiling, extra)
        """
        from scripts.lmp_scanner import find_underlying, calculate_option

        results, unmatched, no_ceiling = [], [], []

        for i, op in enumerate(options, 1):
            und = find_underlying(op.get("symbol",""), lookup, {}, op.get("name",""))
            if not und:
                unmatched.append({"symbol": op.get("symbol",""), "reason": "نگاشت سهم پایه ناموفق"})
                continue

            calc = calculate_option(op, und, market_open, fixed_growth)
            if calc is None:
                unmatched.append({"symbol": op.get("symbol",""), "reason": "محاسبه ناموفق"})
                continue

            # اگر سهم سقف قیمت ندارد → no_ceiling (نه حذف!)
            if calc.get("ceiling") is None:
                no_ceiling.append({"symbol": op.get("symbol",""), "base": und.get("symbol","")})
                # همچنان محاسبه می‌شود ولی با flag
                calc["status"] = "بدون سقف"
            else:
                calc["status"] = "مجاز" if calc.get("score",0) > 0 else "رد"

            row = {
                "ردیف": i, "نماد": op.get("symbol",""), "نوع": "کال",
                "قیمت پایه": calc.get("base_price",""), "قیمت اعمال": calc.get("strike",""),
                "سقف قیمت": calc.get("ceiling","—"), "پرمیوم": calc.get("premium",""),
                "سود خام": calc.get("raw_profit",""), "سربه‌سر": calc.get("break_even",""),
                "امتیاز": calc.get("score",0), "وضعیت": calc.get("status",""),
                # کلیدهای انگلیسی برای validation و ranking
                "symbol": op.get("symbol",""), "strike": calc.get("strike"),
                "premium": calc.get("premium"), "break_even": calc.get("break_even"),
                "score": calc.get("score",0), "status": calc.get("status",""),
            }
            results.append(row)

        extra = {"fixed_growth": fixed_growth}
        return results, unmatched, no_ceiling, extra
