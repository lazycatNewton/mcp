import argparse
import os

from mcp.server.fastmcp import FastMCP

from mcp_stock.tushare_client import get_pro_client

mcp = FastMCP(
    "mcp_stock",
    host=os.getenv("MCP_HOST", "0.0.0.0"),
    port=int(os.getenv("MCP_PORT", "8000")),
)
get_pro_client()

import mcp_stock.tools.history  # noqa: E402, F401
import mcp_stock.tools.market  # noqa: E402, F401

TRANSPORTS = ("stdio", "sse", "streamable-http")


def main():
    parser = argparse.ArgumentParser(description="mcp_stock server")
    parser.add_argument(
        "--transport",
        choices=TRANSPORTS,
        default="stdio",
        help="Transport protocol (default: stdio)",
    )
    args = parser.parse_args()
    mcp.run(transport=args.transport)
