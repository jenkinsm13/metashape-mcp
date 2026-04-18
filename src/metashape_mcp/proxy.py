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

import asyncio
import atexit
import os

from fastmcp import Client
from fastmcp.server import create_proxy

# 24-hour timeout — Metashape operations can take hours (depth maps,
# meshing on large projects). The default httpx timeout (~30s) is what
# was killing long tool calls.
_TIMEOUT_SECONDS = 86400

# allow the port to be overridden for multi-instance setups.  the same
# environment variable (`METASHAPE_MCP_PORT`) is used by the
# `server.start_background` helpers so users only need to set it once.
port = int(os.environ.get("METASHAPE_MCP_PORT", "8765"))
url = f"http://127.0.0.1:{port}/mcp"

client = Client(
    url,
    timeout=_TIMEOUT_SECONDS,
)

proxy = create_proxy(client, name="Metashape")


def _send_cancel():
    """Best-effort cancel request to the Metashape MCP server.

    Called when the proxy exits (stdio disconnected, user interrupted,
    process killed). Sends cancel_processing to abort any in-flight
    Metashape operation so the server thread is freed for future requests.
    """
    try:
        cancel_client = Client(url, timeout=5)

        async def _do_cancel():
            async with cancel_client:
                await cancel_client.call_tool("cancel_processing")

        # Use a fresh event loop — the main one may be closed/broken
        asyncio.run(_do_cancel())
    except Exception:
        pass  # Best effort — server may already be idle or unreachable


def main():
    """Entry point for `uvx metashape-mcp` / `pip install metashape-mcp`."""
    # Register cancel-on-exit so interrupted tool calls don't block
    # the server's thread pool for subsequent requests.
    atexit.register(_send_cancel)

    try:
        proxy.run(transport="stdio")
    except (KeyboardInterrupt, BrokenPipeError, EOFError):
        # stdio disconnected — cancel any running operation
        _send_cancel()
    except SystemExit:
        _send_cancel()
        raise


if __name__ == "__main__":
    main()
