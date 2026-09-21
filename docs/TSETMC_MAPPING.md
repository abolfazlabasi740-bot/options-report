# TSETMC ↔ OptionSchool24 Mapping

## Purpose

This layer connects the two sources without manufacturing identity.

Mapping states:

- EXACT_INSTRUMENT_ID: an explicit instrument identifier on the OptionSchool24 side matches exactly one TSETMC record.
- SYMBOL_ONLY_CANDIDATE: symbol text matches exactly one TSETMC record, but the OptionSchool24 row has no verified instrument identifier.
- AMBIGUOUS: more than one TSETMC record can satisfy the available key.
- NO_MATCH: no evidence-backed match exists.

Only EXACT_INSTRUMENT_ID is eligible for promotion into the canonical merged snapshot.

A symbol-only match is retained as a candidate for later evidence collection. It is never silently promoted to exact identity.

## Identity protection

This layer does not infer:

- underlying
- CALL/PUT
- strike
- expiry

from an option symbol.

The mapping result is therefore independent from the Six-Block scoring model and does not change current ranking or Bale output.
