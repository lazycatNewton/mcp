import pandas as pd
import pytest

from mcp_stock.tools import market


@pytest.mark.asyncio
async def test_get_limit_pool_returns_limit_up_and_down(monkeypatch):
    monkeypatch.setattr(market, "RATE_LIMIT_DELAY", 0)
    monkeypatch.setattr(
        market.ak,
        "stock_zt_pool_sub_new_em",
        lambda date: pd.DataFrame(
            [
                {
                    "代码": "603629",
                    "名称": "*ST利通",
                    "上市日期": "2026-06-01",
                }
            ]
        ),
    )
    monkeypatch.setattr(
        market.ak,
        "stock_zt_pool_em",
        lambda date: pd.DataFrame(
            [
                {
                    "序号": 1,
                    "代码": "603629",
                    "名称": "*ST利通",
                    "涨跌幅": 10.01,
                    "最新价": 18.88,
                    "成交额": 1000000,
                    "流通市值": 2000000,
                    "总市值": 3000000,
                    "换手率": 5.5,
                    "封板资金": float("nan"),
                    "首次封板时间": "093001",
                    "最后封板时间": "145501",
                    "炸板次数": 0,
                    "涨停统计": "1/1",
                    "连板数": 1,
                    "所属行业": "电子元件",
                }
            ]
        ),
    )
    monkeypatch.setattr(
        market.ak,
        "stock_zt_pool_dtgc_em",
        lambda date: pd.DataFrame(
            [
                {
                    "序号": 1,
                    "代码": "000001",
                    "名称": "平安银行",
                    "涨跌幅": -10.0,
                    "最新价": 9.99,
                    "成交额": 1000000,
                    "流通市值": 2000000,
                    "总市值": 3000000,
                    "动态市盈率": 6.5,
                    "换手率": 3.2,
                    "封单资金": 700000,
                    "最后封板时间": "142501",
                    "板上成交额": 200000,
                    "连续跌停": 1,
                    "开板次数": 0,
                    "所属行业": "银行",
                }
            ]
        ),
    )

    result = await market.get_limit_pool(date="20260701", pool="both")

    assert result["date"] == "20260701"
    assert result["source"] == "eastmoney"
    assert result["flags"] == {
        "st_source": "stock_name_prefix",
        "new_stock_source": "eastmoney_sub_new_pool",
        "new_stock_count": 1,
    }
    assert result["counts"] == {"limit_up": 1, "limit_down": 1}
    assert result["limit_up"][0]["symbol"] == "603629"
    assert result["limit_up"][0]["seal_fund"] is None
    assert result["limit_up"][0]["is_st"] is True
    assert result["limit_up"][0]["is_new_stock"] is True
    assert result["limit_up"][0]["listing_date"] == "2026-06-01"
    assert result["limit_up"][0]["consecutive_limit_up_days"] == 1
    assert result["limit_down"][0]["symbol"] == "000001"
    assert result["limit_down"][0]["is_st"] is False
    assert result["limit_down"][0]["is_new_stock"] is False
    assert result["limit_down"][0]["listing_date"] is None
    assert result["limit_down"][0]["consecutive_limit_down_days"] == 1


@pytest.mark.asyncio
async def test_get_limit_pool_can_return_only_limit_up(monkeypatch):
    monkeypatch.setattr(market, "RATE_LIMIT_DELAY", 0)
    monkeypatch.setattr(market.ak, "stock_zt_pool_sub_new_em", lambda date: pd.DataFrame())
    monkeypatch.setattr(market.ak, "stock_zt_pool_em", lambda date: pd.DataFrame())

    def fail_if_called(date):
        raise AssertionError("limit-down pool should not be queried")

    monkeypatch.setattr(market.ak, "stock_zt_pool_dtgc_em", fail_if_called)

    result = await market.get_limit_pool(date="20260701", pool="up")

    assert result["counts"] == {"limit_up": 0}
    assert result["limit_up"] == []
    assert "limit_down" not in result


@pytest.mark.asyncio
async def test_get_limit_pool_falls_back_to_sina_new_stock_pool(monkeypatch):
    monkeypatch.setattr(market, "RATE_LIMIT_DELAY", 0)

    def fail_sub_new(date):
        raise RuntimeError("eastmoney unavailable")

    monkeypatch.setattr(market.ak, "stock_zt_pool_sub_new_em", fail_sub_new)
    monkeypatch.setattr(
        market.ak,
        "stock_zh_a_new",
        lambda: pd.DataFrame([{"code": "920003", "name": "中诚咨询"}]),
    )
    monkeypatch.setattr(
        market.ak,
        "stock_zt_pool_dtgc_em",
        lambda date: pd.DataFrame(
            [
                {
                    "序号": 1,
                    "代码": "920003",
                    "名称": "中诚咨询",
                    "涨跌幅": -10.0,
                    "最新价": 9.99,
                    "成交额": 1000000,
                    "流通市值": 2000000,
                    "总市值": 3000000,
                    "动态市盈率": 6.5,
                    "换手率": 3.2,
                    "封单资金": 700000,
                    "最后封板时间": "142501",
                    "板上成交额": 200000,
                    "连续跌停": 1,
                    "开板次数": 0,
                    "所属行业": "咨询服务",
                }
            ]
        ),
    )

    result = await market.get_limit_pool(date="20260701", pool="down")

    assert result["flags"]["new_stock_source"] == "sina_new_stock_pool"
    assert result["flags"]["new_stock_count"] == 1
    assert result["limit_down"][0]["is_new_stock"] is True
    assert result["limit_down"][0]["listing_date"] is None


@pytest.mark.asyncio
async def test_get_limit_pool_rejects_invalid_arguments():
    with pytest.raises(ValueError, match="YYYYMMDD"):
        await market.get_limit_pool(date="2026-07-01")

    with pytest.raises(ValueError, match="pool must be"):
        await market.get_limit_pool(date="20260701", pool="flat")
