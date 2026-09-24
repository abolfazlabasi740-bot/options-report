# BestLimits Evidence Package Gate — V4.1

Status: IMPLEMENTED / NO LIVE PACKAGE CLAIMED

This gate validates completeness of a future live evidence package. It does not interpret BestLimits fields and does not unlock scoring.

Required package:
- explicit TSETMC instrument IDs;
- at least 3 option instruments;
- at least 1 underlying instrument;
- at least 2 timestamps per instrument;
- complete raw BestLimits payload, extracted raw levels, endpoint, UTC timestamps and SHA-256;
- independent same-time semantic evidence for every captured observation, matched by exact instrument ID and a deterministic correlation window of Δt ≤ 2 seconds;
- no OptionSchool dependency.

A package can become READY_FOR_REVIEW while semantic mapping remains blocked. Review readiness is not production approval.

The validator now recomputes SHA-256 from the preserved complete raw payload and rejects hash mismatch. Regression tests cover package completeness, payload-hash integrity, the Δt ≤ 2-second boundary, semantic six-field coverage, and option/underlying role-overlap rejection. Tests are present in the repository; runtime execution is not claimed here.\n\nThe validator requires each independent semantic-evidence reference to match an actual captured instrument and to fall within the current Δt ≤ 2-second correlation window. The 2-second value is a governance validation parameter, not semantic proof, and remains subject to live latency measurement.

This repository change does not execute Termux and does not create live-market evidence.
