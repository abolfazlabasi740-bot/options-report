"""Source schema audit for OptimusAI V4.1.

Evidence-only: inspects actual DataFrame columns and never infers contract identity
from option symbols.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass
from typing import Iterable
import pandas as pd

ENGINE_VERSION = "SCHEMA-AUDIT-1.0"

ALIASES = {
    "underlying": ["نماد سهم پایه", "نماد پایه", "سهم پایه", "دارایی پایه", "نام دارایی پایه", "شناسه دارایی پایه", "Underlying", "UnderlyingSymbol"],
    "contract_type": ["نوع قرارداد", "نوع اختیار", "نوع آپشن", "نوع", "ContractType", "OptionType"],
    "expiry": ["تاریخ سررسید", "سررسید", "Expiry", "Expiration"],
    "strike": ["قیمت اعمال", "Strike", "StrikePrice"],
}

@dataclass(frozen=True)
class FieldAudit:
    field: str
    status: str
    matched_column: str | None
    aliases_checked: tuple[str, ...]

def _normalize(value: object) -> str:
    text = str(value).strip()
    return text.replace("\u200c", "").replace("\u200f", "").replace("\u200e", "").replace("ي", "ی").replace("ك", "ک").casefold()

def _match_column(columns: Iterable[object], aliases: Iterable[str]) -> str | None:
    normalized = {_normalize(c): str(c) for c in columns}
    for alias in aliases:
        found = normalized.get(_normalize(alias))
        if found is not None:
            return found
    return None

def audit_schema(data: pd.DataFrame) -> dict:
    if not isinstance(data, pd.DataFrame):
        raise TypeError("data must be a pandas DataFrame")
    fields = []
    for field, aliases in ALIASES.items():
        matched = _match_column(data.columns, aliases)
        fields.append(FieldAudit(field, "PRESENT" if matched else "MISSING", matched, tuple(aliases)))
    by_field = {item.field: item for item in fields}
    identity_ready = all(by_field[name].status == "PRESENT" for name in ("underlying", "expiry", "strike"))
    contract_type_explicit = by_field["contract_type"].status == "PRESENT"
    return {
        "status": "SUCCESS",
        "engine_version": ENGINE_VERSION,
        "row_count": int(len(data)),
        "columns": [str(c) for c in data.columns],
        "fields": [asdict(item) for item in fields],
        "identity_readiness": "READY" if identity_ready else "INSUFFICIENT_DATA",
        "contract_type_readiness": "EXPLICIT" if contract_type_explicit else "INSUFFICIENT_DATA",
        "symbol_inference": "DISABLED",
        "economic_parity_readiness": "NOT_READY_UNTIL_IDENTITY_AND_ECONOMIC_INPUTS_ARE_VALIDATED",
    }
