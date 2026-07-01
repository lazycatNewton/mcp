from mcp_stock.server import mcp


@mcp.tool()
async def get_market_index(index_code: str = "") -> dict:
    """Get major market index data (SSE Composite, SZSE Component, CSI 300, etc.).

    Args:
        index_code: Index code, e.g. "sh000001" for SSE Composite. Empty returns all major indices.
    """
    ...
