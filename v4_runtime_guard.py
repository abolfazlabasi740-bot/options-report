"""Runtime gates for the production V4 report pipeline."""
import pandas as pd

MIN_LEVERAGE = 3.5
V4_PROTOCOL = "PROTOCOL_OPTIONS_RANKING_V4_1"


def enforce_v4_invariants(df, leverage_key="اهرم", drop_invalid=True):
    work = df.copy()
    input_rows = len(work)
    if leverage_key not in work.columns:
        raise RuntimeError(f"ستون {leverage_key} در داده وجود ندارد.")
    leverage = pd.to_numeric(work[leverage_key], errors="coerce")
    mask = leverage >= MIN_LEVERAGE
    if drop_invalid:
        work = work.loc[mask].copy()
    audit = {
        "input_rows": input_rows,
        "output_rows": len(work),
        "dropped_rows": input_rows - len(work),
        "minimum_leverage": MIN_LEVERAGE,
    }
    return work, audit
