import os
import subprocess
import sys

import pytest

from mcp_stock.server import mcp


@pytest.mark.asyncio
async def test_server_has_tools():
    """Server should register only implemented tools."""
    tools = await mcp.list_tools()
    assert {tool.name for tool in tools} == {
        "get_historical_data",
        "get_limit_pool",
        "get_stock_list",
    }


def test_server_requires_tushare_token():
    environment = os.environ.copy()
    environment.pop("TUSHARE_TOKEN", None)
    result = subprocess.run(
        [sys.executable, "-c", "import mcp_stock.server"],
        capture_output=True,
        env=environment,
        text=True,
    )

    assert result.returncode != 0
    assert "TUSHARE_TOKEN is not configured" in result.stderr
