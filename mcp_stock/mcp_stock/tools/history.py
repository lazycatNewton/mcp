import asyncio
import logging

import akshare as ak
import pandas as pd

from mcp_stock.config import RATE_LIMIT_DELAY
from mcp_stock.server import mcp

logger = logging.getLogger(__name__)

_SZ_PREFIXES = ("000", "001", "002", "003", "300", "301")
_SH_PREFIXES = ("600", "601", "603", "605", "688")

OUTPUT_COLUMNS = ["date", "open", "close", "high", "low", "volume", "amount"]

# stock_zh_a_hist uses Chinese column names
_HIST_COLUMN_MAP = {
    "日期": "date",
    "开盘": "open",
    "收盘": "close",
    "最高": "high",
    "最低": "low",
    "成交量": "volume",
    "成交额": "amount",
}

# stock_zh_a_daily uses English column names
_DAILY_COLUMN_MAP = {
    "date": "date",
    "open": "open",
    "close": "close",
    "high": "high",
    "low": "low",
    "volume": "volume",
    "amount": "amount",
}


def _prefixed_symbol(symbol: str) -> str:
    if symbol.startswith(_SZ_PREFIXES):
        return f"sz{symbol}"
    if symbol.startswith(_SH_PREFIXES):
        return f"sh{symbol}"
    return f"sz{symbol}"


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
    # 1. Try eastmoney first (supports daily/weekly/monthly)
    try:
        df = await asyncio.to_thread(
            ak.stock_zh_a_hist,
            symbol=symbol,
            period=period,
            start_date=start_date,
            end_date=end_date,
            adjust=adjust,
        )
        df = _normalize(df, _HIST_COLUMN_MAP)
        df = _filter_date(df, start_date, end_date)
        await asyncio.sleep(RATE_LIMIT_DELAY)
        return _to_records(df)
    except Exception:
        logger.warning(
            "stock_zh_a_hist failed, falling back to stock_zh_a_daily (daily only)"
        )

    # 2. Fallback to sina (daily only)
    df = await asyncio.to_thread(
        ak.stock_zh_a_daily,
        symbol=_prefixed_symbol(symbol),
        adjust=adjust,
    )
    df = _normalize(df, _DAILY_COLUMN_MAP)
    df = _filter_date(df, start_date, end_date)
    await asyncio.sleep(RATE_LIMIT_DELAY)
    return _to_records(df)
