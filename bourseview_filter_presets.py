#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Evidence-only, machine-readable BourseView public filter presets.

These presets reproduce publicly described rules over a canonical normalized
record. They do not fetch data, derive missing fields, alter scoring, or issue
BUY/SELL instructions. A caller must provide validated point-in-time fields.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from filter_engine_shadow import evaluate_filter

SOURCE_BASE = "https://t.me/s/bvhelp"
ENGINE_VERSION = "BOURSEVIEW-PUBLIC-FILTER-PRESETS-1.0"

# Numeric percentages are expressed as percentage points (40 means 40%, not 0.40).
# Monetary values are in IRR/rials. 1 billion tomans = 10 billion IRR.
FILTER_PRESETS: dict[str, dict[str, Any]] = {
    "BV-F01": {
        "name": "Unusual traded value",
        "source_url": "https://t.me/s/bvhelp?before=152",
        "provenance": "PUBLICLY_DOCUMENTED_EXAMPLE",
        "description": "Today's traded value exceeds five times the 30-session average; the average exceeds 1 billion tomans.",
        "required_fields": [
            "today_value_to_avg_traded_value_30_sessions_ratio",
            "avg_traded_value_30_sessions_irr",
        ],
        "units": {"today_value_to_avg_traded_value_30_sessions_ratio": "ratio", "avg_traded_value_30_sessions_irr": "IRR"},
        "rules": [
            {"field": "today_value_to_avg_traded_value_30_sessions_ratio", "operator": "GT", "value": 5.0},
            {"field": "avg_traded_value_30_sessions_irr", "operator": "GT", "value": 10_000_000_000},
        ],
        "limitations": ["Intraday values must not be compared with completed-session averages without a separately validated time-of-day normalization."],
    },
    "BV-F02": {
        "name": "Investment companies below NAV",
        "source_url": "https://t.me/s/bvhelp?before=152",
        "provenance": "PUBLICLY_DOCUMENTED_EXAMPLE",
        "description": "Investment companies that traded today and have P/NAV below 1; sort matched results by P/NAV ascending.",
        "required_fields": ["is_investment_company", "traded_today", "p_nav"],
        "units": {"p_nav": "ratio"},
        "rules": [
            {"field": "is_investment_company", "operator": "EQ", "value": True},
            {"field": "traded_today", "operator": "EQ", "value": True},
            {"field": "p_nav", "operator": "LT", "value": 1.0},
        ],
        "sort_by": "p_nav",
        "sort_order": "ASC",
        "limitations": ["NAV must be timestamped and sufficiently fresh; this preset does not calculate NAV."],
    },
    "BV-F03": {
        "name": "Strong monthly revenue performance",
        "source_url": "https://t.me/s/bvhelp",
        "provenance": "PUBLICLY_DOCUMENTED_EXAMPLE",
        "description": "Monthly revenue growth exceeds the 3-month arithmetic-average growth and 1-year growth; average 30-day value exceeds 30 billion IRR; 3-month average growth is positive.",
        "required_fields": [
            "revenue_growth_1m_minus_arithmetic_avg_growth_3m_pct",
            "revenue_growth_1m_minus_growth_1y_pct",
            "avg_value_30d_irr",
            "revenue_arithmetic_average_growth_rate_3m_pct",
        ],
        "units": {"*_pct": "percentage points", "avg_value_30d_irr": "IRR"},
        "rules": [
            {"field": "revenue_growth_1m_minus_arithmetic_avg_growth_3m_pct", "operator": "GT", "value": 0},
            {"field": "revenue_growth_1m_minus_growth_1y_pct", "operator": "GT", "value": 0},
            {"field": "avg_value_30d_irr", "operator": "GT", "value": 30_000_000_000},
            {"field": "revenue_arithmetic_average_growth_rate_3m_pct", "operator": "GT", "value": 0},
        ],
        "limitations": ["Monthly revenue fields must be point-in-time and use the same growth definitions as the source formula."],
    },
    "BV-F04": {
        "name": "Strong quarterly revenue growth",
        "source_url": "https://t.me/s/bvhelp",
        "provenance": "PUBLICLY_DOCUMENTED_EXAMPLE",
        "description": "Quarterly revenue growth QoQ exceeds 10%, YoY exceeds 100%, and average 30-day value exceeds 30 billion IRR.",
        "required_fields": ["revenue_growth_rate_qoq_pct", "revenue_growth_rate_yoy_pct", "avg_value_30d_irr"],
        "units": {"*_pct": "percentage points", "avg_value_30d_irr": "IRR"},
        "rules": [
            {"field": "revenue_growth_rate_qoq_pct", "operator": "GT", "value": 10},
            {"field": "revenue_growth_rate_yoy_pct", "operator": "GT", "value": 100},
            {"field": "avg_value_30d_irr", "operator": "GT", "value": 30_000_000_000},
        ],
        "limitations": ["Quarter boundaries, restatements and report publication time must be handled upstream."],
    },
    "BV-F05": {
        "name": "Improving operating profit margin",
        "source_url": "https://t.me/s/bvhelp",
        "provenance": "PUBLICLY_DOCUMENTED_EXAMPLE",
        "description": "Operating profit margin growth QoQ and YoY is positive, TTM operating profit margin exceeds 30%, and average 30-day value exceeds 30 billion IRR.",
        "required_fields": [
            "operating_profit_margin_mrq_growth_rate_qoq_pct",
            "operating_profit_margin_mrq_growth_rate_yoy_pct",
            "avg_value_30d_irr",
            "operating_profit_margin_ttm_pct",
        ],
        "units": {"*_pct": "percentage points", "avg_value_30d_irr": "IRR"},
        "rules": [
            {"field": "operating_profit_margin_mrq_growth_rate_qoq_pct", "operator": "GT", "value": 0},
            {"field": "operating_profit_margin_mrq_growth_rate_yoy_pct", "operator": "GT", "value": 0},
            {"field": "avg_value_30d_irr", "operator": "GT", "value": 30_000_000_000},
            {"field": "operating_profit_margin_ttm_pct", "operator": "GT", "value": 30},
        ],
        "limitations": ["A separate public variant uses net profit margin TTM > 20%; it is not silently combined with this preset."],
    },
    "BV-F06": {
        "name": "Monthly sales growth with low monthly P/S",
        "source_url": "https://t.me/bvhelp/239",
        "provenance": "PUBLICLY_DOCUMENTED_EXAMPLE",
        "description": "Monthly revenue YoY growth exceeds 40%, monthly growth beats 3-month and 1-year growth, monthly P/S is below 2.5, and average 30-day value exceeds 10 billion IRR.",
        "required_fields": [
            "revenue_year_to_year_growth_rate_1m_pct",
            "revenue_growth_1m_minus_growth_3m_pct",
            "revenue_growth_1m_minus_growth_1y_pct",
            "p_to_s_monthly",
            "avg_value_30d_irr",
        ],
        "units": {"*_pct": "percentage points", "p_to_s_monthly": "ratio", "avg_value_30d_irr": "IRR"},
        "rules": [
            {"field": "revenue_year_to_year_growth_rate_1m_pct", "operator": "GT", "value": 40},
            {"field": "revenue_growth_1m_minus_growth_3m_pct", "operator": "GT", "value": 0},
            {"field": "revenue_growth_1m_minus_growth_1y_pct", "operator": "GT", "value": 0},
            {"field": "p_to_s_monthly", "operator": "LT", "value": 2.5},
            {"field": "avg_value_30d_irr", "operator": "GT", "value": 10_000_000_000},
        ],
        "limitations": ["The source has published multiple variants of this screen; this preset tracks the linked P/S version."],
    },
    "BV-F07": {
        "name": "Oversold RSI with liquidity floor",
        "source_url": "https://t.me/s/bvhelp/274",
        "provenance": "PUBLICLY_DOCUMENTED_EXAMPLE",
        "description": "RSI is below 30 and average 30-day traded value exceeds 30 billion IRR.",
        "required_fields": ["rsi_14", "avg_value_30d_irr"],
        "units": {"rsi_14": "index points", "avg_value_30d_irr": "IRR"},
        "rules": [
            {"field": "rsi_14", "operator": "LT", "value": 30},
            {"field": "avg_value_30d_irr", "operator": "GT", "value": 30_000_000_000},
        ],
        "limitations": ["Oversold is not a buy signal; the existing trend engine's RSI-14 can supply the indicator only when history is sufficient and fresh."],
    },
    "BV-F08": {
        "name": "Large drawdown from 200-day high",
        "source_url": "https://t.me/s/bvhelp?after=212",
        "provenance": "PUBLICLY_DOCUMENTED_EXAMPLE",
        "description": "High Percent 200D is below 0.5 and average 30-day traded value exceeds 10 billion IRR.",
        "required_fields": ["high_percent_200d", "avg_value_30d_irr"],
        "units": {"high_percent_200d": "fraction of 200-day high", "avg_value_30d_irr": "IRR"},
        "rules": [
            {"field": "high_percent_200d", "operator": "LT", "value": 0.5},
            {"field": "avg_value_30d_irr", "operator": "GT", "value": 10_000_000_000},
        ],
        "limitations": ["The existing trend engine's 20-day high is not equivalent; a 200-day history feature is required."],
    },
},
"BV-F09": {
        "name": "Low trailing P/E with broad monthly sales growth",
        "source_url": "https://t.me/s/bvhelp?after=194",
        "provenance": "PUBLICLY_DESCRIBED_SCREEN_RULE_DETAILS_PARTIAL",
        "description": "Public description says trailing P/E is below 8 and average sales growth exceeds 10% across monthly, 3-month, 5-month and same-month-year-ago views; the post does not publish the exact complete expression.",
        "required_fields": [
            "p_to_e_ttm",
            "revenue_growth_1m_pct",
            "revenue_growth_3m_pct",
            "revenue_growth_5m_pct",
            "revenue_yoy_growth_1m_pct",
        ],
        "units": {"p_to_e_ttm": "ratio", "*_pct": "percentage points"},
        "rules": [
            {"field": "p_to_e_ttm", "operator": "LT", "value": 8},
            {"field": "revenue_growth_1m_pct", "operator": "GT", "value": 10},
            {"field": "revenue_growth_3m_pct", "operator": "GT", "value": 10},
            {"field": "revenue_growth_5m_pct", "operator": "GT", "value": 10},
            {"field": "revenue_yoy_growth_1m_pct", "operator": "GT", "value": 10},
        ],
        "limitations": ["The public post describes the screen but does not publish its full expression; this is an explicit approximation of the prose, not a claimed exact reproduction."],
    },
    "BV-F10": {
        "name": "High leverage risk with low trailing P/E",
        "source_url": "https://t.me/s/bvhelp?before=223",
        "provenance": "PUBLICLY_DOCUMENTED_EXAMPLE",
        "description": "Trailing P/E below 8 and interest coverage ratio below 3.",
        "required_fields": ["p_to_e_ttm", "interest_coverage_ratio"],
        "units": {"p_to_e_ttm": "ratio", "interest_coverage_ratio": "ratio"},
        "rules": [
            {"field": "p_to_e_ttm", "operator": "LT", "value": 8},
            {"field": "interest_coverage_ratio", "operator": "LT", "value": 3},
        ],
        "limitations": ["This is a financial-risk screen, not a bullish signal; interest coverage must be computed from comparable operating-profit and finance-cost periods."],
    },


