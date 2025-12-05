from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .data import load_ohlcv_yahoo
from .strategy import SMACrossover
from .engine import run_backtest_single_asset, SimConfig
from .metrics import performance_metrics

app = FastAPI(title="Trading Simulation API", version="1.0.0")


class BacktestRequest(BaseModel):
    symbol: str = Field(default="AAPL")
    start: str = Field(default="2020-01-01")
    end: str = Field(default="2024-01-01")
    fast: int = Field(default=20, ge=2, le=300)
    slow: int = Field(default=50, ge=3, le=600)
    initial_cash: float = Field(default=10000.0, gt=0)
    slippage_bps: float = Field(default=2.0, ge=0)
    commission_per_trade: float = Field(default=1.0, ge=0)


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/backtest")
def backtest(req: BacktestRequest):
    try:
        # Validate params
        if req.fast >= req.slow:
            raise HTTPException(status_code=400, detail="fast must be < slow")

        # Load data
        df = load_ohlcv_yahoo(req.symbol, req.start, req.end, interval="1d")

        # Run strategy + simulation
        strat = SMACrossover(fast=req.fast, slow=req.slow, risk_fraction=0.95)
        cfg = SimConfig(
            initial_cash=req.initial_cash,
            slippage_bps=req.slippage_bps,
            commission_per_trade=req.commission_per_trade,
            allow_fractional=True,
        )

        out = run_backtest_single_asset(df, req.symbol, strat, cfg)
        out["metrics"] = performance_metrics(out["equity_curve"])
        return out

    except HTTPException:
        # Re-raise our own clean API errors
        raise
    except ValueError as e:
        # Expected “bad input / no data” cases
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Unexpected failures: always return JSON error
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")
