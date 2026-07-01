# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## Project Goal

Build an MCP (Model Context Protocol) server that provides stock market data tools. The server exposes tools for querying real-time quotes, historical prices, financial indicators, and market indices — making stock data accessible to AI assistants via the MCP protocol.

## Tech Stack

- **Language**: Python 3.11+
- **MCP Framework**: `fastmcp` (high-level decorator-based API from the official `mcp` Python SDK)
- **Stock Data Source**: AKShare (primary — free, no API key, best coverage for A-shares and HK; limited US market data)
- **Transport**: stdio for local use; SSE can be added later for remote deployment
- **Package Management**: uv (preferred) or pip
- **Testing**: pytest + pytest-asyncio
- **Linting/Formatting**: ruff

## Commands

```bash
# Install dependencies
uv sync

# Run the MCP server locally (stdio transport)
uv run python -m mcp_stock

# Run tests
uv run pytest

# Run a single test
uv run pytest tests/test_server.py::test_function_name -v

# Lint
uv run ruff check mcp_stock/

# Format
uv run ruff format mcp_stock/
```

## Architecture

The server follows the standard MCP pattern: tools are regular Python functions decorated with `@mcp.tool()`, organized by data category.

### Module Layout

```
mcp_stock/
├── server.py          # FastMCP server instance, entry point
├── tools/             # Tool definitions grouped by category
│   ├── __init__.py
│   ├── quote.py       # Real-time/delayed quote tools
│   ├── history.py     # Historical OHLCV data tools
│   ├── fundamental.py # Financial statements, PE/PB, dividends
│   └── market.py      # Index data, market breadth, sectors
├── config.py          # Configuration (default timeouts, rate limits)
└── __main__.py        # python -m mcp_stock entry point
pyproject.toml         # Project metadata, dependencies, ruff config
tests/
├── conftest.py        # Shared fixtures (e.g., mock AKShare responses)
├── test_server.py
└── test_tools/
```

### Key Design Rules

- Each tool function is self-contained and returns JSON-serializable data (dicts, lists, primitives)
- AKShare calls run in a thread executor (`asyncio.to_thread`) to avoid blocking the event loop
- Stock codes use standard formats: A-shares as `"000001"`, HK as `"00700"`, US as `"AAPL"` — tools accept strings and normalize internally if needed
- Rate-limit AKShare calls with a small delay between requests to avoid being blocked
- Tool descriptions are written for LLM consumption — include parameter formats and what data is returned
- Never cache data in-process. MCP clients handle caching if needed

### Adding a New Tool

1. Create or add to the appropriate module under `tools/`
2. Decorate with `@mcp.tool()` using a clear, LLM-friendly description
3. Use type hints for all parameters and return types
4. Import the module in `server.py` so the `@mcp.tool()` decorator registers it
5. Add tests with mocked AKShare responses
