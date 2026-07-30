"""Tushare Pro chip distribution tools for A-shares."""

import asyncio
from datetime import datetime

import pandas as pd

from mcp_stock.server import mcp
from mcp_stock.tushare_client import get_pro_client, to_ts_code


def _validate_date(value: str, parameter: str) -> None:
    if not value:
        return
    if len(value) != 8 or not value.isdigit():
        raise ValueError(f"{parameter} must be in YYYYMMDD format")
    try:
        datetime.strptime(value, "%Y%m%d")
    except ValueError as exc:
        raise ValueError(f"{parameter} must be in YYYYMMDD format") from exc


def _validate_date_parameters(trade_date: str, start_date: str, end_date: str) -> None:
    _validate_date(trade_date, "trade_date")
    _validate_date(start_date, "start_date")
    _validate_date(end_date, "end_date")
    if start_date and end_date and start_date > end_date:
        raise ValueError("start_date must not be after end_date")


def _to_records(df: pd.DataFrame, columns: list[str]) -> list[dict]:
    if df is None or df.empty:
        return []
    available_columns = [column for column in columns if column in df.columns]
    normalized = df[available_columns].rename(columns={"trade_date": "date"})
    normalized = normalized.astype(object).where(pd.notna(normalized), None)
    return normalized.to_dict(orient="records")


@mcp.tool()
async def get_chip_performance(
    symbol: str,
    trade_date: str = "",
    start_date: str = "",
    end_date: str = "",
) -> list[dict]:
    """Get daily A-share chip cost and winner-rate data from Tushare Pro cyq_perf.

    Args:
        symbol: A-share stock code, e.g. "000001" (SZ) or "600519" (SH).
        trade_date: One trading date in YYYYMMDD format. May be combined with a date range.
        start_date: Start date in YYYYMMDD format.
        end_date: End date in YYYYMMDD format.

    Returns:
        Daily historical price bounds, chip cost percentiles, weighted average cost,
        and winner rate.
    """
    _validate_date_parameters(trade_date, start_date, end_date)
    client = get_pro_client()
    df = await asyncio.to_thread(
        client.cyq_perf,
        ts_code=to_ts_code(symbol),
        trade_date=trade_date,
        start_date=start_date,
        end_date=end_date,
    )
    return _to_records(
        df,
        [
            "trade_date",
            "his_low",
            "his_high",
            "cost_5pct",
            "cost_15pct",
            "cost_50pct",
            "cost_85pct",
            "cost_95pct",
            "weight_avg",
            "winner_rate",
        ],
    )


@mcp.tool()
async def get_chip_distribution(
    symbol: str,
    trade_date: str = "",
    start_date: str = "",
    end_date: str = "",
) -> list[dict]:
    """Get daily A-share price-level chip distributions from Tushare Pro cyq_chips.

    Args:
        symbol: A-share stock code, e.g. "000001" (SZ) or "600519" (SH).
        trade_date: One trading date in YYYYMMDD format. May be combined with a date range.
        start_date: Start date in YYYYMMDD format.
        end_date: End date in YYYYMMDD format.

    Returns:
        One record per trading date and chip price level, including its percentage share.
    """
    _validate_date_parameters(trade_date, start_date, end_date)
    client = get_pro_client()
    df = await asyncio.to_thread(
        client.cyq_chips,
        ts_code=to_ts_code(symbol),
        trade_date=trade_date,
        start_date=start_date,
        end_date=end_date,
    )
    return _to_records(df, ["trade_date", "price", "percent"])
