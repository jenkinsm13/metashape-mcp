"""Stdio-to-HTTP proxy for Metashape MCP server.

Bridges Claude Code (stdio, no timeout) to Metashape HTTP server.
Uses FastMCP create_proxy for proper MCP protocol handling.
"""

from fastmcp.server import create_proxy

proxy = create_proxy("http://127.0.0.1:8765/mcp", name="Metashape")

if __name__ == "__main__":
    proxy.run(transport="stdio")
