# BestLimits Evidence Package Gate — V4.1

Status: IMPLEMENTED / NO LIVE PACKAGE CLAIMED

This gate validates completeness of a future live evidence package. It does not interpret BestLimits fields and does not unlock scoring.

Required package:
- explicit TSETMC instrument IDs;
- at least 3 option instruments;
- at least 1 underlying instrument;
- at least 2 timestamps per instrument;
- raw BestLimits levels, endpoint, UTC timestamps and SHA-256;
- independent same-time semantic evidence;
- no OptionSchool dependency.

A package can become READY_FOR_REVIEW while semantic mapping remains blocked. Review readiness is not production approval.

This repository change does not execute Termux and does not create live-market evidence.
