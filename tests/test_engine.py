import pandas as pd

from tradesim.strategy import SMACrossover
from tradesim.engine import run_backtest_single_asset, SimConfig


def _sample_df():
    # simple increasing price series (should produce at least some trades)
    dates = pd.date_range("2021-01-01", periods=120, freq="D")
    close = pd.Series(range(100, 220), index=dates).astype(float)
    df = pd.DataFrame(
        {
            "open": close,
            "high": close * 1.01,
            "low": close * 0.99,
            "close": close,
            "volume": 1000,
        },
        index=dates,
    )
    return df


def test_backtest_returns_expected_keys():
    df = _sample_df()
    strat = SMACrossover(fast=5, slow=20, risk_fraction=0.95)
    cfg = SimConfig(initial_cash=10000, slippage_bps=0.0, commission_per_trade=0.0, allow_fractional=True)

    out = run_backtest_single_asset(df, "TEST", strat, cfg)

    assert "equity_curve" in out
    assert "trades" in out
    assert "final_equity" in out
    assert isinstance(out["equity_curve"], list)
    assert isinstance(out["trades"], list)
    assert out["final_equity"] > 0
