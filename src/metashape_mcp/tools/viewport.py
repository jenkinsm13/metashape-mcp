"""Viewport tools: screenshots, view control."""

import os
import tempfile

import Metashape

from metashape_mcp.utils.bridge import get_chunk, get_document


def register(mcp) -> None:
    """Register viewport tools."""

    @mcp.tool()
    def capture_viewport(
        path: str | None = None,
        width: int = 1920,
        height: int = 1080,
        hide_items: bool = False,
        transparent: bool = False,
    ) -> dict:
        """Capture a screenshot of the Metashape 3D viewport.

        Saves the current model/point cloud/tie point view to an image.
        Use this to visually inspect alignment, mesh, or texture results.

        Args:
            path: Output image path. If omitted, saves to a temp file.
            width: Image width in pixels.
            height: Image height in pixels.
            hide_items: Hide UI overlays (markers, cameras, etc).
            transparent: Use transparent background.

        Returns:
            Path to the saved screenshot.
        """
        if path is None:
            path = os.path.join(tempfile.gettempdir(), "metashape_viewport.png")

        image = Metashape.app.captureView(
            width=width,
            height=height,
            transparent=transparent,
            hide_items=hide_items,
        )
        image.save(path)

        size = os.path.getsize(path) if os.path.exists(path) else 0
        return {"path": path, "size_bytes": size, "width": width, "height": height}

    @mcp.tool()
    def get_console_output(last_n_lines: int = 50) -> dict:
        """Read the Metashape console pane output.

        Useful for checking processing messages, warnings, and errors
        that Metashape logs during operations.

        Args:
            last_n_lines: Number of lines from the end to return.

        Returns:
            Console output text.
        """
        try:
            contents = Metashape.app.console_pane.contents
            lines = contents.strip().split("\n")
            if last_n_lines > 0:
                lines = lines[-last_n_lines:]
            return {"output": "\n".join(lines), "total_lines": len(contents.strip().split("\n"))}
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def auto_save() -> dict:
        """Save the project to its current path.

        Call this between processing steps to preserve progress.
        Equivalent to Ctrl+S in the Metashape GUI.

        Returns:
            Confirmation with saved path.
        """
        doc = get_document()
        if not doc.path:
            return {"error": "Project has no save path. Use save_project(path=...) first."}
        doc.save()
        return {"saved": doc.path}