def list_bourseview_presets() -> list[dict[str, Any]]:
    """Return preset metadata without exposing mutable internal rule objects."""
    return [
        {
            "preset_id": preset_id,
            **{k: deepcopy(v) for k, v in preset.items() if k != "rules"},
            "rule_count": len(preset["rules"]),
            "engine_version": ENGINE_VERSION,
            "production_gate": "OFF",
        }
        for preset_id, preset in FILTER_PRESETS.items()
    ]


def evaluate_bourseview_preset(preset_id: str, record: dict[str, Any]) -> dict[str, Any]:
    """Evaluate one public rule against an already-normalized record.

    Missing fields remain INSUFFICIENT_DATA. This function does not fetch data,
    derive input fields, verify freshness, or promote results to production.
    """
    preset = FILTER_PRESETS.get(str(preset_id))
    if preset is None:
        return {
            "status": "INVALID_PRESET",
            "preset_id": str(preset_id),
            "matched": False,
            "engine_version": ENGINE_VERSION,
            "production_gate": "OFF",
        }
    result = evaluate_filter(record, preset["rules"], mode="ALL")
    return {
        "preset_id": str(preset_id),
        "name": preset["name"],
        "source_url": preset["source_url"],
        "provenance": preset["provenance"],
        "engine_version": ENGINE_VERSION,
        "production_gate": "OFF",
        "data_freshness_checked": False,
        **result,
    }
