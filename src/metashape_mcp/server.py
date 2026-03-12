"""FastMCP server entry point for Metashape MCP.

This module creates the MCP server and registers all tools, resources,
and prompts. It can be started embedded inside Metashape or standalone.
"""

from mcp.server.fastmcp import FastMCP

from metashape_mcp.tools import register_all_tools
from metashape_mcp.resources import register_all_resources
from metashape_mcp.prompts import register_all_prompts


# the port can now be configured per-session.  callers may pass a port
# value to :func:`create_mcp`, :func:`main` or :func:`start_background`, or
# set the METASHAPE_MCP_PORT environment variable.  the global ``mcp`` is
# no longer created at import time; instead each start call makes a fresh
# instance which allows restarts with a different port.

DEFAULT_PORT = 8765


def create_mcp(port: int | None = None) -> FastMCP:
    """Build and register a FastMCP instance bound to ``port``.

    Args:
        port: TCP port for the HTTP transport; falls back to
            ``METASHAPE_MCP_PORT`` env var or ``DEFAULT_PORT``.
    """
    if port is None:
        env = os.environ.get("METASHAPE_MCP_PORT")
        if env:
            try:
                port = int(env)
            except ValueError:  # pragma: no cover - unlikely
                port = DEFAULT_PORT
        else:
            port = DEFAULT_PORT

    mcp = FastMCP(
        name="Metashape",
        instructions=(
            "MCP server for Agisoft Metashape Professional 2.3+. "
            "Provides tools covering the full photogrammetry pipeline: "
            "project management, photo import, alignment, dense reconstruction, "
            "mesh generation, texturing, survey product creation, export/import, "
            "markers/GCPs, coordinate systems, and network processing. "
            "All processing operates on the currently active chunk unless "
            "specified otherwise. Use resources to inspect project state "
            "before running tools.\n\n"
            "CRITICAL AGENT RULES:\n"
            "1. NEVER write pipeline scripts that batch multiple MCP tool calls. "
            "You are an AI AGENT — call each tool INDIVIDUALLY, inspect the result, "
            "reason about it, then decide and call the next tool. Writing a Python "
            "script that chains tool calls defeats the entire purpose of MCP. "
            "Every Metashape tool call must be a separate agent action.\n"
            "2. ALWAYS pass keep_keypoints=True when calling match_photos. "
            "Without it, incremental batch alignment fails because keypoints "
            "are discarded after matching.\n"
            "3. GPU/CPU RULE: Enable CPU (set_gpu_config(cpu_enable=True)) "
            "ONLY during alignment (match_photos, align_cameras). For ALL other "
            "operations (depth maps, meshing, texturing), DISABLE CPU "
            "(set_gpu_config(cpu_enable=False)) — CPU slows GPU operations.\n"
            "4. USGS tie point filtering: RU=10, PA=3, RE=0.3. "
            "NEVER remove more than 50% of tie points in one pass. "
            "The filter_tie_points tool enforces this automatically.\n"
            "5. Tool calls block until the Metashape operation completes. "
            "Operations can take hours or days. Never set timeouts. Never poll."
        ),
        stateless_http=True,
        json_response=True,
        port=port,
    )

    register_all_tools(mcp)
    register_all_resources(mcp)
    register_all_prompts(mcp)

    return mcp

# internal state for restart support
_last_thread = None
_last_mcp = None


def main(port: int | None = None):
    """Run server in the foreground on the requested port.

    ``port`` may be passed directly or configured via the
    ``METASHAPE_MCP_PORT`` environment variable.  This function is called
    when ``__main__`` is executed and is also useful for standalone testing.
    """
    mcp = create_mcp(port)
    mcp.run(transport="streamable-http")


def start_background(port: int | None = None):
    """Start (or restart) the MCP server on a background thread.

    ``port`` overrides the default value.  If a server is already running
    in this interpreter and the requested port differs, an attempt is made to
    shut it down before starting the new instance.  The current thread object
    is returned (useful for testing or shutdown checks).

    This is the entrypoint used by ``scripts/start_mcp_server.py`` and can be
    called from Metashape's Python console.
    """
    import sys
    import threading

    # ensure stdout/stderr behave like real ttys for uvicorn's logger
    class _StdWrapper:
        def __init__(self, inner):
            self._inner = inner
        def write(self, s):
            return self._inner.write(s)
        def flush(self):
            if hasattr(self._inner, "flush"):
                self._inner.flush()
        def isatty(self):
            return False

    if not hasattr(sys.stdout, "isatty"):
        sys.stdout = _StdWrapper(sys.stdout)
    if not hasattr(sys.stderr, "isatty"):
        sys.stderr = _StdWrapper(sys.stderr)

    global _last_thread, _last_mcp

    # if a server is already active with a different port, try to stop it
    if _last_thread and _last_thread.is_alive():
        if port is None or port == _last_mcp.port:
            print(
                f"MCP server already running on port {_last_mcp.port}, "
                "skipping start request."
            )
            return _last_thread
        else:
            print(f"Shutting down MCP on port {_last_mcp.port}…")
            try:
                _last_mcp.shutdown()
            except Exception:  # graceful stop not available
                print("Warning: previous MCP server may still be running.")

    # create new instance with requested port and launch
    mcp = create_mcp(port)
    _last_mcp = mcp

    thread = threading.Thread(
        target=lambda: mcp.run(transport="streamable-http"),
        daemon=True,
    )
    thread.start()
    _last_thread = thread

    print(
        f"Metashape MCP server started on http://127.0.0.1:{mcp.port}/mcp"
    )
    return thread


if __name__ == "__main__":
    # allow CLI override via METASHAPE_MCP_PORT env var
    main()
