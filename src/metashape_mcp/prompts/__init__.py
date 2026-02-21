"""Prompt registration for all Metashape MCP prompts."""

from metashape_mcp.prompts import troubleshooting, workflows

_MODULES = [workflows, troubleshooting]


def register_all_prompts(mcp) -> None:
    """Register all prompt modules with the MCP server."""
    for module in _MODULES:
        module.register(mcp)
