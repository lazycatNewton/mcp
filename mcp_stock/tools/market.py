import asyncio
import logging
from datetime import datetime

import pandas as pd

from mcp_stock.config import NEW_STOCK_WINDOW_DAYS, RATE_LIMIT_DELAY
from mcp_stock.server import mcp
from mcp_stock.tushare_client import get_pro_client

logger = logging.getLogger(__name__)

_ST_PREFIXES = ("*ST", "ST", "S*ST", "SST", "NST", "N*ST")

_STOCK_MARKETS = {"sh", "sz", "bj", "both"}
_TUSHARE_EXCHANGES = {"sh": "SSE", "sz": "SZSE", "bj": "BSE"}
_TUSHARE_MARKETS = {"SSE": "SH", "SZSE": "SZ", "BSE": "BJ"}
_TUSHARE_LIMIT_UP_COLUMN_MAP = {
    "ts_code": "symbol",
    "name": "name",
    "pct_chg": "change_pct",
    "close": "latest_price",
    "amount": "turnover",
    "float_mv": "free_float_market_cap",
    "total_mv": "total_market_cap",
    "turnover_ratio": "turnover_rate",
    "fd_amount": "seal_fund",
    "first_time": "first_limit_time",
    "last_time": "last_limit_time",
    "open_times": "break_limit_count",
    "up_stat": "limit_up_stat",
    "limit_times": "consecutive_limit_up_days",
    "industry": "industry",
}

_TUSHARE_LIMIT_DOWN_COLUMN_MAP = {
    "ts_code": "symbol",
    "name": "name",
    "pct_chg": "change_pct",
    "close": "latest_price",
    "amount": "turnover",
    "float_mv": "free_float_market_cap",
    "total_mv": "total_market_cap",
    "turnover_ratio": "turnover_rate",
    "fd_amount": "seal_fund",
    "last_time": "last_limit_time",
    "open_times": "open_limit_count",
    "limit_times": "consecutive_limit_down_days",
    "industry": "industry",
}


def _default_trade_date() -> str:
    return datetime.now().strftime("%Y%m%d")


def _validate_date(date: str) -> str:
    if not date:
        return _default_trade_date()
    if len(date) != 8 or not date.isdigit():
        raise ValueError("date must be in YYYYMMDD format")
    return date


def _normalize_pool(df: pd.DataFrame, column_map: dict[str, str]) -> list[dict]:
    if df.empty:
        return []
    normalized = df.rename(columns=column_map)
    columns = [column for column in column_map.values() if column in normalized.columns]
    normalized = normalized[columns].astype(object).where(pd.notna(normalized), None)
    if "symbol" in normalized.columns:
        normalized["symbol"] = normalized["symbol"].map(_code_key)
    return normalized.to_dict(orient="records")


def _normalize_stock_records(df: pd.DataFrame) -> list[dict]:
    if df.empty:
        return []

    records = []
    for _, row in df.iterrows():
        exchange = str(row["exchange"]).upper()
        records.append(
            {
                "market": _TUSHARE_MARKETS[exchange],
                "code": _code_key(row["symbol"]),
                "name": None if pd.isna(row["name"]) else str(row["name"]),
            }
        )
    return records


async def _get_market_stocks(market: str) -> list[dict]:
    client = get_pro_client()
    df = await asyncio.to_thread(
        client.stock_basic,
        exchange=_TUSHARE_EXCHANGES[market],
        list_status="L",
        fields="ts_code,symbol,name,exchange",
    )
    return _normalize_stock_records(df)


def _normalize_sector_records(df: pd.DataFrame, sector: str) -> list[dict]:
    """Keep the stable, small response contract for THS index records."""
    if df is None or df.empty or "name" not in df.columns:
        return []

    records = []
    for name in df["name"]:
        if pd.isna(name):
            continue
        records.append({"name": str(name), "sector": sector})
    return records


async def _get_sector_records(client, sector: str) -> list[dict]:
    df = await asyncio.to_thread(client.ths_index, type=sector)
    return _normalize_sector_records(df, sector)


def _is_st_stock_name(name: object) -> bool:
    normalized = str(name or "").strip().upper().replace("＊", "*")
    return normalized.startswith(_ST_PREFIXES)


def _code_key(code: object) -> str:
    return str(code).strip().split(".", maxsplit=1)[0].zfill(6)


def _new_stock_map_from_df(df: pd.DataFrame, date: str) -> dict[str, str | None]:
    if df.empty:
        return {}
    if not {"symbol", "list_date"}.issubset(df.columns):
        return {}
    trade_date = datetime.strptime(date, "%Y%m%d").date()
    mapping = {}
    for _, row in df.iterrows():
        if pd.isna(row["list_date"]):
            continue
        listing_date = str(row["list_date"]).replace("-", "")
        try:
            listed_at = datetime.strptime(listing_date, "%Y%m%d").date()
        except ValueError:
            continue
        if 0 <= (trade_date - listed_at).days <= NEW_STOCK_WINDOW_DAYS:
            mapping[_code_key(row["symbol"])] = listed_at.isoformat()
    return mapping


