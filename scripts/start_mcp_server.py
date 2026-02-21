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

# ──────────────────────────────────────────────────────────────────────
# EDIT THIS PATH to point to your local clone of the metashape-mcp repo
# ──────────────────────────────────────────────────────────────────────
METASHAPE_MCP_SRC = r"C:\path\to\metashape-mcp\src"

# Add the source directory to Python path
if METASHAPE_MCP_SRC not in sys.path:
    sys.path.insert(0, METASHAPE_MCP_SRC)


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

from metashape_mcp.server import start_background

print("=" * 60)
print("  Starting Metashape MCP Server...")
print("=" * 60)

start_background()

print("")
print("  MCP server is running on http://127.0.0.1:8765/mcp")
print("  Connect your AI assistant (Claude Desktop, Claude Code)")
print("  The Metashape UI is NOT blocked — you can still use it.")
print("  Watch this console for progress updates on MCP operations.")
print("=" * 60)
