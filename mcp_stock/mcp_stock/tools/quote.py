from mcp_stock.server import mcp


@mcp.tool()
async def get_realtime_quote(symbol: str) -> dict:
    """Get real-time/delayed stock quote for a given symbol.

    Args:
        symbol: Stock code. A-shares as "000001", HK as "00700", US as "AAPL".
    """
    ...
