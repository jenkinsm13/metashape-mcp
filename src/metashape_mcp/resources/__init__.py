"""Resource registration for all Metashape MCP resources."""

from metashape_mcp.resources import camera_info, processing, project_info

_MODULES = [project_info, camera_info, processing]


def register_all_resources(mcp) -> None:
    """Register all resource modules with the MCP server."""
    for module in _MODULES:
        module.register(mcp)
