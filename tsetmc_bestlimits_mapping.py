#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Frozen semantic adapter for TSETMC BestLimits level-1 fields.

This adapter is intentionally limited to the raw TSETMC BestLimits schema.
It performs semantic translation only after the V4.1 evidence gate has been
reviewed. It does not fetch data, infer missing values, or synthesize values
from another source.
"""

from __future__ import annotations

from typing import Any


MAPPING_VERSION = "TSETMC-BESTLIMITS-MAPPING-1.0"

RAW_TO_SEMANTIC = {
    "pd": "bid_price",
    "po": "ask_price",
    "qd": "bid_quantity",
    "qo": "ask_quantity",
    "zd": "bid_order_count",
    "zo": "ask_order_count",
}


def map_bestlimits_level_1(raw_level: dict[str, Any]) -> dict[str, Any]:
    """Translate one raw BestLimits level into the frozen semantic contract.

    Missing raw fields remain None. No defaults, estimates, or cross-source
    substitutions are permitted.
    """
    if not isinstance(raw_level, dict):
        raise TypeError("raw_level must be a dict")

    return {
        "bid_price": raw_level.get("pMeDem"),
        "ask_price": raw_level.get("pMeOf"),
        "bid_quantity": raw_level.get("qTitMeDem"),
        "ask_quantity": raw_level.get("qTitMeOf"),
        "bid_order_count": raw_level.get("zOrdMeDem"),
        "ask_order_count": raw_level.get("zOrdMeOf"),
    }
