# mcp-stock

MCP server that provides A-share stock market data via the Model Context Protocol.

## Cold Start

```bash
# 1. Create and activate environment
conda create -n mcp_stock python=3.11 -y
conda activate mcp_stock

# 2. Install dependencies
pip install mcp>=1.0.0 akshare>=1.14.0
pip install pytest>=8.0 pytest-asyncio>=0.24 ruff>=0.6  # dev

# 3. Verify the server starts
python -m mcp_stock --help

# 4. Run (stdio transport, for use with Claude Desktop / MCP clients)
python -m mcp_stock

# 5. Run with alternative transports
python -m mcp_stock --transport sse
python -m mcp_stock --transport streamable-http
```

**Proxy note:** If you have a system proxy configured, the server patches `requests` to skip it by default. Set `TRUST_SYSTEM_PROXY = True` in `mcp_stock/config.py` if you need the proxy for EastMoney API access.

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

### `get_historical_data`

Get historical daily/weekly/monthly OHLCV data for A-share stocks.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `symbol` | str | — | Stock code, e.g. `"000001"` (SZ), `"600519"` (SH) |
| `start_date` | str | `""` | Start date in `YYYYMMDD` format |
| `end_date` | str | `""` | End date in `YYYYMMDD` format |
| `period` | str | `"daily"` | `"daily"`, `"weekly"`, or `"monthly"` |
| `adjust` | str | `"qfq"` | `"qfq"` (前复权), `"hfq"` (后复权), `""` (不复权) |

Returns `list[dict]` with fields: `date`, `open`, `close`, `high`, `low`, `volume`, `amount`.

Data source: EastMoney (primary, supports all periods), falls back to Sina (daily only) on network failure.

### `get_realtime_quote` *(not yet implemented)*

Get real-time/delayed quote for a stock.

### `get_financial_data` *(not yet implemented)*

Get fundamental data: PE, PB, market cap, dividend yield.

### `get_market_index` *(not yet implemented)*

Get major market index data (SSE Composite, SZSE Component, CSI 300, etc.).
