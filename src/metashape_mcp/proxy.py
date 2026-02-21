"""Stdio-to-HTTP proxy for Metashape MCP server.

Bridges Claude Code (stdio) to the Metashape HTTP server running inside
Metashape. Stdio transport has no timeout, so long operations like
matching, alignment, and depth maps block properly until completion.

The HTTP server still runs inside Metashape on port 8765.
This proxy just translates stdio <-> HTTP so Claude Code can wait
indefinitely for operations to finish.
"""

from fastmcp.server import create_proxy

proxy = create_proxy("http://127.0.0.1:8765/mcp", name="Metashape")

if __name__ == "__main__":
    proxy.run()  # Defaults to stdio — no timeout
