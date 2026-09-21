# Source Schema Audit

## Purpose

schema_audit.py is an evidence-only readiness check for the OptionSchool24 source DataFrame. It records whether fields required for explicit option-chain identity are present. It does not infer identity from the option symbol.

## Identity readiness

Required explicit fields:
- Underlying
- Expiry
- Strike

Contract type is audited separately.

## Status policy

PRESENT means a supported explicit source column was found.
MISSING means no supported explicit source column was found.
READY means Underlying + Expiry + Strike are present.
INSUFFICIENT_DATA means one or more required identity fields are absent.

## Hard rule

Symbol parsing is disabled. A symbol prefix is not accepted as evidence of CALL/PUT for chain intelligence.

Economic parity analysis remains unavailable until identity and required economic inputs are separately validated.

## Runtime evidence

This repository establishes the schema-audit behavior using synthetic regression fixtures. It does not claim that the current live OptionSchool24 workbook contains these explicit identity fields unless a real workbook is inspected and recorded as evidence.


## Archived real-workbook evidence — 2026-08-30

Workbook inspected: `optionschool24_all_1788105478761.xlsx`.
The workbook contains one worksheet (`sheet1`) with the source fields including:

- `نماد`
- `قیمت اعمال`
- `تاریخ سررسید`
- `وضعیت`
- `اهرم`
- `نوسان ضمنی`
- Greek fields and market/liquidity fields

The inspected workbook does not contain explicit source columns for:

- Underlying / نماد سهم پایه
- Contract Type / نوع قرارداد

Therefore, for this archived real workbook the schema-audit result is:

- Identity readiness: `INSUFFICIENT_DATA`
- Contract type readiness: `INSUFFICIENT_DATA`
- Expiry: `PRESENT`
- Strike: `PRESENT`
- Symbol inference: `DISABLED`

The workbook contains symbols such as `ضهرم6047` and `ضهرم7060`, but the prefix is not used as CALL/PUT evidence by the active chain engine.

This is archived-source evidence, not proof of the current live download on 2026-09-21.
