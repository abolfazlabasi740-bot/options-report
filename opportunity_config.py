#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Explicit, auditable configuration for Shadow opportunity discovery."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return float(raw)


def _int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


@dataclass(frozen=True)
class OpportunityConfig:
    relative_value_rank: float = _float("OPP_RELATIVE_VALUE_RANK", 0.85)
    breakeven_rank: float = _float("OPP_BREAKEVEN_RANK", 0.80)
    liquidity_rank: float = _float("OPP_LIQUIDITY_RANK", 0.75)
    liquidity_block_weight: float = _float("OPP_LIQUIDITY_BLOCK_WEIGHT", 20.0)
    execution_penalty_max: float = _float("OPP_EXECUTION_PENALTY_MAX", 0.10)
    confirmation_confidence: float = _float("OPP_CONFIRMATION_CONFIDENCE", 90.0)
    near_expiry_days: int = _int("OPP_NEAR_EXPIRY_DAYS", 10)
    historical_pattern_window: int = _int("HISTORICAL_PATTERN_WINDOW", 3)
    production_min_leverage_reference: float = _float("PRODUCTION_MIN_LEVERAGE_REFERENCE", 3.5)

    def validate(self) -> None:
        bounded = {
            "relative_value_rank": self.relative_value_rank,
            "breakeven_rank": self.breakeven_rank,
            "liquidity_rank": self.liquidity_rank,
        }
        for name, value in bounded.items():
            if not 0 <= value <= 1:
                raise ValueError(f"{name} must be between 0 and 1")
        if self.liquidity_block_weight <= 0:
            raise ValueError("liquidity_block_weight must be positive")
        if self.execution_penalty_max < 0:
            raise ValueError("execution_penalty_max must be non-negative")
        if self.confirmation_confidence < 0:
            raise ValueError("confirmation_confidence must be non-negative")
        if self.near_expiry_days < 0:
            raise ValueError("near_expiry_days must be non-negative")
        if self.historical_pattern_window < 1:
            raise ValueError("historical_pattern_window must be positive")
        if self.production_min_leverage_reference <= 0:
            raise ValueError("production_min_leverage_reference must be positive")


CONFIG = OpportunityConfig()
CONFIG.validate()
