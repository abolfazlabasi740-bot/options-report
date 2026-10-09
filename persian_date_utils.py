#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deterministic Gregorian-to-Jalali conversion for report date display."""
from __future__ import annotations
from datetime import date, datetime

def gregorian_to_jalali(value):
    """Return YYYY/MM/DD Jalali date for date/datetime or YYYYMMDD/YYYY-MM-DD."""
    if isinstance(value, datetime):
        gy, gm, gd = value.year, value.month, value.day
    elif isinstance(value, date):
        gy, gm, gd = value.year, value.month, value.day
    else:
        raw = str(value or "").strip()
        if len(raw) == 8 and raw.isdigit():
            gy, gm, gd = int(raw[:4]), int(raw[4:6]), int(raw[6:8])
        elif len(raw) >= 10 and raw[4] == "-" and raw[7] == "-":
            gy, gm, gd = int(raw[:4]), int(raw[5:7]), int(raw[8:10])
        else:
            return None
    if not (1 <= gm <= 12 and 1 <= gd <= 31):
        return None
    g_month_days = (0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334)
    gy2 = gy + 1 if gm > 2 else gy
    days = 355666 + 365 * gy + (gy2 + 3) // 4 - (gy2 + 99) // 100 + (gy2 + 399) // 400 + gd + g_month_days[gm - 1]
    jy = -1595 + 33 * (days // 12053)
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        jm, jd = 1 + days // 31, 1 + days % 31
    else:
        jm, jd = 7 + (days - 186) // 30, 1 + (days - 186) % 30
    return f"{jy:04d}/{jm:02d}/{jd:02d}"
