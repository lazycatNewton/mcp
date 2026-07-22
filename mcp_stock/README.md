# mcp-stock

MCP server that provides A-share stock market data via the Model Context Protocol.

## Cold Start

```bash
# 1. Create and activate environment
conda create -n mcp_stock python=3.11 -y
conda activate mcp_stock

# 2. Install dependencies
pip install mcp>=1.0.0 tushare>=1.4.29
pip install pytest>=8.0 pytest-asyncio>=0.24 ruff>=0.6  # dev

# 3. Verify the server starts
python -m mcp_stock --help

# 4. Run (stdio transport, for use with Claude Desktop / MCP clients)
python -m mcp_stock

# 5. Run with alternative transports
python -m mcp_stock --transport sse
python -m mcp_stock --transport streamable-http
```

本 MCP 的唯一数据源是 Tushare Pro。使用历史行情、股票清单或涨跌停池前，必须在 MCP
进程环境中设置 `TUSHARE_TOKEN`。

## MCP Client Configuration

将此 JSON 添加到 MCP 客户端配置文件中（如 Claude Desktop 的 `claude_desktop_config.json`）：

```json
{
  "mcpServers": {
    "mcp-stock": {
      "command": "conda",
      "args": ["run", "-n", "mcp_stock", "python", "-m", "mcp_stock"],
      "cwd": "/Users/didiapp/dev/mcp/mcp_stock"
    }
  }
}
```

如需直接使用 Python 解释器：

```json
{
  "mcpServers": {
    "mcp-stock": {
      "command": "python",
      "args": ["-m", "mcp_stock"],
      "cwd": "/Users/didiapp/dev/mcp/mcp_stock",
      "env": {
        "CONDA_PREFIX": "/opt/anaconda3/envs/mcp_stock",
        "PATH": "/opt/anaconda3/envs/mcp_stock/bin:/usr/bin:/bin"
      }
    }
  }
}
```

## MCP Tools

当前 MCP 仅注册以下三个已实现工具。

### `get_historical_data`

作用：查询单只 A 股的日、周或月 OHLCV 历史行情，并支持前复权、后复权或不复权。

数据源：Tushare Pro `pro_bar`；需要具备相应权限的 `TUSHARE_TOKEN`。股票代码会自动转换为
Tushare 格式，例如 `000001` 转为 `000001.SZ`。

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `symbol` | str | — | Stock code, e.g. `"000001"` (SZ), `"600519"` (SH) |
| `start_date` | str | `""` | Start date in `YYYYMMDD` format |
| `end_date` | str | `""` | End date in `YYYYMMDD` format |
| `period` | str | `"daily"` | `"daily"`, `"weekly"`, or `"monthly"` |
| `adjust` | str | `"qfq"` | `"qfq"` (前复权), `"hfq"` (后复权), `""` (不复权) |

输出：`list[dict]`，每项固定包含 `date`、`open`、`close`、`high`、`low`、`volume`、`amount`。

### `get_stock_list`

作用：按交易所返回当前上市的 A 股基础证券清单，不包含 B 股等非 A 股证券。

数据源：Tushare Pro `stock_basic`。

| 输入 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `market` | str | `"both"` | `"sh"`、`"sz"`、`"bj"` 或 `"both"` |

输出：字典，包含请求的 `market`、`source: "tushare"`、分市场及总计的 `counts`，以及
`stocks` 数组。每只股票包含 `market`（`SH`/`SZ`/`BJ`）、六位 `code` 和 `name`。

### `get_limit_pool`

作用：按交易日查询 A 股涨停池、跌停池或两者，并补充 ST 和次新股标记。

数据源：Tushare Pro `limit_list_d`；次新股标记由 `stock_basic` 的上市日期计算。名称以 ST
前缀识别 ST 股票，上市日期距目标交易日不超过 365 天识别为次新股。

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `date` | str | `""` | Trading date in `YYYYMMDD` format; empty uses today |
| `pool` | str | `"both"` | `"up"`, `"down"`, or `"both"` |

输出：字典，包含 `date`、`source: "tushare"`、`counts`、`flags` 和按请求出现的
`limit_up` / `limit_down` 数组。股票记录使用六位 `symbol`，并尽可能包含 `name`、
`change_pct`、`latest_price`、成交额、市值、封单资金、连板数、行业等字段；每项均附带
`is_st`、`is_new_stock`、`listing_date`。字段是否存在取决于 Tushare 当次返回的权限与数据。
