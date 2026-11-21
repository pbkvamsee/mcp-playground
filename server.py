
import os
from fastmcp import FastMCP

mcp = FastMCP("My First MCP Server")

@mcp.tool
def say_hello(name: str) -> str:
    """Say hello to someone by name."""
    return f"Hello {name}! This message is coming from my MCP server in the cloud."

if __name__ == "__main__":
    mcp.run(
        transport="http",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000))
    )
