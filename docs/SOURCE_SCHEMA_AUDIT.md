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
