# BestLimits Evidence Package Gate — V4.1

Status: IMPLEMENTED / NO LIVE PACKAGE CLAIMED

This gate validates completeness of a future live evidence package. It does not interpret BestLimits fields and does not unlock scoring.

Required package:
- explicit TSETMC instrument IDs;
- at least 3 option instruments;
- at least 1 underlying instrument;
- at least 2 timestamps per instrument;
- complete raw BestLimits payload, extracted raw levels, endpoint, UTC timestamps and SHA-256;
- independent same-time semantic evidence;
- no OptionSchool dependency.

A package can become READY_FOR_REVIEW while semantic mapping remains blocked. Review readiness is not production approval.

The validator now recomputes SHA-256 from the preserved complete raw payload and rejects hash mismatch. Regression tests cover package completeness and payload-hash integrity. Tests are present in the repository; runtime execution is not claimed here.\n\nThis repository change does not execute Termux and does not create live-market evidence.
