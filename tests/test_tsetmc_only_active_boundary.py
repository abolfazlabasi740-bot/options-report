#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regression guard for the V4.1 TSETMC-only active runtime boundary.

Historical OptionSchool material is intentionally allowed elsewhere in the
repository. This test protects only the files that form the active production
source/report/distribution path.
"""

from __future__ import annotations

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

ACTIVE_FILES = (
    "report_engine.py",
    "tsetmc_first_source.py",
    "tsetmc_adapter.py",
    "bale_runtime_verification.py",
)

FORBIDDEN_RUNTIME_TOKENS = (
    "optionschool",
    "optionschool24",
)


class TestTsetmcOnlyActiveBoundary(unittest.TestCase):
    def _source(self, name: str) -> str:
        return (ROOT / name).read_text(encoding="utf-8")

    def test_audit_integrity_contract_version_is_enforced(self):
        source = self._source("audit_integrity.py")
        self.assertIn('ENGINE_VERSION = "AUDIT-INTEGRITY-1.3"', source)
        self.assertIn('"audit_version"', source)
        self.assertIn('audit.get("audit_version") != ENGINE_VERSION', source)

    def test_active_files_exist(self):
        for name in ACTIVE_FILES:
            self.assertTrue((ROOT / name).is_file(), name)

    def test_active_runtime_has_no_optionschool_dependency_reference(self):
        for name in ACTIVE_FILES:
            source = self._source(name).lower()
            for token in FORBIDDEN_RUNTIME_TOKENS:
                self.assertNotIn(
                    token,
                    source,
                    f"{name} contains forbidden active-runtime token: {token}",
                )

    def test_report_engine_import_boundary_is_tsetmc(self):
        tree = ast.parse(self._source("report_engine.py"))
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)

        self.assertIn("tsetmc_first_source", imports)
        self.assertIn("audit_integrity", imports)
        self.assertNotIn("optionschool", " ".join(sorted(imports)).lower())
        self.assertNotIn("pandas", imports)

    def test_active_report_path_is_canonical_root_report(self):
        source = self._source("report_engine.py")
        self.assertIn('root / "output"', source)
        self.assertIn('root / "latest_report.txt"', source)
        self.assertIn('root / "latest_audit.json"', source)

    def test_bale_verifier_does_not_regenerate_analysis(self):
        source = self._source("bale_runtime_verification.py")
        self.assertIn('REPORT_PATH = ROOT / "output" / "latest_report.txt"', source)
        self.assertNotIn("report_engine", source)
        self.assertNotIn("build_tsetmc_snapshot", source)


if __name__ == "__main__":
    unittest.main()
