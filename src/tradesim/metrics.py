from __future__ import annotations
import pandas as pd
import numpy as np

def performance_metrics(equity_curve_records: list[dict], periods_per_year: int = 252) -> dict:
    df = pd.DataFrame(equity_curve_records)
    if df.empty:
        return {"cagr": 0.0, "sharpe": 0.0, "max_drawdown": 0.0}

    df["dt"] = pd.to_datetime(df["dt"])
    df = df.sort_values("dt")
    eq = df["equity"].astype(float).values

    if len(eq) < 3:
        return {"cagr": 0.0, "sharpe": 0.0, "max_drawdown": 0.0}

    rets = np.diff(eq) / eq[:-1]
    vol = np.std(rets) * np.sqrt(periods_per_year)
    mean = np.mean(rets) * periods_per_year
    sharpe = (mean / vol) if vol > 0 else 0.0

    peak = np.maximum.accumulate(eq)
    dd = (eq - peak) / peak
    max_dd = float(dd.min())

    start = eq[0]
    end = eq[-1]
    years = (df["dt"].iloc[-1] - df["dt"].iloc[0]).days / 365.25
    cagr = float((end / start) ** (1 / years) - 1) if years > 0 and start > 0 else 0.0

    return {"cagr": cagr, "sharpe": float(sharpe), "max_drawdown": float(max_dd)}
