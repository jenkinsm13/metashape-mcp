"""Headless Metashape MCP server — no GUI required.

Runs Metashape in headless/offscreen mode with the MCP server in the
foreground. Ideal for remote servers, VMs, CI pipelines, and automated
batch processing where no display is available.

Usage:
  # Windows:
  "C:\\Program Files\\Agisoft\\Metashape Pro\\metashape.exe" -platform offscreen -r start_mcp_headless.py

  # Linux:
  metashape -platform offscreen -r start_mcp_headless.py

  # macOS:
  /Applications/MetashapePro.app/Contents/MacOS/MetashapePro -platform offscreen -r start_mcp_headless.py

The server runs in the foreground and blocks — press Ctrl+C to stop.
Viewport/screenshot tools are unavailable in headless mode; all
processing, export, import, and scripting tools work normally.
"""

import sys
import os

# ──────────────────────────────────────────────────────────────────────
# EDIT THIS PATH to point to your local clone of the metashape-mcp repo
# ──────────────────────────────────────────────────────────────────────
METASHAPE_MCP_SRC = r"C:\path\to\metashape-mcp\src"

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

import Metashape

print("=" * 60)
print("  Metashape MCP Server — HEADLESS MODE")
print(f"  Metashape {Metashape.app.version}")
print(f"  Python {sys.version.split()[0]}")
print("=" * 60)
print("")
print("  No GUI — all processing tools available")
print("  Viewport/screenshot tools are unavailable")
print("  Server will listen on http://127.0.0.1:8765/mcp")
print("  Press Ctrl+C to stop")
print("=" * 60)

from metashape_mcp.server import main
main()
