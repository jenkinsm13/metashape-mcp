"""Safe access to the Metashape application, document, and active chunk.

Every tool should use these helpers instead of accessing Metashape globals
directly. They provide clear error messages when prerequisites are missing.
"""

from typing import Optional

import Metashape


def get_app() -> Metashape.Application:
    """Return the Metashape Application singleton."""
    return Metashape.app


def get_document() -> Metashape.Document:
    """Return the active document, raising if none is open."""
    doc = Metashape.app.document
    if doc is None or doc.path == "" and len(doc.chunks) == 0:
        raise RuntimeError(
            "No project is open. Use 'open_project' or 'create_project' first."
        )
    return doc


def get_chunk(label: Optional[str] = None, index: Optional[int] = None) -> Metashape.Chunk:
    """Return a chunk by label, index, or the active chunk.

    Priority: label > index > active chunk.
    """
    doc = get_document()

    if label is not None:
        for c in doc.chunks:
            if c.label == label:
                return c
        raise RuntimeError(
            f"No chunk with label '{label}'. "
            f"Available: {[c.label for c in doc.chunks]}"
        )

    if index is not None:
        if 0 <= index < len(doc.chunks):
            return doc.chunks[index]
        raise RuntimeError(
            f"Chunk index {index} out of range (0-{len(doc.chunks) - 1})."
        )

    chunk = doc.chunk
    if chunk is None:
        raise RuntimeError(
            "No active chunk. Add a chunk with 'add_chunk' or "
            "select one with 'set_active_chunk'."
        )
    return chunk


def require_tie_points(chunk: Metashape.Chunk) -> None:
    """Raise if the chunk has no tie points (alignment not done)."""
    if chunk.tie_points is None:
        raise RuntimeError(
            "No tie points found. Run 'match_photos' and 'align_cameras' first."
        )


def require_depth_maps(chunk: Metashape.Chunk) -> None:
    """Raise if the chunk has no depth maps."""
    if chunk.depth_maps is None:
        raise RuntimeError("No depth maps found. Run 'build_depth_maps' first.")


def require_point_cloud(chunk: Metashape.Chunk) -> None:
    """Raise if the chunk has no dense point cloud."""
    if chunk.point_cloud is None:
        raise RuntimeError("No point cloud found. Run 'build_point_cloud' first.")


def require_model(chunk: Metashape.Chunk) -> None:
    """Raise if the chunk has no 3D model."""
    if chunk.model is None:
        raise RuntimeError("No model found. Run 'build_model' first.")


def require_elevation(chunk: Metashape.Chunk) -> None:
    """Raise if the chunk has no DEM."""
    if chunk.elevation is None:
        raise RuntimeError("No DEM found. Run 'build_dem' first.")


def require_orthomosaic(chunk: Metashape.Chunk) -> None:
    """Raise if the chunk has no orthomosaic."""
    if chunk.orthomosaic is None:
        raise RuntimeError("No orthomosaic found. Run 'build_orthomosaic' first.")
