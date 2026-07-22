"""Tushare Pro client setup and A-share symbol normalization."""

import os

import tushare as ts
from tushare.pro.client import DataApi

from mcp_stock.config import REQUEST_TIMEOUT

_pro_client: DataApi | None = None


def get_pro_client() -> DataApi:
    """Return the process-global authenticated Tushare Pro client."""
    global _pro_client
    if _pro_client is not None:
        return _pro_client

    token = os.environ.get("TUSHARE_TOKEN", "").strip()
    if not token:
        raise RuntimeError("TUSHARE_TOKEN is not configured")
    _pro_client = ts.pro_api(token=token, timeout=REQUEST_TIMEOUT)
    return _pro_client


def to_ts_code(symbol: str) -> str:
    """Convert a six-digit A-share code to Tushare's exchange-qualified code."""
    normalized = symbol.strip().upper()
    if "." in normalized:
        return normalized
    if not normalized.isdigit() or len(normalized) != 6:
        raise ValueError("symbol must be a six-digit A-share code or Tushare ts_code")
    if normalized.startswith("6"):
        return f"{normalized}.SH"
    if normalized.startswith(("4", "8", "9")):
        return f"{normalized}.BJ"
    return f"{normalized}.SZ"
