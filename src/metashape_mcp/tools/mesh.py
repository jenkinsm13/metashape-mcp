"""Mesh generation and editing tools."""

from mcp.server.fastmcp import Context

from metashape_mcp.utils.bridge import get_chunk, require_model, require_tie_points
from metashape_mcp.utils.enums import resolve_enum
from metashape_mcp.utils.progress import (
    make_progress_callback,
    make_tracking_callback,
    run_in_thread,
)

import Metashape


def register(mcp) -> None:
    """Register mesh tools."""

    @mcp.tool()
    async def build_model(
        surface_type: str = "arbitrary",
        face_count: str = "high",
        source_data: str = "depth_maps",
        interpolation: str = "enabled",
        face_count_custom: int = 200000,
        vertex_colors: bool = True,
        keep_depth: bool = True,
        ctx: Context = None,
    ) -> dict:
        """Build a 3D mesh from depth maps or point cloud.

        Args:
            surface_type: "arbitrary" (3D objects) or "height_field" (terrain).
            face_count: Target: "low", "medium", "high", or "custom".
            source_data: Source: "depth_maps", "point_cloud", "tie_points".
            interpolation: "disabled", "enabled", or "extrapolated".
            face_count_custom: Custom face count when face_count="custom".
            vertex_colors: Calculate vertex colors.
            keep_depth: Keep depth maps after building.

        Returns:
            Model statistics including face and vertex counts.
        """
        chunk = get_chunk()
        require_tie_points(chunk)

        stype = resolve_enum("surface_type", surface_type)
        fcount = resolve_enum("face_count", face_count)
        src = resolve_enum("data_source", source_data)
        interp = resolve_enum("interpolation", interpolation)

        cb = make_progress_callback(ctx, "Building model") if ctx else make_tracking_callback("Building model")

        await run_in_thread(
            chunk.buildModel,
            surface_type=stype,
            face_count=fcount,
            face_count_custom=face_count_custom,
            source_data=src,
            interpolation=interp,
            vertex_colors=vertex_colors,
            keep_depth=keep_depth,
            progress=cb,
        )

        model = chunk.model
        faces = len(model.faces) if model else 0
        vertices = len(model.vertices) if model else 0
        return {
            "status": "model_built",
            "faces": faces,
            "vertices": vertices,
        }

    @mcp.tool()
    async def decimate_model(
        face_count: int = 200000,
        ctx: Context = None,
    ) -> dict:
        """Reduce mesh complexity by decimating to a target face count.

        Args:
            face_count: Target number of faces.

        Returns:
            Face count before and after decimation.
        """
        chunk = get_chunk()
        require_model(chunk)

        before = len(chunk.model.faces)
        cb = make_progress_callback(ctx, "Decimating model") if ctx else make_tracking_callback("Decimating model")

        await run_in_thread(chunk.decimateModel, face_count=face_count, progress=cb)

        after = len(chunk.model.faces)
        return {"before": before, "after": after}

    @mcp.tool()
    async def smooth_model(
        strength: float = 3.0,
        preserve_edges: bool = False,
        fix_borders: bool = True,
        ctx: Context = None,
    ) -> dict:
        """Smooth the mesh using Laplacian smoothing.

        Args:
            strength: Smoothing strength (higher = smoother).
            preserve_edges: Preserve sharp edges during smoothing.
            fix_borders: Keep border vertices fixed.

        Returns:
            Confirmation of smoothing.
        """
        chunk = get_chunk()
        require_model(chunk)

        cb = make_progress_callback(ctx, "Smoothing model") if ctx else make_tracking_callback("Smoothing model")

        await run_in_thread(
            chunk.smoothModel,
            strength=strength,
            preserve_edges=preserve_edges,
            fix_borders=fix_borders,
            progress=cb,
        )

        return {"status": "model_smoothed", "strength": strength}

    @mcp.tool()
    async def clean_model(
        criterion: str = "component_size",
        level: int = 0,
        ctx: Context = None,
    ) -> dict:
        """Remove model artifacts based on filtering criteria.

        Args:
            criterion: Filter by "component_size" or other Model.Criterion.
            level: Filtering threshold in percent (0-100).

        Returns:
            Face count before and after cleaning.
        """
        chunk = get_chunk()
        require_model(chunk)

        crit_map = {
            "component_size": Metashape.Model.ComponentSize,
        }
        crit = crit_map.get(criterion.lower(), Metashape.Model.ComponentSize)

        before = len(chunk.model.faces)
        cb = make_progress_callback(ctx, "Cleaning model") if ctx else make_tracking_callback("Cleaning model")

        await run_in_thread(chunk.cleanModel, criterion=crit, level=level, progress=cb)

        after = len(chunk.model.faces)
        return {"before": before, "after": after, "removed": before - after}

    @mcp.tool()
    async def close_holes(
        level: int = 100,
        ctx: Context = None,
    ) -> dict:
        """Close holes in the 3D mesh.

        Args:
            level: Maximum hole size to close (percentage, 0-100).
                   Higher values close larger holes.

        Returns:
            Face count before and after.
        """
        chunk = get_chunk()
        require_model(chunk)

        before = len(chunk.model.faces)
        cb = make_progress_callback(ctx, "Closing holes") if ctx else make_tracking_callback("Closing holes")

        await run_in_thread(chunk.model.closeHoles, level=level, progress=cb)

        after = len(chunk.model.faces)
        return {"before": before, "after": after, "added": after - before}

    @mcp.tool()
    async def refine_model(
        downscale: int = 4,
        iterations: int = 10,
        smoothness: float = 0.5,
        ctx: Context = None,
    ) -> dict:
        """Refine mesh geometry using multi-view stereo optimization.

        Args:
            downscale: Quality (1=Ultra, 2=High, 4=Medium, 8=Low, 16=Lowest).
            iterations: Number of refinement iterations.
            smoothness: Smoothing strength (0.0-1.0).

        Returns:
            Model statistics after refinement.
        """
        chunk = get_chunk()
        require_model(chunk)

        cb = make_progress_callback(ctx, "Refining model") if ctx else make_tracking_callback("Refining model")

        await run_in_thread(
            chunk.refineModel,
            downscale=downscale,
            iterations=iterations,
            smoothness=smoothness,
            progress=cb,
        )

        model = chunk.model
        return {
            "status": "model_refined",
            "faces": len(model.faces),
            "vertices": len(model.vertices),
        }

    @mcp.tool()
    async def clear_model() -> dict:
        """Remove the 3D model from the active chunk to free memory.

        Returns:
            Status indicating whether the model was cleared or absent.
        """
        chunk = get_chunk()
        if chunk.model is None:
            return {"status": "no_model"}
        chunk.remove(chunk.model)
        return {"status": "model_cleared"}

    @mcp.tool()
    async def get_model_stats() -> dict:
        """Return detailed statistics about the current 3D model.

        Returns:
            Dictionary with face/vertex counts, UV and texture info,
            and vertex color status.
        """
        chunk = get_chunk()
        require_model(chunk)

        model = chunk.model
        stats = {
            "faces": len(model.faces),
            "vertices": len(model.vertices),
            "has_uv": model.tex_vertices is not None and len(model.tex_vertices) > 0,
            "texture_count": len(model.textures) if model.textures else 0,
            "has_vertex_colors": model.has_vertex_colors if hasattr(model, 'has_vertex_colors') else False,
        }

        # Try to get texture dimensions
        try:
            if model.textures:
                tex = model.textures[0]
                stats["texture_width"] = tex.width
                stats["texture_height"] = tex.height
        except (AttributeError, IndexError):
            pass

        return stats
