import pandas as pd
import pytest

from mcp_stock import tushare_client
from mcp_stock.tools import history


@pytest.mark.asyncio
async def test_get_historical_data_uses_tushare_pro_bar(monkeypatch):
    calls = []

    def pro_bar(**kwargs):
        calls.append(kwargs)
        return pd.DataFrame(
            [
                {
                    "trade_date": "20260701",
                    "open": 10,
                    "close": 11,
                    "high": 12,
                    "low": 9,
                    "vol": 100,
                    "amount": 1000,
                }
            ]
        )

    client = object()
    monkeypatch.setattr(history, "get_pro_client", lambda: client)
    monkeypatch.setattr(history.ts, "pro_bar", pro_bar)

    result = await history.get_historical_data("600519", "20260701", "20260701", "daily", "qfq")

    assert calls == [
        {
            "ts_code": "600519.SH",
            "api": client,
            "start_date": "20260701",
            "end_date": "20260701",
            "freq": "D",
            "adj": "qfq",
        }
    ]
    assert result == [
        {
            "date": "20260701",
            "open": 10,
            "close": 11,
            "high": 12,
            "low": 9,
            "volume": 100,
            "amount": 1000,
        }
    ]


def test_to_ts_code_rejects_invalid_symbol():
    with pytest.raises(ValueError, match="six-digit"):
        history.to_ts_code("AAPL")


def test_get_pro_client_requires_token(monkeypatch):
    monkeypatch.setattr(tushare_client, "_pro_client", None)
    monkeypatch.delenv("TUSHARE_TOKEN", raising=False)

    with pytest.raises(RuntimeError, match="TUSHARE_TOKEN"):
        tushare_client.get_pro_client()


def test_get_pro_client_is_process_global(monkeypatch):
    created_client = object()
    calls = []
    monkeypatch.setattr(tushare_client, "_pro_client", None)
    monkeypatch.setenv("TUSHARE_TOKEN", "test-token")
    monkeypatch.setattr(
        tushare_client.ts,
        "pro_api",
        lambda **kwargs: calls.append(kwargs) or created_client,
    )

    assert tushare_client.get_pro_client() is created_client
    assert tushare_client.get_pro_client() is created_client
    assert calls == [{"token": "test-token", "timeout": tushare_client.REQUEST_TIMEOUT}]
