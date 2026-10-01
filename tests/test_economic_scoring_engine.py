import unittest
from economic_scoring_engine import build_economic_ranking

class EconomicScoringTests(unittest.TestCase):
    def row(self,symbol,S,K,P,close,volume=100,value=1000,days=20,typ="CALL"):
        return {"canonical":{"نماد":symbol,"قیمت سهم پایه":S,"قیمت اعمال":K,"آخرین قیمت":P,
        "قیمت پایانی":close,"حجم معاملات":volume,"ارزش معاملات":value,"روزهای تقویمی":days,
        "بیشترین قیمت":(P*1.05 if P is not None else None),"کمترین قیمت":(P*.95 if P is not None else None)},
        "identity":{"instrument_id":symbol,"contract_type":typ}}

    def test_mode_and_source(self):
        r=build_economic_ranking([self.row("A",100,100,10,10)])
        self.assertEqual(r["mode"],"TSETMC_ECONOMIC_SCORING")
        self.assertEqual(r["source_of_truth"],"TSETMC")
        self.assertTrue(r["ranking_rows"])

    def test_lower_premium_burden_scores_higher(self):
        r=build_economic_ranking([
            self.row("CHEAP",100,100,10,10),
            self.row("EXPENSIVE",100,100,20,20)])
        x={a["instrument_id"]:a for a in r["ranking_rows"]}
        self.assertLess(x["CHEAP"]["features"]["premium_burden"],x["EXPENSIVE"]["features"]["premium_burden"])
        self.assertGreater(x["CHEAP"]["economic_score"],x["EXPENSIVE"]["economic_score"])

    def test_breakeven_distance_is_economic_feature(self):
        r=build_economic_ranking([
            self.row("A",100,100,5,5),
            self.row("B",100,90,20,20)])
        self.assertTrue(all("breakeven_distance" in x["features"] for x in r["ranking_rows"]))

    def test_missing_data_is_not_zero(self):
        r=build_economic_ranking([self.row("M",100,100,None,None)])
        x=r["ranking_rows"][0]
        self.assertIsNone(x["features"]["premium_burden"])

    def test_call_and_put_derivations(self):
        c=build_economic_ranking([self.row("C",100,90,15,15,typ="CALL")])["ranking_rows"][0]
        p=build_economic_ranking([self.row("P",100,110,15,15,typ="PUT")])["ranking_rows"][0]
        self.assertAlmostEqual(c["features"]["breakeven_distance"],.05)
        self.assertAlmostEqual(p["features"]["breakeven_distance"],.05)

if __name__=="__main__":
    unittest.main()
