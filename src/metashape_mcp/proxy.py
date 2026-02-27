"""Stdio-to-HTTP proxy for Metashape MCP server.

Bridges Claude Code (stdio, no timeout) to the Metashape HTTP server
running inside Metashape on port 8765.

Why this exists:
  The HTTP server inside Metashape uses stateless_http=True (required
  because Claude Code returns 406 with stateful SSE). But HTTP transport
  has a client-side read timeout (~60s) that kills long-running tool calls
  like optimize_cameras, build_depth_maps, etc.

  Stdio transport has NO timeout. This proxy sits between Claude Code
  (stdio) and Metashape (HTTP), letting operations run for hours without
  the connection dropping.

Usage:
  python -m metashape_mcp.proxy
"""

from fastmcp import Client
from fastmcp.server import create_proxy

# 24-hour timeout — Metashape operations can take hours (depth maps,
# meshing on large projects). The default httpx timeout (~30s) is what
# was killing long tool calls.
_TIMEOUT_SECONDS = 86400

client = Client(
    "http://127.0.0.1:8765/mcp",
    timeout=_TIMEOUT_SECONDS,
)

proxy = create_proxy(client, name="Metashape")

def main():
    """Entry point for `uvx metashape-mcp` / `pip install metashape-mcp`."""
    proxy.run(transport="stdio")


if __name__ == "__main__":
    main()
