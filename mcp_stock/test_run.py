"""Debug: inspect tool call results structure."""
import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    params = StdioServerParameters(
        command="uv", args=["run", "python", "-m", "mcp_stock"],
        cwd="/Users/didiapp/dev/mcp/mcp_stock",
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            print(f"Tools: {[t.name for t in tools.tools]}")

            # Test get_market_index
            result = await session.call_tool("get_market_index", {})
            print(f"\nget_market_index result type: {type(result)}")
            print(f"  isError: {result.isError}")
            print(f"  content len: {len(result.content)}")
            for i, c in enumerate(result.content):
                print(f"  content[{i}] type: {type(c).__name__}")
                print(f"  content[{i}] dir: {[x for x in dir(c) if not x.startswith('_')]}")
                if hasattr(c, "text"):
                    text = c.text
                    print(f"  text len: {len(text)}")
                    print(f"  text[:500]: {text[:500]}")
                if hasattr(c, "data"):
                    print(f"  data: {c.data}")
                if hasattr(c, "type"):
                    print(f"  type attr: {c.type}")

            # Test get_historical_data
            result2 = await session.call_tool(
                "get_historical_data",
                {"symbol": "000001", "start_date": "20250101", "end_date": "20250110"},
            )
            print(f"\nget_historical_data result:")
            print(f"  isError: {result2.isError}")
            print(f"  content len: {len(result2.content)}")
            for i, c in enumerate(result2.content):
                print(f"  content[{i}] type: {type(c).__name__}")
                if hasattr(c, "text"):
                    text = c.text
                    print(f"  text len: {len(text)}")
                    print(f"  text[:500]: {text[:500]}")

asyncio.run(main())
