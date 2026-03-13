"""Stdio-to-HTTP proxy for Metashape MCP server.

Bridges Claude Code (stdio, no timeout) to Metashape HTTP server.
Uses FastMCP create_proxy for proper MCP protocol handling.

For multi-instance support, use the multiplexer instead:
    python -m metashape_mcp.multiplexer

This simple proxy connects to a single instance. Set METASHAPE_MCP_PORT
to override the default port (8765).
"""

import os

from fastmcp.server import create_proxy

_port = os.environ.get("METASHAPE_MCP_PORT", "8765")
_url = f"http://127.0.0.1:{_port}/mcp"

proxy = create_proxy(_url, name="Metashape")

if __name__ == "__main__":
    proxy.run(transport="stdio")
