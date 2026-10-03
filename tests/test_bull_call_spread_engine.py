#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from bull_call_spread_engine import form_bull_call_spread, rank_bull_call_spreads


def row(i, strike, price, symbol="TEST", expiry="1405/12/01"):
    return {
        "identity": {
            "instrument_id": i,
            "contract_type": "call",
            "underlying_symbol": symbol,
        },
        "canonical": {
            "نماد": i,
            "تاریخ سررسید": expiry,
            "قیمت اعمال": strike,
            "آخرین قیمت": price,
            "حجم": 100,
            "ارزش معاملات": 1000,
            "موقعیت های باز": 50,
        },
    }


def main():
    a = row("CALL_A", 100, 12)
    b = row("CALL_B", 120, 4)
    s = form_bull_call_spread(a, b)
    assert s is not None
    assert s.net_debit == 8
    assert s.max_loss == 8
    assert s.max_profit == 12
    assert s.breakeven == 108

    invalid = form_bull_call_spread(
        row("X", 100, 12), row("Y", 120, 20)
    )
    assert invalid is None

    assert len(rank_bull_call_spreads([a, b], top_count=15)) == 1
    print("BULL_CALL_SPREAD_TEST=PASS")


if __name__ == "__main__":
    main()
