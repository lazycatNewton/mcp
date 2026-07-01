import argparse

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("mcp-stock")

# Patch requests before tool imports so AKShare skips the system proxy
import mcp_stock._http  # noqa: E402, F401

import mcp_stock.tools.fundamental  # noqa: E402, F401
import mcp_stock.tools.history  # noqa: E402, F401
import mcp_stock.tools.market  # noqa: E402, F401
import mcp_stock.tools.quote  # noqa: E402, F401

TRANSPORTS = ("stdio", "sse", "streamable-http")


def main():
    parser = argparse.ArgumentParser(description="mcp-stock server")
    parser.add_argument(
        "--transport",
        choices=TRANSPORTS,
        default="stdio",
        help="Transport protocol (default: stdio)",
    )
    args = parser.parse_args()
    mcp.run(transport=args.transport)
