"""Debug: inspect the MCP server's implemented tool inventory."""

import asyncio

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    params = StdioServerParameters(
        command="uv",
        args=["run", "python", "-m", "mcp_stock"],
        cwd="/Users/didiapp/dev/mcp/mcp_stock",
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print(f"Tools: {[t.name for t in tools.tools]}")


asyncio.run(main())