async def _get_new_stock_map(client, date: str) -> tuple[dict[str, str | None] | None, str]:
    try:
        df = await asyncio.to_thread(
            client.stock_basic,
            list_status="L",
            fields="ts_code,symbol,name,list_date",
        )
        return _new_stock_map_from_df(df, date), "tushare_stock_basic_365_days"
    except Exception as exc:
        logger.warning("Tushare stock_basic for new-stock flags failed: %s", exc)

    return None, "unavailable"


def _apply_stock_flags(records: list[dict], new_stock_map: dict[str, str | None] | None) -> None:
    for record in records:
        symbol = _code_key(record.get("symbol", ""))
        record["is_st"] = _is_st_stock_name(record.get("name"))
        if new_stock_map is None:
            record["is_new_stock"] = None
            record["listing_date"] = None
            continue
        record["is_new_stock"] = symbol in new_stock_map
        record["listing_date"] = new_stock_map.get(symbol)


@mcp.tool()
async def get_stock_list(market: str = "both") -> dict:
    """Get A-share stock list by market, excluding B-shares and other non-A-share lists.

    Args:
        market: Which market to return: "sh" for Shanghai main-board A-shares and STAR Market,
            "sz" for Shenzhen A-shares including ChiNext, "bj" for Beijing Stock Exchange,
            or "both" for all supported markets.
    """
    market = market.strip().lower()
    if market not in _STOCK_MARKETS:
        raise ValueError('market must be one of "sh", "sz", "bj", or "both"')

    selected_markets = ("sh", "sz", "bj") if market == "both" else (market,)
    result: dict = {
        "market": market,
        "source": "tushare",
        "counts": {},
        "stocks": [],
    }

    for selected_market in selected_markets:
        records = await _get_market_stocks(selected_market)

        result["counts"][selected_market] = len(records)
        result["stocks"].extend(records)
        if selected_market != selected_markets[-1]:
            await asyncio.sleep(RATE_LIMIT_DELAY)

    result["counts"]["total"] = len(result["stocks"])
    return result


@mcp.tool()
async def get_sector_list(sector: str = "both") -> list[dict]:
    """Get all Tonghuashun industries and/or concepts from Tushare Pro ths_index.

    Args:
        sector: ``N`` for concepts, ``I`` for industries, or ``both`` for both.

    Returns:
        Records containing only ``name`` and ``sector`` (``N`` or ``I``).
    """
    normalized_sector = sector.strip().upper()
    if normalized_sector not in {"N", "I", "BOTH"}:
        raise ValueError('sector must be one of "N", "I", or "both"')

    client = get_pro_client()
    selected_types = ("N", "I") if normalized_sector == "BOTH" else (normalized_sector,)
    if len(selected_types) == 1:
        return await _get_sector_records(client, selected_types[0])

    # Both requests are independent; issue them concurrently and combine in a
    # deterministic N-then-I order regardless of completion order.
    records = await asyncio.gather(
        *(_get_sector_records(client, selected_type) for selected_type in selected_types)
    )
    return [record for records_for_type in records for record in records_for_type]


@mcp.tool()
async def get_limit_pool(date: str = "", pool: str = "both") -> dict:
    """Get Tushare A-share limit-up and/or limit-down stock pools.

    Args:
        date: Trading date in YYYYMMDD format. Empty uses today's date.
        pool: Which pool to return: "up" for limit-up, "down" for limit-down, or "both".
    """
    trade_date = _validate_date(date)
    pool = pool.lower()
    if pool not in {"up", "down", "both"}:
        raise ValueError('pool must be one of "up", "down", or "both"')

    result: dict = {
        "date": trade_date,
        "source": "tushare",
        "counts": {},
        "flags": {
            "st_source": "stock_name_prefix",
        },
    }

    client = get_pro_client()
    new_stock_map, new_stock_source = await _get_new_stock_map(client, trade_date)
    result["flags"]["new_stock_source"] = new_stock_source
    result["flags"]["new_stock_count"] = None if new_stock_map is None else len(new_stock_map)
    await asyncio.sleep(RATE_LIMIT_DELAY)

    if pool in {"up", "both"}:
        up_df = await asyncio.to_thread(client.limit_list_d, trade_date=trade_date, limit_type="U")
        limit_up = _normalize_pool(up_df, _TUSHARE_LIMIT_UP_COLUMN_MAP)
        _apply_stock_flags(limit_up, new_stock_map)
        result["limit_up"] = limit_up
        result["counts"]["limit_up"] = len(limit_up)
        if pool == "both":
            await asyncio.sleep(RATE_LIMIT_DELAY)

    if pool in {"down", "both"}:
        down_df = await asyncio.to_thread(
            client.limit_list_d, trade_date=trade_date, limit_type="D"
        )
        limit_down = _normalize_pool(down_df, _TUSHARE_LIMIT_DOWN_COLUMN_MAP)
        _apply_stock_flags(limit_down, new_stock_map)
        result["limit_down"] = limit_down
        result["counts"]["limit_down"] = len(limit_down)

    return result
