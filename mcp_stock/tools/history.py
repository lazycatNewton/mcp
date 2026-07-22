import asyncio

import pandas as pd
import tushare as ts

from mcp_stock.server import mcp
from mcp_stock.tushare_client import get_pro_client, to_ts_code

OUTPUT_COLUMNS = ["date", "open", "close", "high", "low", "volume", "amount"]

_HIST_COLUMN_MAP = {
    "trade_date": "date",
    "open": "open",
    "close": "close",
    "high": "high",
    "low": "low",
    "vol": "volume",
    "amount": "amount",
}


def _normalize(df: pd.DataFrame, column_map: dict) -> pd.DataFrame:
    df = df.rename(columns=column_map)
    available = [c for c in OUTPUT_COLUMNS if c in df.columns]
    return df[available]


def _filter_date(df: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    if "date" not in df.columns:
        return df
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y%m%d")
    if start:
        df = df[df["date"] >= start]
    if end:
        df = df[df["date"] <= end]
    return df


def _to_records(df: pd.DataFrame) -> list[dict]:
    return df[OUTPUT_COLUMNS].to_dict(orient="records")


@mcp.tool()
async def get_historical_data(
    symbol: str,
    start_date: str = "",
    end_date: str = "",
    period: str = "daily",
    adjust: str = "qfq",
) -> list[dict]:
    """Get historical OHLCV data for an A-share stock.

    Args:
        symbol: A-share stock code, e.g. "000001" (SZ) or "600519" (SH).
        start_date: Start date in YYYYMMDD format (e.g. "20240101").
        end_date: End date in YYYYMMDD format.
        period: Data frequency — "daily", "weekly", or "monthly".
        adjust: Price adjustment — "qfq" (前复权, default), "hfq" (后复权), or "" (不复权).
    """
    if period not in {"daily", "weekly", "monthly"}:
        raise ValueError('period must be one of "daily", "weekly", or "monthly"')
    if adjust not in {"qfq", "hfq", ""}:
        raise ValueError('adjust must be one of "qfq", "hfq", or ""')

    frequency = {"daily": "D", "weekly": "W", "monthly": "M"}[period]
    client = get_pro_client()
    df = await asyncio.to_thread(
        ts.pro_bar,
        ts_code=to_ts_code(symbol),
        api=client,
        start_date=start_date,
        end_date=end_date,
        freq=frequency,
        adj=adjust or None,
    )
    if df is None:
        return []
    df = _normalize(df, _HIST_COLUMN_MAP)
    df = _filter_date(df, start_date, end_date)
    return _to_records(df)
