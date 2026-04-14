"""Metashape MCP Multiplexer — route tool calls to multiple Metashape instances.

Runs as a stdio MCP server (for Claude Code). Discovers running Metashape
instances from discovery files and forwards all MCP traffic to the active
instance. Provides two extra tools for instance management:

  - list_instances: Show all running Metashape instances
  - switch_instance: Switch which instance receives tool calls

Architecture:
  Claude Code --stdio--> Multiplexer --HTTP--> Metashape Instance A (:8765)
                                     --HTTP--> Metashape Instance B (:8766)
                                     --HTTP--> Metashape Instance C (:8767)

Usage:
    python -m metashape_mcp.multiplexer
    python multiplexer.py  (also works — auto-adds src/ to sys.path)
"""

# Ensure package is importable when run as a script (not via -m)
import sys
from pathlib import Path
_src = str(Path(__file__).resolve().parent.parent)
if _src not in sys.path:
    sys.path.insert(0, _src)

import json
import logging

import httpx
import mcp.types as types
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server

from metashape_mcp.discovery import discover_instances

logger = logging.getLogger(__name__)

# ── State ─────────────────────────────────────────────────────────

_active_url: str | None = None
_active_port: int | None = None
_cached_tools: list[dict] = []


# ── Own tool definitions ──────────────────────────────────────────

_OWN_TOOLS = [
    types.Tool(
        name="list_instances",
        description=(
            "List all running Metashape MCP server instances. "
            "Shows port, PID, project path, start time, and which is active. "
            "Use switch_instance to change the active instance."
        ),
        inputSchema={
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
    ),
    types.Tool(
        name="switch_instance",
        description=(
            "Switch the active Metashape instance by port number. "
            "All subsequent tool calls will be forwarded to this instance. "
            "Use list_instances first to see available ports."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "port": {
                    "type": "number",
                    "description": "Port number of the Metashape instance to switch to.",
                },
            },
            "required": ["port"],
            "additionalProperties": False,
        },
    ),
]


# ── HTTP forwarding ───────────────────────────────────────────────

async def _post_mcp(url: str, method: str, params: dict | None = None,
                    timeout: float | None = None) -> dict:
    """Send a JSON-RPC request to a Metashape Streamable HTTP endpoint.

    Args:
        url: The MCP endpoint URL.
        method: JSON-RPC method name.
        params: Method parameters.
        timeout: Read/write timeout in seconds. Use a large value for
            long-running operations (exports, builds). Connect timeout
            is always 15s.
    """
    request_body = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params or {},
        "id": 1,
    }
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(timeout, connect=15.0, pool=60.0)
    ) as client:
        resp = await client.post(
            url,
            json=request_body,
            headers={
                "Accept": "application/json, text/event-stream",
                "Content-Type": "application/json",
            },
        )
        resp.raise_for_status()
        return resp.json()


async def _fetch_tools(url: str) -> list[dict]:
    """Fetch tool list from a Metashape MCP instance."""
    try:
        result = await _post_mcp(url, "tools/list", timeout=15.0)
        if "result" in result and "tools" in result["result"]:
            return result["result"]["tools"]
    except Exception as e:
        logger.warning("Failed to fetch tools from %s: %s", url, e)
    return []


async def _forward_tool_call(url: str, name: str, arguments: dict) -> dict:
    """Forward a tool call to the active instance.

    Uses a generous timeout (4 hours) rather than None so that truly dead
    connections are eventually cleaned up, but long Metashape operations
    (8K texture export, dense cloud build, etc.) can complete.
    """
    return await _post_mcp(
        url, "tools/call",
        {"name": name, "arguments": arguments},
        timeout=14400.0,  # 4 hours — covers even multi-hour processing
    )


# ── Local tool handlers ──────────────────────────────────────────

async def _query_project_info(port: int) -> dict | None:
    """Ask a Metashape instance for its current project info."""
    url = f"http://127.0.0.1:{port}/mcp"
    try:
        response = await _post_mcp(
            url, "tools/call",
            {"name": "get_project_info", "arguments": {}},
            timeout=5.0,
        )
        if "result" in response:
            content = response["result"].get("content", [])
            for c in content:
                if c.get("type") == "text":
                    return json.loads(c["text"])
    except Exception as e:
        logger.debug("Failed to query project info on port %s: %s", port, e)
    return None


async def _handle_list_instances() -> list[types.TextContent]:
    """List all discovered Metashape instances with live project info."""
    import asyncio

    instances = discover_instances(check_alive=True)

    # Query all instances concurrently for live project info
    async def _enrich(inst):
        inst["active"] = inst.get("port") == _active_port
        info = await _query_project_info(inst["port"])
        if info:
            inst["project_path"] = info.get("path", "")
            inst["chunks"] = info.get("chunks", 0)
            inst["active_chunk"] = info.get("active_chunk")

    await asyncio.gather(*[_enrich(inst) for inst in instances])
    result = {
        "instances": instances,
        "active_port": _active_port,
        "total": len(instances),
    }
    return [types.TextContent(type="text", text=json.dumps(result, indent=2))]


async def _handle_switch_instance(port: int) -> list[types.TextContent]:
    """Switch to a different Metashape instance."""
    global _active_url, _active_port, _cached_tools

    url = f"http://127.0.0.1:{port}/mcp"

    # Verify the instance is alive by fetching its tools
    tools = await _fetch_tools(url)
    if not tools:
        return [types.TextContent(
            type="text",
            text=json.dumps({
                "error": f"Cannot connect to Metashape instance on port {port}. "
                         f"Check that Metashape is running and the MCP server is started.",
            }, indent=2),
        )]

    _active_url = url
    _active_port = port
    _cached_tools = tools

    # Fetch live project info
    info = await _query_project_info(port)
    project = info.get("path", "") if info else ""

    result = {
        "status": "connected",
        "port": port,
        "project": project,
        "tools_available": len(tools),
    }
    return [types.TextContent(type="text", text=json.dumps(result, indent=2))]


# ── MCP Server setup ─────────────────────────────────────────────

server = Server("Metashape-Multiplexer")


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """Return combined list of own tools + remote Metashape tools."""
    global _cached_tools

    if _active_url:
        try:
            _cached_tools = await _fetch_tools(_active_url)
        except Exception:
            pass

    remote_tools = []
    for t in _cached_tools:
        try:
            remote_tools.append(types.Tool(**t))
        except Exception:
            pass

    return list(_OWN_TOOLS) + remote_tools


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent]:
    """Handle tool calls — own tools locally, everything else forwarded."""

    arguments = arguments or {}

    # ── Our own tools ─────────────────────────────────────────
    if name == "list_instances":
        return await _handle_list_instances()

    if name == "switch_instance":
        port = arguments.get("port")
        if port is None:
            raise ValueError(
                "'port' argument is required. Use list_instances to see available ports."
            )
        return await _handle_switch_instance(int(port))

    # ── Forward to active Metashape instance ──────────────────
    if not _active_url:
        raise RuntimeError(
            "No active Metashape instance. "
            "Use list_instances to see available instances, "
            "then switch_instance to connect."
        )

    try:
        response = await _forward_tool_call(_active_url, name, arguments)
    except httpx.ConnectError:
        raise RuntimeError(
            f"Connection lost to Metashape on port {_active_port}. "
            f"The instance may be restarting after a transport error. "
            f"Use list_instances to check status, then switch_instance to reconnect."
        )
    except (httpx.ReadTimeout, httpx.WriteTimeout, httpx.PoolTimeout):
        raise RuntimeError(
            f"Timeout waiting for Metashape on port {_active_port}. "
            f"The operation may still be running in Metashape. "
            f"Use get_processing_status to check, or list_instances to verify "
            f"the instance is alive."
        )
    except (httpx.ReadError, httpx.RemoteProtocolError) as e:
        raise RuntimeError(
            f"Connection to Metashape on port {_active_port} was interrupted: {e}. "
            f"The operation likely completed or is still running in Metashape. "
            f"Use get_processing_status to check progress, or list_instances "
            f"to verify the instance is alive and switch_instance to reconnect."
        )
    except Exception as e:
        raise RuntimeError(f"Error forwarding to Metashape: {e}")

    # Extract content from the JSON-RPC response, preserving all content types
    if "result" in response:
        result = response["result"]
        if isinstance(result, dict) and "content" in result:
            content_items = []
            for c in result["content"]:
                ctype = c.get("type")
                if ctype == "text":
                    content_items.append(
                        types.TextContent(type="text", text=c.get("text", ""))
                    )
                elif ctype == "image":
                    content_items.append(
                        types.ImageContent(
                            type="image",
                            data=c.get("data", ""),
                            mimeType=c.get("mimeType", "image/png"),
                        )
                    )
                elif ctype == "resource":
                    content_items.append(
                        types.EmbeddedResource(
                            type="resource",
                            resource=c.get("resource", {}),
                        )
                    )
            return content_items if content_items else [
                types.TextContent(type="text", text=json.dumps(result, indent=2))
            ]
        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]
    elif "error" in response:
        error = response["error"]
        msg = error.get("message", str(error)) if isinstance(error, dict) else str(error)
        raise RuntimeError(f"Metashape error: {msg}")

    return [types.TextContent(type="text", text=json.dumps(response, indent=2))]


# ── Entry point ───────────────────────────────────────────────────

async def _run():
    """Start the multiplexer as a stdio MCP server."""
    global _active_url, _active_port, _cached_tools

    # Auto-connect to first available instance
    instances = discover_instances(check_alive=True)
    if instances:
        first = instances[0]
        _active_port = first["port"]
        _active_url = f"http://127.0.0.1:{_active_port}/mcp"
        _cached_tools = await _fetch_tools(_active_url)

    async with stdio_server() as (read_stream, write_stream):
        init_options = server.create_initialization_options()
        await server.run(read_stream, write_stream, init_options)


def main():
    """Entry point for the multiplexer proxy."""
    import asyncio
    asyncio.run(_run())


if __name__ == "__main__":
    main()
