"""FastMCP server entry point for Metashape MCP.

This module creates the MCP server and registers all tools, resources,
and prompts. It can be started embedded inside Metashape or standalone.
"""

from mcp.server.fastmcp import FastMCP

from metashape_mcp.tools import register_all_tools
from metashape_mcp.resources import register_all_resources
from metashape_mcp.prompts import register_all_prompts

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
        "4. Tool calls block until the Metashape operation completes. "
        "Operations can take hours or days. Never set timeouts. Never poll."
    ),
    stateless_http=True,
    json_response=True,
    port=8765,
)

register_all_tools(mcp)
register_all_resources(mcp)
register_all_prompts(mcp)


def main():
    """Run server with Streamable HTTP transport (default for Claude Desktop)."""
    mcp.run(transport="streamable-http")


def start_background():
    """Start server in a background thread (for embedding inside Metashape).

    Call this from Metashape's Python console or a startup script:
        >>> from metashape_mcp.server import start_background
        >>> start_background()
    """
    import sys
    import threading

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

    thread = threading.Thread(
        target=lambda: mcp.run(transport="streamable-http"),
        daemon=True,
    )
    thread.start()
    print("Metashape MCP server started on http://127.0.0.1:8765/mcp")
    return thread


if __name__ == "__main__":
    main()
