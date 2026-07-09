import pandas as pd
import pytest

from mcp_stock.tools import market


@pytest.mark.asyncio
async def test_get_stock_list_returns_sh_main_and_star_market(monkeypatch):
    monkeypatch.setattr(market, "RATE_LIMIT_DELAY", 0)
    calls = []

    def stock_info_sh_name_code(symbol):
        calls.append(symbol)
        if symbol == "主板A股":
            return pd.DataFrame(
                [
                    {
                        "证券代码": "600000",
                        "证券简称": "浦发银行",
                        "证券全称": "上海浦东发展银行股份有限公司",
                        "公司简称": "浦发银行",
                        "公司全称": "上海浦东发展银行股份有限公司",
                        "上市日期": pd.Timestamp("1999-11-10").date(),
                    }
                ]
            )
        return pd.DataFrame(
            [
                {
                    "证券代码": "688001",
                    "证券简称": "华兴源创",
                    "证券全称": "苏州华兴源创科技股份有限公司",
                    "公司简称": "华兴源创",
                    "公司全称": "苏州华兴源创科技股份有限公司",
                    "上市日期": pd.Timestamp("2019-07-22").date(),
                }
            ]
        )

    monkeypatch.setattr(market.ak, "stock_info_sh_name_code", stock_info_sh_name_code)

    result = await market.get_stock_list(market="sh")

    assert calls == ["主板A股", "科创板"]
    assert result["market"] == "sh"
    assert result["source"] == "akshare"
    assert result["counts"] == {"sh": 2, "total": 2}
    assert result["stocks"] == [
        {"market": "SH", "code": "600000", "name": "浦发银行"},
        {"market": "SH", "code": "688001", "name": "华兴源创"},
    ]


@pytest.mark.asyncio
async def test_get_stock_list_returns_sz_a_shares(monkeypatch):
    monkeypatch.setattr(market, "RATE_LIMIT_DELAY", 0)

    def stock_info_sz_name_code(symbol):
        assert symbol == "A股列表"
        return pd.DataFrame(
            [
                {
                    "板块": "主板",
                    "A股代码": "000001",
                    "A股简称": "平安银行",
                    "A股上市日期": "1991-04-03",
                    "A股总股本": 19405918198,
                    "A股流通股本": 19405754675,
                    "所属行业": "金融业",
                },
                {
                    "板块": "创业板",
                    "A股代码": "300001",
                    "A股简称": "特锐德",
                    "A股上市日期": "2009-10-30",
                    "A股总股本": 1058690071,
                    "A股流通股本": 990175075,
                    "所属行业": "制造业",
                },
            ]
        )

    monkeypatch.setattr(market.ak, "stock_info_sz_name_code", stock_info_sz_name_code)

    result = await market.get_stock_list(market="sz")

    assert result["counts"] == {"sz": 2, "total": 2}
    assert result["stocks"] == [
        {"market": "SZ", "code": "000001", "name": "平安银行"},
        {"market": "SZ", "code": "300001", "name": "特锐德"},
    ]


@pytest.mark.asyncio
async def test_get_stock_list_returns_bj_stocks(monkeypatch):
    monkeypatch.setattr(market, "RATE_LIMIT_DELAY", 0)
    monkeypatch.setattr(
        market.ak,
        "stock_info_bj_name_code",
        lambda: pd.DataFrame(
            [
                {
                    "证券代码": "920002",
                    "证券简称": "万达轴承",
                    "总股本": 50000000,
                    "流通股本": 25000000,
                    "上市日期": pd.Timestamp("2024-05-30"),
                    "所属行业": "制造业",
                    "地区": "江苏",
                    "报告日期": pd.Timestamp("2026-03-31"),
                }
            ]
        ),
    )

    result = await market.get_stock_list(market="bj")

    assert result["counts"] == {"bj": 1, "total": 1}
    assert result["stocks"][0] == {
        "market": "BJ",
        "code": "920002",
        "name": "万达轴承",
    }


@pytest.mark.asyncio
async def test_get_stock_list_both_combines_supported_markets(monkeypatch):
    monkeypatch.setattr(market, "RATE_LIMIT_DELAY", 0)

    async def get_sh_stocks():
        return [{"market": "SH", "code": "600000", "name": "浦发银行"}]

    async def get_sz_stocks():
        return [{"market": "SZ", "code": "000001", "name": "平安银行"}]

    async def get_bj_stocks():
        return [{"market": "BJ", "code": "920002", "name": "万达轴承"}]

    monkeypatch.setattr(market, "_get_sh_stocks", get_sh_stocks)
    monkeypatch.setattr(market, "_get_sz_stocks", get_sz_stocks)
    monkeypatch.setattr(market, "_get_bj_stocks", get_bj_stocks)

    result = await market.get_stock_list()

    assert result["market"] == "both"
    assert result["counts"] == {"sh": 1, "sz": 1, "bj": 1, "total": 3}
    assert result["stocks"] == [
        {"market": "SH", "code": "600000", "name": "浦发银行"},
        {"market": "SZ", "code": "000001", "name": "平安银行"},
        {"market": "BJ", "code": "920002", "name": "万达轴承"},
    ]


@pytest.mark.asyncio
async def test_get_stock_list_rejects_invalid_market():
    with pytest.raises(ValueError, match="market must be"):
        await market.get_stock_list(market="hk")


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
