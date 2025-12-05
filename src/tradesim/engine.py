from __future__ import annotations
import pandas as pd
import numpy as np
from dataclasses import dataclass
from .core import Portfolio, Position, Order, Fill, Side
from .strategy import SMACrossover

@dataclass
class SimConfig:
    initial_cash: float = 10_000.0
    commission_per_trade: float = 1.0          # flat commission
    slippage_bps: float = 2.0                  # 1 bp = 0.01%
    allow_fractional: bool = True

def _apply_slippage(price: float, side: Side, slippage_bps: float) -> tuple[float, float]:
    slip = (slippage_bps / 10_000.0) * price
    if side == Side.BUY:
        return price + slip, slip
    else:
        return price - slip, slip

def run_backtest_single_asset(
    ohlcv: pd.DataFrame,
    symbol: str,
    strategy: SMACrossover,
    cfg: SimConfig = SimConfig(),
) -> dict:
    """
    Generate signal at bar close, fill at next bar open.
    Single asset, long/flat.
    """
    df = ohlcv.copy().sort_index()
    if "open" not in df.columns or "close" not in df.columns:
        raise ValueError("OHLCV must include open and close columns.")

    portfolio = Portfolio(cash=cfg.initial_cash, position=Position(symbol=symbol, qty=0.0, avg_price=0.0))
    fills: list[Fill] = []
    pending: list[Order] = []

    equity_curve = []
    trade_log = []

    idx = df.index.to_list()
    for i in range(len(idx) - 1):
        dt = idx[i]
        next_dt = idx[i + 1]
        bar = df.loc[dt]
        next_open = float(df.loc[next_dt, "open"])

        pos_qty = portfolio.position.qty if portfolio.position else 0.0
        mtm = portfolio.cash + pos_qty * float(bar["close"])
        equity_curve.append({"dt": dt, "equity": mtm, "cash": portfolio.cash, "pos_qty": pos_qty})

        # Fill pending orders at next open
        new_pending: list[Order] = []
        for order in pending:
            qty = order.qty
            if qty == -1.0 and order.side == Side.BUY:
                target_value = strategy.risk_fraction * mtm
                qty = target_value / next_open
                if not cfg.allow_fractional:
                    qty = float(np.floor(qty))
                if qty <= 0:
                    continue

            exec_price, slip = _apply_slippage(next_open, order.side, cfg.slippage_bps)
            commission = cfg.commission_per_trade

            if order.side == Side.BUY:
                cost = qty * exec_price + commission
                if cost > portfolio.cash:
                    continue
                portfolio.cash -= cost
                portfolio.position.qty += qty

                prev_qty = portfolio.position.qty - qty
                prev_cost = prev_qty * portfolio.position.avg_price
                new_cost = qty * exec_price
                portfolio.position.avg_price = (prev_cost + new_cost) / (prev_qty + qty) if (prev_qty + qty) > 0 else exec_price

            else:  # SELL
                sell_qty = min(qty, portfolio.position.qty)
                if sell_qty <= 0:
                    continue
                proceeds = sell_qty * exec_price - commission
                portfolio.cash += proceeds
                portfolio.position.qty -= sell_qty
                if portfolio.position.qty <= 1e-12:
                    portfolio.position.qty = 0.0
                    portfolio.position.avg_price = 0.0

            fills.append(Fill(
                symbol=symbol, side=order.side, qty=float(qty),
                price=float(exec_price), commission=float(commission),
                slippage=float(slip), filled_at=next_dt, reason=order.reason
            ))
            trade_log.append({
                "filled_at": next_dt, "side": order.side.value, "qty": float(qty),
                "price": float(exec_price), "commission": float(commission),
                "slippage": float(slip), "reason": order.reason
            })

        pending = new_pending

        # Generate new orders at bar close (history up to dt)
        hist = df.loc[:dt]
        orders = strategy.generate_orders(symbol=symbol, dt=dt, hist=hist, equity=mtm, current_qty=portfolio.position.qty)
        pending.extend(orders)

    # Final mark-to-market
    last_dt = idx[-1]
    last_close = float(df.loc[last_dt, "close"])
    final_equity = portfolio.cash + portfolio.position.qty * last_close
    equity_curve.append({"dt": last_dt, "equity": final_equity, "cash": portfolio.cash, "pos_qty": portfolio.position.qty})

    trades = pd.DataFrame(trade_log)
    return {
        "symbol": symbol,
        "final_equity": float(final_equity),
        "equity_curve": pd.DataFrame(equity_curve).to_dict(orient="records"),
        "trades": trades.to_dict(orient="records"),
        "fills_count": len(fills),
    }
