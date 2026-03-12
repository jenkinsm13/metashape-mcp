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

# configuration file where the chosen port is stored for future sessions
_PORT_CONFIG = os.path.expanduser("~/.metashape_mcp_port")

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


def _read_saved_port(default: int = 8765) -> int:
    try:
        with open(_PORT_CONFIG, "r") as f:
            return int(f.read().strip())
    except Exception:
        return default


def _save_port(port: int) -> None:
    try:
        with open(_PORT_CONFIG, "w") as f:
            f.write(str(port))
    except Exception:
        pass


def _ask_for_port(initial: int) -> int:
    """Show a simple dialog and return the selected port.

    Falls back to console input if no Qt bindings are available.
    """
    port = initial
    # try Qt first (Metashape provides PySide2/PyQt5 in its bundled Python)
    try:
        from PySide2 import QtWidgets
    except ImportError:
        try:
            from PyQt5 import QtWidgets
        except ImportError:
            QtWidgets = None

    if QtWidgets:
        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        dlg = QtWidgets.QInputDialog()
        dlg.setWindowTitle("Metashape MCP Port")
        dlg.setLabelText("Enter TCP port for MCP server:")
        dlg.setInputMode(QtWidgets.QInputDialog.IntInput)
        dlg.setIntMinimum(1)
        dlg.setIntMaximum(65535)
        dlg.setIntValue(initial)
        if dlg.exec_() == QtWidgets.QDialog.Accepted:
            port = dlg.intValue()
    else:
        try:
            text = input(f"MCP port [{initial}]: ")
            if text.strip():
                port = int(text.strip())
        except Exception:
            pass
    return port



print("=" * 60)
print("  Starting Metashape MCP Server...")
print("=" * 60)

# load previously saved port and prompt user
default_port = _read_saved_port()
chosen = _ask_for_port(default_port)
if chosen != default_port:
    _save_port(chosen)

start_background(port=chosen)

print("")
print(f"  MCP server is running on http://127.0.0.1:{chosen}/mcp")
print("  Connect your AI assistant (Claude Desktop, Claude Code)")
print("  The Metashape UI is NOT blocked — you can still use it.")
print("  Watch this console for progress updates on MCP operations.")
print("=" * 60)
