from __future__ import annotations

import io
import pandas as pd
import yfinance as yf
import requests


def _normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    rename_map = {
        "Open": "open", "High": "high", "Low": "low", "Close": "close",
        "Volume": "volume",
        "open": "open", "high": "high", "low": "low", "close": "close",
        "volume": "volume",
    }
    df = df.rename(columns=rename_map)

    required = ["open", "high", "low", "close", "volume"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Data missing columns: {missing}. Got: {list(df.columns)}")

    df = df[required].copy()
    df.index = pd.to_datetime(df.index)
    df = df.dropna()
    return df


def _fetch_stooq_daily(symbol: str, start: str, end: str) -> pd.DataFrame:
    sym = (symbol or "").strip().lower()
    if "." not in sym:
        sym = sym + ".us"  # AAPL -> aapl.us for stooq

    url = f"https://stooq.com/q/d/l/?s={sym}&i=d"
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)

    if r.status_code != 200:
        raise ValueError(f"Stooq HTTP {r.status_code}")

    text = (r.text or "").strip()
    if not text or text.startswith("<"):
        raise ValueError("Stooq returned empty/HTML (possibly blocked)")

    raw = pd.read_csv(io.StringIO(text))
    if "Date" not in raw.columns:
        raise ValueError(f"Unexpected Stooq columns: {list(raw.columns)}")

    raw["Date"] = pd.to_datetime(raw["Date"])
    raw = raw.set_index("Date").sort_index()
    raw = raw.loc[pd.to_datetime(start):pd.to_datetime(end)]

    if raw.empty:
        raise ValueError("Stooq returned no rows for that date range")

    return _normalize_ohlcv(raw)


def load_ohlcv_yahoo(symbol: str, start: str, end: str, interval: str = "1d") -> pd.DataFrame:
    symbol = (symbol or "").strip()

    # Try 1: yfinance download
    df = yf.download(
        symbol,
        start=start,
        end=end,
        interval=interval,
        auto_adjust=False,
        progress=False,
        threads=False,
    )
    if df is not None and not df.empty:
        return _normalize_ohlcv(df)

    # Try 2: yfinance history  ✅ THIS LINE WAS BROKEN BEFORE
    df = yf.Ticker(symbol).history(
        start=start,
        end=end,
        interval=interval,
        auto_adjust=False,
    )
    if df is not None and not df.empty:
        return _normalize_ohlcv(df)

    # Try 3: Stooq direct CSV (daily only)
    if interval != "1d":
        raise ValueError("Only interval='1d' supported when Yahoo returns no data.")

    try:
        return _fetch_stooq_daily(symbol, start, end)
    except Exception as e:
        raise ValueError(
            f"No data returned for {symbol}. Yahoo may be blocked/rate-limited and Stooq failed: {e}"
        )
