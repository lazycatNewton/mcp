import asyncio
import logging
from datetime import datetime

import akshare as ak
import pandas as pd

from mcp_stock.config import RATE_LIMIT_DELAY
from mcp_stock.server import mcp

logger = logging.getLogger(__name__)

_LIMIT_UP_COLUMN_MAP = {
    "序号": "rank",
    "代码": "symbol",
    "名称": "name",
    "涨跌幅": "change_pct",
    "最新价": "latest_price",
    "成交额": "turnover",
    "流通市值": "free_float_market_cap",
    "总市值": "total_market_cap",
    "换手率": "turnover_rate",
    "封板资金": "seal_fund",
    "首次封板时间": "first_limit_time",
    "最后封板时间": "last_limit_time",
    "炸板次数": "break_limit_count",
    "涨停统计": "limit_up_stat",
    "连板数": "consecutive_limit_up_days",
    "所属行业": "industry",
}

_LIMIT_DOWN_COLUMN_MAP = {
    "序号": "rank",
    "代码": "symbol",
    "名称": "name",
    "涨跌幅": "change_pct",
    "最新价": "latest_price",
    "成交额": "turnover",
    "流通市值": "free_float_market_cap",
    "总市值": "total_market_cap",
    "动态市盈率": "pe_dynamic",
    "换手率": "turnover_rate",
    "封单资金": "seal_fund",
    "最后封板时间": "last_limit_time",
    "板上成交额": "limit_board_turnover",
    "连续跌停": "consecutive_limit_down_days",
    "开板次数": "open_limit_count",
    "所属行业": "industry",
}

_ST_PREFIXES = ("*ST", "ST", "S*ST", "SST", "NST", "N*ST")

_STOCK_MARKETS = {"sh", "sz", "bj", "both"}


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
    return normalized.to_dict(orient="records")


def _normalize_stock_records(
    df: pd.DataFrame, *, market: str, code_column: str, name_column: str
) -> list[dict]:
    if df.empty:
        return []

    records = []
    for _, row in df.iterrows():
        records.append(
            {
                "market": market,
                "code": _code_key(row[code_column]),
                "name": None if pd.isna(row[name_column]) else str(row[name_column]),
            }
        )
    return records


async def _get_sh_stocks() -> list[dict]:
    records = []
    for board in ("主板A股", "科创板"):
        df = await asyncio.to_thread(ak.stock_info_sh_name_code, symbol=board)
        records.extend(
            _normalize_stock_records(
                df,
                market="SH",
                code_column="证券代码",
                name_column="证券简称",
            )
        )
        await asyncio.sleep(RATE_LIMIT_DELAY)
    return records


async def _get_sz_stocks() -> list[dict]:
    df = await asyncio.to_thread(ak.stock_info_sz_name_code, symbol="A股列表")
    return _normalize_stock_records(
        df,
        market="SZ",
        code_column="A股代码",
        name_column="A股简称",
    )


async def _get_bj_stocks() -> list[dict]:
    df = await asyncio.to_thread(ak.stock_info_bj_name_code)
    return _normalize_stock_records(
        df,
        market="BJ",
        code_column="证券代码",
        name_column="证券简称",
    )


def _is_st_stock_name(name: object) -> bool:
    normalized = str(name or "").strip().upper().replace("＊", "*")
    return normalized.startswith(_ST_PREFIXES)


def _code_key(code: object) -> str:
    return str(code).strip().zfill(6)


def _new_stock_map_from_df(df: pd.DataFrame) -> dict[str, str | None]:
    if df.empty:
        return {}
    if "代码" in df.columns:
        code_column = "代码"
    elif "code" in df.columns:
        code_column = "code"
    else:
        return {}

    listing_column = "上市日期" if "上市日期" in df.columns else None
    mapping = {}
    for _, row in df.iterrows():
        listing_date = None
        if listing_column:
            raw_listing_date = row[listing_column]
            if pd.notna(raw_listing_date):
                listing_date = str(raw_listing_date)
        mapping[_code_key(row[code_column])] = listing_date
    return mapping


async def _get_new_stock_map(date: str) -> tuple[dict[str, str | None] | None, str]:
    try:
        df = await asyncio.to_thread(ak.stock_zt_pool_sub_new_em, date=date)
        return _new_stock_map_from_df(df), "eastmoney_sub_new_pool"
    except Exception as exc:
        logger.warning("stock_zt_pool_sub_new_em failed: %s", exc)

    try:
        df = await asyncio.to_thread(ak.stock_zh_a_new)
        return _new_stock_map_from_df(df), "sina_new_stock_pool"
    except Exception as exc:
        logger.warning("stock_zh_a_new failed: %s", exc)

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
async def get_market_index(index_code: str = "") -> dict:
    """Get major market index data (SSE Composite, SZSE Component, CSI 300, etc.).

    Args:
        index_code: Index code, e.g. "sh000001" for SSE Composite. Empty returns all major indices.
    """
    ...


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
        "source": "akshare",
        "counts": {},
        "stocks": [],
    }

    for selected_market in selected_markets:
        if selected_market == "sh":
            records = await _get_sh_stocks()
        elif selected_market == "sz":
            records = await _get_sz_stocks()
        else:
            records = await _get_bj_stocks()

        result["counts"][selected_market] = len(records)
        result["stocks"].extend(records)
        if selected_market != selected_markets[-1]:
            await asyncio.sleep(RATE_LIMIT_DELAY)

    result["counts"]["total"] = len(result["stocks"])
    return result


@mcp.tool()
async def get_limit_pool(date: str = "", pool: str = "both") -> dict:
    """Get EastMoney A-share limit-up and/or limit-down stock pools.

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
        "source": "eastmoney",
        "counts": {},
        "flags": {
            "st_source": "stock_name_prefix",
        },
    }

    new_stock_map, new_stock_source = await _get_new_stock_map(trade_date)
    result["flags"]["new_stock_source"] = new_stock_source
    result["flags"]["new_stock_count"] = None if new_stock_map is None else len(new_stock_map)
    await asyncio.sleep(RATE_LIMIT_DELAY)

    if pool in {"up", "both"}:
        up_df = await asyncio.to_thread(ak.stock_zt_pool_em, date=trade_date)
        limit_up = _normalize_pool(up_df, _LIMIT_UP_COLUMN_MAP)
        _apply_stock_flags(limit_up, new_stock_map)
        result["limit_up"] = limit_up
        result["counts"]["limit_up"] = len(limit_up)
        await asyncio.sleep(RATE_LIMIT_DELAY)

    if pool in {"down", "both"}:
        down_df = await asyncio.to_thread(ak.stock_zt_pool_dtgc_em, date=trade_date)
        limit_down = _normalize_pool(down_df, _LIMIT_DOWN_COLUMN_MAP)
        _apply_stock_flags(limit_down, new_stock_map)
        result["limit_down"] = limit_down
        result["counts"]["limit_down"] = len(limit_down)
        await asyncio.sleep(RATE_LIMIT_DELAY)

    return result
