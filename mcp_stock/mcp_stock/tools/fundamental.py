from mcp_stock.server import mcp


@mcp.tool()
async def get_financial_data(symbol: str) -> dict:
    """Get fundamental financial data: PE, PB, market cap, dividend yield, etc.

    Args:
        symbol: Stock code. A-shares as "000001", HK as "00700", US as "AAPL".
    """
    ...
