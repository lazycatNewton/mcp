import pandas as pd
import pytest

from mcp_stock.tools import market


@pytest.mark.asyncio
async def test_get_stock_list_returns_exchange_records(monkeypatch):
    monkeypatch.setattr(market, "RATE_LIMIT_DELAY", 0)

    class Client:
        def stock_basic(self, **kwargs):
            assert kwargs["exchange"] == "SSE"
            return pd.DataFrame(
                [
                    {
                        "ts_code": "600000.SH",
                        "symbol": "600000",
                        "name": "浦发银行",
                        "exchange": "SSE",
                    }
                ]
            )

    monkeypatch.setattr(market, "get_pro_client", Client)
    result = await market.get_stock_list(market="sh")

    assert result == {
        "market": "sh",
        "source": "tushare",
        "counts": {"sh": 1, "total": 1},
        "stocks": [{"market": "SH", "code": "600000", "name": "浦发银行"}],
    }


@pytest.mark.asyncio
async def test_get_stock_list_rejects_invalid_market():
    with pytest.raises(ValueError, match="market must be"):
        await market.get_stock_list(market="hk")


@pytest.mark.asyncio
async def test_get_limit_pool_returns_limit_up_and_down(monkeypatch):
    monkeypatch.setattr(market, "RATE_LIMIT_DELAY", 0)

    class Client:
        def stock_basic(self, **kwargs):
            return pd.DataFrame(
                [
                    {"symbol": "603629", "list_date": "20260601"},
                    {"symbol": "000001", "list_date": "19910403"},
                ]
            )

        def limit_list_d(self, trade_date, limit_type):
            assert trade_date == "20260701"
            if limit_type == "U":
                return pd.DataFrame([{"ts_code": "603629.SH", "name": "*ST利通", "limit_times": 1}])
            return pd.DataFrame([{"ts_code": "000001.SZ", "name": "平安银行", "limit_times": 1}])

    monkeypatch.setattr(market, "get_pro_client", Client)
    result = await market.get_limit_pool(date="20260701", pool="both")

    assert result["source"] == "tushare"
    assert result["counts"] == {"limit_up": 1, "limit_down": 1}
    assert result["limit_up"][0]["symbol"] == "603629"
    assert result["limit_up"][0]["is_st"] is True
    assert result["limit_up"][0]["is_new_stock"] is True
    assert result["limit_down"][0]["symbol"] == "000001"
    assert result["limit_down"][0]["is_st"] is False


@pytest.mark.asyncio
async def test_get_limit_pool_can_return_only_limit_up(monkeypatch):
    monkeypatch.setattr(market, "RATE_LIMIT_DELAY", 0)

    class Client:
        def stock_basic(self, **kwargs):
            return pd.DataFrame(columns=["symbol", "list_date"])

        def limit_list_d(self, trade_date, limit_type):
            assert limit_type == "U"
            return pd.DataFrame()

    monkeypatch.setattr(market, "get_pro_client", Client)
    result = await market.get_limit_pool(date="20260701", pool="up")

    assert result["counts"] == {"limit_up": 0}
    assert result["limit_up"] == []
    assert "limit_down" not in result
