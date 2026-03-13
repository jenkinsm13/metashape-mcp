"""FastMCP server entry point for Metashape MCP.

This module creates the MCP server and registers all tools, resources,
and prompts. It can be started embedded inside Metashape or standalone.

Multi-instance support:
  - Port is auto-assigned from range 8765-8784 (or set via METASHAPE_MCP_PORT env var)
  - A discovery file is written to %LOCALAPPDATA%/metashape-mcp/instances/{port}.json
  - The multiplexer proxy reads these files to find and switch between instances
"""

import os

from mcp.server.fastmcp import FastMCP

from metashape_mcp.tools import register_all_tools
from metashape_mcp.resources import register_all_resources
from metashape_mcp.prompts import register_all_prompts
from metashape_mcp.discovery import find_free_port

DEFAULT_PORT = 8765


def _resolve_port(port: int | None = None) -> int:
    """Determine the port to use: explicit > env var > auto-assign > default."""
    if port is not None:
        return port
    env = os.environ.get("METASHAPE_MCP_PORT", "")
    if env:
        try:
            return int(env)
        except ValueError:
            pass
    try:
        return find_free_port()
    except RuntimeError:
        return DEFAULT_PORT


def create_mcp(port: int | None = None) -> FastMCP:
    """Build and register a FastMCP instance bound to ``port``.

    Args:
        port: TCP port for the HTTP transport.  Falls back to
            ``METASHAPE_MCP_PORT`` env var, then auto-assignment
            from 8765-8784, then ``DEFAULT_PORT``.
    """
    resolved = _resolve_port(port)

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
        port=resolved,
    )

    register_all_tools(mcp)
    register_all_resources(mcp)
    register_all_prompts(mcp)

    return mcp


# Internal state for restart support
_last_thread = None
_last_mcp = None


def get_port() -> int:
    """Return the port the active server is using (or the resolved default)."""
    if _last_mcp is not None:
        return _last_mcp.settings.port
    return _resolve_port()


def main(port: int | None = None):
    """Run server with Streamable HTTP transport (default for Claude Desktop).

    ``port`` may be passed directly or configured via the
    ``METASHAPE_MCP_PORT`` environment variable.
    """
    mcp = create_mcp(port)
    mcp.run(transport="streamable-http")


def start_background(port: int | None = None):
    """Start (or restart) the MCP server on a background thread.

    Call this from Metashape's Python console or a startup script:
        >>> from metashape_mcp.server import start_background
        >>> start_background()

    If a server is already running and the requested port differs,
    it will attempt to shut down the old one before starting the new one.
    """
    import sys
    import threading

    from metashape_mcp.discovery import register_instance

    # Metashape's PyStdout lacks isatty() which uvicorn's logger needs.
    # Can't monkey-patch it (C++ object), so wrap it.
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

    resolved = _resolve_port(port)

    # If a server is already active, handle restart
    if _last_thread and _last_thread.is_alive():
        if resolved == _last_mcp.settings.port:
            print(
                f"MCP server already running on port {resolved}, "
                "skipping start request."
            )
            return _last_thread
        else:
            print(f"Shutting down MCP on port {_last_mcp.settings.port}...")
            try:
                _last_mcp.shutdown()
            except Exception:
                print("Warning: previous MCP server may still be running.")

    # Create new instance
    mcp = create_mcp(resolved)
    _last_mcp = mcp

    # Get project info for the discovery file
    project_path = ""
    metashape_version = ""
    try:
        import Metashape
        metashape_version = Metashape.app.version
        if Metashape.app.document and Metashape.app.document.path:
            project_path = Metashape.app.document.path
    except Exception:
        pass

    # Register this instance for discovery
    register_instance(resolved, project_path=project_path, metashape_version=metashape_version)

    thread = threading.Thread(
        target=lambda: mcp.run(transport="streamable-http"),
        daemon=True,
    )
    thread.start()
    _last_thread = thread

    print(f"Metashape MCP server started on http://127.0.0.1:{resolved}/mcp")
    return thread


if __name__ == "__main__":
    main()
