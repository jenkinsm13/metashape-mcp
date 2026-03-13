"""Metashape startup script for the MCP server.

Copy this file to your Metashape scripts folder:
  Windows: C:\\Users\\<user>\\AppData\\Local\\Agisoft\\Metashape Pro\\scripts\\
  macOS:   ~/Library/Application Support/Agisoft/Metashape Pro/scripts/
  Linux:   ~/.local/share/Agisoft/Metashape Pro/scripts/

Or run it manually via Tools > Run Script in Metashape.

After starting, watch the Console panel (View > Console) for status messages.
The MCP server runs in the background — the Metashape UI remains fully usable.
"""

import sys
import os
from pathlib import Path

# ──────────────────────────────────────────────────────────────────────
# EDIT THIS PATH to point to your local clone of the metashape-mcp repo
# ──────────────────────────────────────────────────────────────────────
METASHAPE_MCP_SRC = r"X:\tools\mcps\metashape-mcp\src"

# Add the source directory to Python path
if METASHAPE_MCP_SRC not in sys.path:
    sys.path.insert(0, METASHAPE_MCP_SRC)

# Port settings persistence
_PORT_FILE = Path.home() / ".metashape_mcp_port"
_DEFAULT_PORT = None  # None = auto-assign from range


def _load_saved_port() -> int | None:
    """Load previously saved port preference."""
    try:
        return int(_PORT_FILE.read_text().strip())
    except (FileNotFoundError, ValueError):
        return None


def _save_port(port: int) -> None:
    """Save port preference for next session."""
    _PORT_FILE.write_text(str(port))


def _ask_port_dialog(default: int | None) -> int | None:
    """Show a Qt dialog for port selection. Returns port or None for auto."""
    try:
        # Try PySide2 first (Metashape bundles this)
        try:
            from PySide2.QtWidgets import QInputDialog
        except ImportError:
            from PyQt5.QtWidgets import QInputDialog

        hint = default if default else 8765
        port, ok = QInputDialog.getInt(
            None,
            "Metashape MCP Server",
            "TCP port (0 = auto-assign from 8765-8784):",
            hint, 0, 65535,
        )
        if not ok:
            return default  # cancelled — use previous/default
        return None if port == 0 else port

    except Exception:
        # No Qt available — fall back to saved/default
        return default


# ── Auto-install missing dependencies ────────────────────────────────
def _ensure_dependencies():
    """Install mcp and fastmcp into Metashape's Python if missing."""
    deps = [("mcp", "mcp[cli]>=1.2.0"), ("fastmcp", "fastmcp>=2.0.0")]
    missing = []
    for mod, spec in deps:
        try:
            __import__(mod)
        except ImportError:
            missing.append(spec)

    if not missing:
        return

    print(f"  Installing missing dependencies: {', '.join(missing)}")
    import subprocess
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install"] + missing
        )
        print("  Dependencies installed successfully!")
    except Exception as e:
        print(f"  Auto-install failed: {e}")
        print("  Please install manually — see README for instructions.")
        raise


_ensure_dependencies()
# ─────────────────────────────────────────────────────────────────────

from metashape_mcp.server import start_background, get_port

print("=" * 60)
print("  Starting Metashape MCP Server...")
print("=" * 60)

# Determine port: dialog > saved > auto
saved_port = _load_saved_port()
chosen_port = _ask_port_dialog(saved_port)

start_background(port=chosen_port)

_port = get_port()

# Save the chosen port for next session
_save_port(_port)

port_source = "auto-assigned"
if os.environ.get("METASHAPE_MCP_PORT"):
    port_source = "set via METASHAPE_MCP_PORT"
elif chosen_port is not None:
    port_source = "user-selected (saved for next session)"

print("")
print(f"  MCP server is running on http://127.0.0.1:{_port}/mcp")
print(f"  Port {_port} was {port_source}")
print(f"  Port preference saved to {_PORT_FILE}")
print("  Connect your AI assistant (Claude Desktop, Claude Code)")
print("  The Metashape UI is NOT blocked — you can still use it.")
print("  Multiple Metashape instances are supported — each gets its own port.")
print("  Watch this console for progress updates on MCP operations.")
print("=" * 60)
