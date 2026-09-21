"""Regression tests for source schema audit."""
import unittest
import pandas as pd
from schema_audit import audit_schema, ENGINE_VERSION

class SchemaAuditTests(unittest.TestCase):
    def test_explicit_identity_is_detected_without_symbol_inference(self):
        data = pd.DataFrame({"نماد":["ضتست1"],"نماد سهم پایه":["فزر"],"نوع قرارداد":["CALL"],"تاریخ سررسید":["1405/07/30"],"قیمت اعمال":[1000]})
        result = audit_schema(data)
        self.assertEqual(result["status"], "SUCCESS")
        self.assertEqual(result["engine_version"], ENGINE_VERSION)
        self.assertEqual(result["identity_readiness"], "READY")
        self.assertEqual(result["contract_type_readiness"], "EXPLICIT")
        self.assertEqual(result["symbol_inference"], "DISABLED")

    def test_missing_identity_stays_insufficient_data(self):
        data = pd.DataFrame({"نماد":["ضتست1"],"قیمت اعمال":[1000]})
        result = audit_schema(data)
        self.assertEqual(result["identity_readiness"], "INSUFFICIENT_DATA")
        self.assertEqual(result["contract_type_readiness"], "INSUFFICIENT_DATA")

    def test_alias_normalization_is_explicit_only(self):
        data = pd.DataFrame({" نماد سهم پايه " :["فزر"],"نوع آپشن":["PUT"],"Expiry":["1405/07/30"],"StrikePrice":[1100]})
        result = audit_schema(data)
        self.assertEqual(result["identity_readiness"], "READY")
        self.assertEqual(result["contract_type_readiness"], "EXPLICIT")
