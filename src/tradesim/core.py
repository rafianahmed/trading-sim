from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Optional

class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

@dataclass(frozen=True)
class Order:
    symbol: str
    side: Side
    qty: float  # shares/units
    created_at: object  # timestamp-like (engine will pass pd.Timestamp)
    reason: str = ""

@dataclass(frozen=True)
class Fill:
    symbol: str
    side: Side
    qty: float
    price: float
    commission: float
    slippage: float
    filled_at: object
    reason: str = ""

@dataclass
class Position:
    symbol: str
    qty: float = 0.0
    avg_price: float = 0.0

@dataclass
class Portfolio:
    cash: float
    position: Optional[Position] = None
