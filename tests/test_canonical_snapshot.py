import unittest
import pandas as pd
from canonical_snapshot import build_canonical_snapshot

class CanonicalSnapshotTests(unittest.TestCase):
    def test_only_exact_mapping_is_promoted(self):
        options=pd.DataFrame([{"نماد":"ضهرم","insCode":"A","قیمت اعمال":100,"آخرین قیمت":10},
                              {"نماد":"ضملت","insCode":"B","قیمت اعمال":200,"آخرین قیمت":20}])
        canonical,meta=build_canonical_snapshot(options,[{"instrument_id":"A","symbol":"ضهرم"}])
        self.assertEqual(len(canonical),1)
        self.assertEqual(canonical.iloc[0]["instrument_id"],"A")
        self.assertEqual(meta["exact_promoted"],1)
        self.assertEqual(meta["no_match"],1)
    def test_exact_mapping_promotes_explicit_tsetmc_option_metadata(self):
        options = pd.DataFrame([{"نماد":"ضهرم7050","insCode":"C456","قیمت اعمال":20000}])
        tsetmc = [{
            "instrument_id":"C456",
            "symbol":"ضهرم7050",
            "contract_type":"CALL",
            "underlying_id":"UA789",
            "underlying_symbol":"اهرم",
            "strike":20000,
            "end_date":"20261021",
        }]
        canonical, meta = build_canonical_snapshot(options, tsetmc)
        self.assertEqual(meta["exact_promoted"], 1)
        self.assertEqual(len(canonical), 1)
        row = canonical.iloc[0]
        self.assertEqual(row["instrument_id"], "C456")
        self.assertEqual(row["underlying_id"], "UA789")
        self.assertEqual(row["contract_type"], "CALL")
        self.assertEqual(row["underlying_symbol"], "اهرم")
        self.assertEqual(row["expiry"], "20261021")
        self.assertEqual(row["underlying_source_status"], "EXPLICIT_ID_AVAILABLE")

    def test_missing_identity_is_not_invented(self):
        options=pd.DataFrame([{"نماد":"ضهرم","insCode":"A"}])
        canonical,_=build_canonical_snapshot(options,[{"instrument_id":"A","symbol":"ضهرم"}])
        self.assertIsNone(canonical.iloc[0]["underlying_id"])
        self.assertIsNone(canonical.iloc[0]["contract_type"])
        self.assertEqual(canonical.iloc[0]["underlying_quote_status"], "NOT_ATTACHED")
    def test_snapshot_id_is_deterministic(self):
        options=pd.DataFrame([{"نماد":"ضهرم","insCode":"A"}])
        t=[{"instrument_id":"A","symbol":"ضهرم"}]
        _,a=build_canonical_snapshot(options,t); _,b=build_canonical_snapshot(options,t)
        self.assertEqual(a["snapshot_id"],b["snapshot_id"])
if __name__=="__main__": unittest.main()
