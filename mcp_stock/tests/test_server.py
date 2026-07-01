import pytest
from mcp_stock.server import mcp


@pytest.mark.asyncio
async def test_server_has_tools():
    """Server should have at least one tool registered."""
    tools = await mcp.list_tools()
    assert len(tools) > 0
