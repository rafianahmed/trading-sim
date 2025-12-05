# Trading Simulation Dashboard (Backtest → Metrics → Trades)

A simple trading backtesting project with a Streamlit dashboard.  
Runs in **Local mode** (recommended for Streamlit Cloud) and optionally supports **API mode** (FastAPI).

## Live Demo
- Streamlit App: https://trading-sim-9gwdm9jspbewurgisgvirf.streamlit.app 
- GitHub Repo: https://github.com/rafianahmed/trading-sim

## Features
- SMA Crossover strategy backtest
- Equity curve chart (Plotly)
- Metrics: Final equity, CAGR, Sharpe, Max Drawdown
- Two run modes:
  - **Local**: backtest runs inside Streamlit (best for deployment)
  - **API**: Streamlit calls FastAPI `/backtest` endpoint

## Tech Stack
- Python, pandas, numpy
- Streamlit, Plotly
- FastAPI + Uvicorn (optional API mode)
- pytest

## Run Locally (Windows PowerShell)

### 1) Create & activate venv
```powershell
cd "$env:USERPROFILE\Desktop\Trading-sim"
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt


