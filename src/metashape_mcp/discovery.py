"""Instance discovery for Metashape MCP multi-instance support.

Each Metashape instance writes a JSON discovery file when its MCP server
starts. The multiplexer reads these files to find running instances.

Discovery directory: %LOCALAPPDATA%/metashape-mcp/instances/
  (falls back to ~/.metashape-mcp/instances/ on non-Windows)

Each file is named {port}.json and contains:
  port, pid, project_path, metashape_version, started_at
"""

import atexit
import json
import os
import socket
import time
from pathlib import Path

# Discovery directory
_LOCALAPPDATA = os.environ.get("LOCALAPPDATA", "")
if _LOCALAPPDATA:
    DISCOVERY_DIR = Path(_LOCALAPPDATA) / "metashape-mcp" / "instances"
else:
    DISCOVERY_DIR = Path.home() / ".metashape-mcp" / "instances"

# Port range for auto-assignment (20 ports should be plenty)
PORT_RANGE_START = 8765
PORT_RANGE_END = 8785


def _ensure_discovery_dir() -> Path:
    """Create discovery directory if it doesn't exist."""
    DISCOVERY_DIR.mkdir(parents=True, exist_ok=True)
    return DISCOVERY_DIR


def find_free_port(start: int = PORT_RANGE_START, end: int = PORT_RANGE_END) -> int:
    """Find the first available port in the range.

    Tries to bind each port in sequence. Returns the first one that's free.
    Raises RuntimeError if all ports in the range are occupied.
    """
    for port in range(start, end):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", port))
                return port
        except OSError:
            continue
    raise RuntimeError(
        f"No free port in range {start}-{end}. "
        f"Close some Metashape instances or increase the range."
    )


def register_instance(
    port: int,
    project_path: str = "",
    metashape_version: str = "",
) -> Path:
    """Write a discovery file for this Metashape instance.

    Also registers an atexit handler to clean up on exit.
    Returns the path to the discovery file.
    """
    discovery_dir = _ensure_discovery_dir()
    info = {
        "port": port,
        "pid": os.getpid(),
        "project_path": project_path,
        "metashape_version": metashape_version,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    path = discovery_dir / f"{port}.json"
    path.write_text(json.dumps(info, indent=2))

    # Clean up on exit
    atexit.register(lambda p=path: p.unlink(missing_ok=True))

    return path


def unregister_instance(port: int) -> None:
    """Remove the discovery file for a specific port."""
    path = _ensure_discovery_dir() / f"{port}.json"
    path.unlink(missing_ok=True)


def _is_port_responding(port: int, host: str = "127.0.0.1", timeout: float = 1.0) -> bool:
    """Check if a port is accepting TCP connections."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            s.connect((host, port))
            return True
    except (OSError, ConnectionRefusedError):
        return False


def discover_instances(check_alive: bool = True) -> list[dict]:
    """Find all registered Metashape MCP instances.

    Args:
        check_alive: If True, verify each instance is still responding
                     and remove stale discovery files.

    Returns:
        List of instance info dicts, sorted by port number.
    """
    discovery_dir = _ensure_discovery_dir()
    instances = []

    for f in sorted(discovery_dir.glob("*.json")):
        try:
            data = json.loads(f.read_text())
        except (json.JSONDecodeError, OSError):
            f.unlink(missing_ok=True)
            continue

        port = data.get("port")
        if port is None:
            f.unlink(missing_ok=True)
            continue

        if check_alive:
            if not _is_port_responding(port):
                f.unlink(missing_ok=True)
                continue

        instances.append(data)

    return instances
