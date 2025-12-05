import streamlit as st
import requests
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Trading Sim Dashboard", layout="wide")
st.title("Trading Simulation (Backtest → Metrics → Trades)")

api_url = st.sidebar.text_input("API base URL", "http://localhost:8000")
symbol = st.sidebar.text_input("Symbol", "AAPL")
start = st.sidebar.text_input("Start (YYYY-MM-DD)", "2020-01-01")
end = st.sidebar.text_input("End (YYYY-MM-DD)", "2024-01-01")
fast = st.sidebar.slider("Fast SMA", 5, 200, 20)
slow = st.sidebar.slider("Slow SMA", 10, 400, 50)
initial_cash = st.sidebar.number_input("Initial cash", value=10000.0, min_value=100.0)
slippage_bps = st.sidebar.number_input("Slippage (bps)", value=2.0, min_value=0.0)
commission = st.sidebar.number_input("Commission/trade", value=1.0, min_value=0.0)

if st.sidebar.button("Run backtest"):
    payload = {
        "symbol": symbol,
        "start": start,
        "end": end,
        "fast": fast,
        "slow": slow,
        "initial_cash": float(initial_cash),
        "slippage_bps": float(slippage_bps),
        "commission_per_trade": float(commission),
    }

    try:
        r = requests.post(f"{api_url}/backtest", json=payload, timeout=120)
    except Exception as e:
        st.error(f"Could not reach API: {e}")
        st.stop()

    # If API returned an error page/text, show it
    if not r.ok:
        st.error(f"API error {r.status_code}")
        st.code(r.text[:2000])
        st.stop()

    try:
        out = r.json()
    except Exception:
        st.error("API returned non-JSON response:")
        st.code(r.text[:2000])
        st.stop()

    st.subheader("Metrics")
    m = out.get("metrics", {})
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Final equity", f'{out["final_equity"]:.2f}')
    c2.metric("CAGR", f'{m.get("cagr", 0)*100:.2f}%')
    c3.metric("Sharpe", f'{m.get("sharpe", 0):.2f}')
    c4.metric("Max drawdown", f'{m.get("max_drawdown", 0)*100:.2f}%')

    eq = pd.DataFrame(out["equity_curve"])
    eq["dt"] = pd.to_datetime(eq["dt"])
    fig = px.line(eq, x="dt", y="equity", title="Equity curve")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Trades")
    trades = pd.DataFrame(out["trades"])
    st.dataframe(trades, use_container_width=True)
