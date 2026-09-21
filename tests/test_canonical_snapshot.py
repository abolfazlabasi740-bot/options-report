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
    def test_missing_identity_is_not_invented(self):
        options=pd.DataFrame([{"نماد":"ضهرم","insCode":"A"}])
        canonical,_=build_canonical_snapshot(options,[{"instrument_id":"A","symbol":"ضهرم"}])
        self.assertIsNone(canonical.iloc[0]["underlying_id"])
        self.assertIsNone(canonical.iloc[0]["contract_type"])
    def test_snapshot_id_is_deterministic(self):
        options=pd.DataFrame([{"نماد":"ضهرم","insCode":"A"}])
        t=[{"instrument_id":"A","symbol":"ضهرم"}]
        _,a=build_canonical_snapshot(options,t); _,b=build_canonical_snapshot(options,t)
        self.assertEqual(a["snapshot_id"],b["snapshot_id"])
if __name__=="__main__": unittest.main()
