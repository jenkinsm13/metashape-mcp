"""Tool registration for all Metashape MCP tools.

Each tool module exports a `register(mcp)` function that decorates
its tools with @mcp.tool(). This __init__ collects them all.
"""

from metashape_mcp.tools import (
    alignment,
    camera,
    coordinate,
    dense,
    export,
    import_data,
    markers,
    mesh,
    network,
    photos,
    project,
    scripting,
    survey,
    texture,
    viewport,
)

_MODULES = [
    project,
    photos,
    camera,
    alignment,
    dense,
    mesh,
    texture,
    survey,
    export,
    import_data,
    markers,
    coordinate,
    network,
    viewport,
    scripting,
]


def register_all_tools(mcp) -> None:
    """Register all tool modules with the MCP server."""
    for module in _MODULES:
        module.register(mcp)
