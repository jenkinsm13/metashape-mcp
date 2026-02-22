"""Project management tools: open, save, create projects and manage chunks."""

import os

import Metashape

from metashape_mcp.utils.bridge import auto_save, get_chunk, get_document
from metashape_mcp.utils.progress import get_operation_state, request_cancel


def register(mcp) -> None:
    """Register project management tools."""

    @mcp.tool()
    def open_project(path: str, read_only: bool = False) -> dict:
        """Open a Metashape project file (.psx/.psz).

        Args:
            path: Absolute path to the project file.
            read_only: Open in read-only mode.

        Returns:
            Project info including path, chunk count, and read-only status.
        """
        if not os.path.exists(path):
            raise FileNotFoundError(f"Project file not found: {path}")

        doc = Metashape.app.document
        doc.open(path, read_only=read_only)
        return {
            "path": doc.path,
            "chunks": len(doc.chunks),
            "read_only": doc.read_only,
            "active_chunk": doc.chunk.label if doc.chunk else None,
        }

    @mcp.tool()
    def save_project(path: str | None = None) -> dict:
        """Save the current project.

        Args:
            path: Optional new path. If omitted, saves to the current location.

        Returns:
            Confirmation with the saved path.
        """
        doc = get_document()
        if path:
            doc.save(path)
        else:
            doc.save()
        return {"saved": doc.path}

    @mcp.tool()
    def create_project(path: str) -> dict:
        """Create a new empty Metashape project.

        Args:
            path: Path for the new project file (.psx).

        Returns:
            Project info with path and initial chunk.
        """
        doc = Metashape.app.document
        doc.clear()
        chunk = doc.addChunk()
        chunk.label = "Chunk 1"
        doc.save(path)
        return {
            "path": doc.path,
            "chunks": len(doc.chunks),
            "active_chunk": chunk.label,
        }

    @mcp.tool()
    def add_chunk(label: str | None = None) -> dict:
        """Add a new chunk to the project.

        Args:
            label: Optional label for the new chunk.

        Returns:
            Info about the created chunk.
        """
        doc = get_document()
        chunk = doc.addChunk()
        if label:
            chunk.label = label
        return {
            "label": chunk.label,
            "key": chunk.key,
            "total_chunks": len(doc.chunks),
        }

    @mcp.tool()
    def set_active_chunk(label_or_index: str) -> dict:
        """Switch the active chunk by label or index.

        Args:
            label_or_index: Chunk label (string) or index (number as string).

        Returns:
            Info about the newly active chunk.
        """
        doc = get_document()

        # Try as integer index first
        try:
            idx = int(label_or_index)
            if 0 <= idx < len(doc.chunks):
                doc.chunk = doc.chunks[idx]
                return {"active_chunk": doc.chunk.label, "index": idx}
            raise RuntimeError(
                f"Index {idx} out of range (0-{len(doc.chunks) - 1})."
            )
        except ValueError:
            pass

        # Try as label
        for c in doc.chunks:
            if c.label == label_or_index:
                doc.chunk = c
                return {"active_chunk": c.label, "index": doc.chunks.index(c)}

        available = [c.label for c in doc.chunks]
        raise RuntimeError(
            f"No chunk '{label_or_index}'. Available: {available}"
        )

    @mcp.tool()
    def list_chunks() -> list[dict]:
        """List all chunks in the project with summary info.

        Returns:
            List of chunk summaries including cameras, tie points, and
            processing state for each chunk.
        """
        doc = get_document()
        result = []
        for i, c in enumerate(doc.chunks):
            info = {
                "index": i,
                "label": c.label,
                "enabled": c.enabled,
                "cameras": len(c.cameras),
                "markers": len(c.markers),
                "has_tie_points": c.tie_points is not None,
                "has_point_cloud": c.point_cloud is not None,
                "has_model": c.model is not None,
                "has_elevation": c.elevation is not None,
                "has_orthomosaic": c.orthomosaic is not None,
                "has_tiled_model": c.tiled_model is not None,
                "is_active": c == doc.chunk,
            }
            if c.crs:
                info["crs"] = c.crs.name
            result.append(info)
        return result

    @mcp.tool()
    def set_gpu_config(
        cpu_enable: bool = False,
        gpu_mask: int | None = None,
    ) -> dict:
        """Configure GPU/CPU usage for processing.

        IMPORTANT: Enable CPU only during alignment (match_photos,
        align_cameras) where it speeds things up. For ALL other steps
        (depth maps, point cloud, meshing, texturing), disable CPU —
        it slows things down when a GPU is active.

        Args:
            cpu_enable: Use CPU alongside GPU. True only for alignment.
            gpu_mask: Bitmask of GPU devices (1=device 0, 3=devices 0+1, etc.).
                      If not provided, keeps current mask.

        Returns:
            Current GPU configuration.
        """
        app = Metashape.app
        app.cpu_enable = cpu_enable
        if gpu_mask is not None:
            app.gpu_mask = gpu_mask

        devices = app.enumGPUDevices()
        return {
            "cpu_enable": app.cpu_enable,
            "gpu_mask": app.gpu_mask,
            "devices": [str(d) for d in devices],
        }

    @mcp.tool()
    def duplicate_chunk(label: str | None = None) -> dict:
        """Duplicate the active chunk.

        Creates an exact copy of the current chunk including all data.
        Useful for testing different processing parameters without
        losing work.

        Args:
            label: Label for the new chunk. Defaults to original + " copy".

        Returns:
            Info about the duplicated chunk.
        """
        doc = get_document()
        chunk = doc.chunk
        if chunk is None:
            raise RuntimeError("No active chunk to duplicate.")

        new_chunk = chunk.copy()
        if label:
            new_chunk.label = label

        return {
            "label": new_chunk.label,
            "key": new_chunk.key,
            "total_chunks": len(doc.chunks),
        }

    @mcp.tool()
    def merge_chunks(
        chunk_labels: list[str] | None = None,
        merge_markers: bool = True,
        merge_tie_points: bool = True,
        merge_depth_maps: bool = False,
        merge_point_clouds: bool = True,
        merge_models: bool = True,
    ) -> dict:
        """Merge multiple chunks into the active chunk.

        Args:
            chunk_labels: Labels of chunks to merge. If omitted, merges all.
            merge_markers: Include markers in merge.
            merge_tie_points: Include tie points in merge.
            merge_depth_maps: Include depth maps in merge.
            merge_point_clouds: Include point clouds in merge.
            merge_models: Include models in merge.

        Returns:
            Merge results.
        """
        doc = get_document()
        chunks = []

        if chunk_labels:
            for lbl in chunk_labels:
                found = False
                for c in doc.chunks:
                    if c.label == lbl:
                        chunks.append(c)
                        found = True
                        break
                if not found:
                    raise RuntimeError(f"Chunk '{lbl}' not found.")
        else:
            chunks = list(doc.chunks)

        if len(chunks) < 2:
            raise RuntimeError("Need at least 2 chunks to merge.")

        doc.mergeChunks(
            chunks=chunks,
            merge_markers=merge_markers,
            merge_tiepoints=merge_tie_points,
            merge_depth_maps=merge_depth_maps,
            merge_point_clouds=merge_point_clouds,
            merge_models=merge_models,
        )

        auto_save()
        return {
            "status": "chunks_merged",
            "chunks_merged": len(chunks),
            "total_chunks": len(doc.chunks),
        }

    @mcp.tool()
    def align_chunks(method: str = "tie_points") -> dict:
        """Align chunks relative to each other.

        Args:
            method: Alignment method - "tie_points" (0), "markers" (1),
                    or "cameras" (2).

        Returns:
            Alignment status and chunk count.
        """
        doc = get_document()
        if len(doc.chunks) < 2:
            raise RuntimeError("Need at least 2 chunks to align.")

        method_map = {
            "tie_points": 0,
            "markers": 1,
            "cameras": 2,
        }
        m = method_map.get(method.lower())
        if m is None:
            raise ValueError(
                f"Unknown alignment method: {method}. "
                f"Use: tie_points, markers, cameras."
            )

        doc.alignChunks(chunks=list(doc.chunks), method=m)
        auto_save()
        return {"status": "chunks_aligned", "chunks": len(doc.chunks)}

    @mcp.tool()
    def get_processing_status() -> dict:
        """Check the current processing status of the Metashape server.

        Returns the active operation name, progress percentage, and
        elapsed time. Use this to monitor long-running operations like
        matching, alignment, depth maps, mesh building, etc.

        Returns:
            Current operation state including progress and elapsed time.
        """
        state = get_operation_state()
        if state["active"]:
            return {
                "status": "processing",
                "operation": state["operation"],
                "progress": f"{state['progress']:.1%}",
                "progress_raw": state["progress"],
                "elapsed_seconds": state.get("elapsed_seconds", 0),
            }
        return {"status": "idle"}

    @mcp.tool()
    def cancel_processing() -> dict:
        """Cancel the currently running Metashape operation.

        Signals the active processing operation to abort at its next
        progress callback. The operation will raise an error and stop.

        Returns:
            Confirmation that cancellation was requested.
        """
        request_cancel()
        return {"status": "cancel_requested"}
