from __future__ import annotations

import sys
from pathlib import Path
import streamlit as st
import pandas as pd
import plotly.express as px

# Optional (only used in API mode)
import requests

# --- make sure we can import from src/ on Streamlit Cloud ---
ROOT = Path(__file__).resolve().parents[1]     # project root
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from tradesim.data import load_ohlcv_yahoo
from tradesim.strategy import SMACrossover
from tradesim.engine import run_backtest_single_asset, SimConfig
from tradesim.metrics import performance_metrics

st.set_page_config(page_title="Trading Sim Dashboard", layout="wide")

st.title("Trading Simulation (Backtest → Metrics → Trades)")

# ----- Sidebar inputs -----
default_api = st.secrets.get("API_BASE_URL", "http://localhost:8000")

mode = st.sidebar.radio(
    "Run mode",
    ["Local (recommended on Streamlit Cloud)", "API (FastAPI server)"],
    index=0,
)

api_base = st.sidebar.text_input(
    "API base URL",
    value=default_api,
    disabled=(mode.startswith("Local")),
)

symbol = st.sidebar.text_input("Symbol", value="AAPL")
start = st.sidebar.text_input("Start (YYYY-MM-DD)", value="2020-01-01")
end = st.sidebar.text_input("End (YYYY-MM-DD)", value="2024-01-01")

fast = st.sidebar.slider("Fast SMA", min_value=2, max_value=300, value=20)
slow = st.sidebar.slider("Slow SMA", min_value=3, max_value=600, value=50)

initial_cash = st.sidebar.number_input("Initial cash", min_value=1.0, value=10000.0, step=500.0)
slippage_bps = st.sidebar.number_input("Slippage (bps)", min_value=0.0, value=2.0, step=0.5)
commission_per_trade = st.sidebar.number_input("Commission/trade", min_value=0.0, value=1.0, step=0.5)

run_btn = st.sidebar.button("Run backtest")

# ----- helpers -----
def _equity_df(out: dict) -> pd.DataFrame:
    eq = out.get("equity_curve")
    if eq is None:
        return pd.DataFrame()

    # common shapes: list[dict] with dt/equity OR list[float]
    if isinstance(eq, list) and len(eq) > 0 and isinstance(eq[0], dict):
        df = pd.DataFrame(eq)
    elif isinstance(eq, dict):
        df = pd.DataFrame(eq)
    else:
        df = pd.DataFrame({"equity": list(eq)})

    # normalize dt column if present
    if "dt" in df.columns:
        df["dt"] = pd.to_datetime(df["dt"], errors="coerce")
    return df


def _run_local() -> dict:
    df = load_ohlcv_yahoo(symbol, start, end, interval="1d")

    if df is None or len(df) == 0:
        raise ValueError(f"No data returned for {symbol}. Try another symbol (e.g., MSFT, SPY).")

    strat = SMACrossover(fast=fast, slow=slow, risk_fraction=0.95)
    cfg = SimConfig(
        initial_cash=float(initial_cash),
        slippage_bps=float(slippage_bps),
        commission_per_trade=float(commission_per_trade),
        allow_fractional=True,
    )

    out = run_backtest_single_asset(df, symbol, strat, cfg)

    # ensure metrics exist
    if "metrics" not in out and "equity_curve" in out:
        out["metrics"] = performance_metrics(out["equity_curve"])

    return out


def _run_api() -> dict:
    payload = {
        "symbol": symbol,
        "start": start,
        "end": end,
        "fast": int(fast),
        "slow": int(slow),
        "initial_cash": float(initial_cash),
        "slippage_bps": float(slippage_bps),
        "commission_per_trade": float(commission_per_trade),
    }

    r = requests.post(f"{api_base.rstrip('/')}/backtest", json=payload, timeout=60)
    # show useful error text if it isn't JSON
    if r.status_code >= 400:
        try:
            raise RuntimeError(r.json())
        except Exception:
            raise RuntimeError(r.text)

    return r.json()


# ----- Run + Render -----
if run_btn:
    if fast >= slow:
        st.error("fast must be < slow")
    else:
        try:
            with st.spinner("Running backtest..."):
                if mode.startswith("API"):
                    try:
                        out = _run_api()
                    except Exception as e:
                        st.warning(f"API not reachable ({e}). Falling back to Local mode.")
                        out = _run_local()
                else:
                    out = _run_local()

            st.session_state["last_out"] = out

        except Exception as e:
            st.error(f"{e}")

out = st.session_state.get("last_out")

if out:
    metrics = out.get("metrics", {}) or {}
    eq_df = _equity_df(out)

    # Metrics row
    c1, c2, c3, c4 = st.columns(4)

    final_equity = None
    if not eq_df.empty and "equity" in eq_df.columns:
        final_equity = float(eq_df["equity"].iloc[-1])

    c1.metric("Final equity", f"{final_equity:.2f}" if final_equity is not None else "—")
    c2.metric("CAGR", f"{metrics.get('cagr', 0)*100:.2f}%" if "cagr" in metrics else "—")
    c3.metric("Sharpe", f"{metrics.get('sharpe', 0):.2f}" if "sharpe" in metrics else "—")
    c4.metric("Max drawdown", f"{metrics.get('max_dd', 0)*100:.2f}%" if "max_dd" in metrics else "—")

    st.subheader("Equity curve")
    if not eq_df.empty:
        if "dt" in eq_df.columns and "equity" in eq_df.columns:
            fig = px.line(eq_df, x="dt", y="equity")
        else:
            fig = px.line(eq_df, y="equity")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No equity curve to plot.")

    st.subheader("Trades")
    trades = out.get("trades", [])
    if isinstance(trades, list) and len(trades) > 0:
        st.dataframe(pd.DataFrame(trades), use_container_width=True)
    else:
        st.info("No trades returned.")
