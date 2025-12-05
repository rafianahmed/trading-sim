from __future__ import annotations
import pandas as pd
from dataclasses import dataclass
from .core import Order, Side

@dataclass
class SMACrossover:
    fast: int = 20
    slow: int = 50
    risk_fraction: float = 0.95  # fraction of equity to allocate when long

    def generate_orders(
        self,
        symbol: str,
        dt: pd.Timestamp,
        hist: pd.DataFrame,
        equity: float,
        current_qty: float
    ) -> list[Order]:
        # Need enough data to compute MAs
        if len(hist) < self.slow + 2:
            return []

        close = hist["close"]
        fast_ma = close.rolling(self.fast).mean().iloc[-1]
        slow_ma = close.rolling(self.slow).mean().iloc[-1]

        orders: list[Order] = []

        want_long = fast_ma > slow_ma
        have_long = current_qty > 0

        if want_long and not have_long:
            # qty == -1 means "size me with risk_fraction at next open"
            orders.append(Order(symbol=symbol, side=Side.BUY, qty=-1.0, created_at=dt, reason="SMA cross long"))
        elif (not want_long) and have_long:
            orders.append(Order(symbol=symbol, side=Side.SELL, qty=current_qty, created_at=dt, reason="SMA cross exit"))

        return orders
