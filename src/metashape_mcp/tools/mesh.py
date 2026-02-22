"""Mesh generation and editing tools."""

from metashape_mcp.utils.bridge import get_chunk, require_model, require_tie_points
from metashape_mcp.utils.enums import resolve_enum
from metashape_mcp.utils.progress import make_tracking_callback

import Metashape


def register(mcp) -> None:
    """Register mesh tools."""

    @mcp.tool()
    def build_model(
        surface_type: str = "arbitrary",
        source_data: str = "depth_maps",
        interpolation: str = "enabled",
        vertex_colors: bool = True,
        keep_depth: bool = True,
    ) -> dict:
        """Build a 3D mesh from depth maps or point cloud.

        Always builds with unlimited face count (face_count_custom=0).

        Args:
            surface_type: "arbitrary" (3D objects) or "height_field" (terrain).
            source_data: Source: "depth_maps", "depth_maps_and_laser_scans", "point_cloud", "laser_scans", "tie_points".
            interpolation: "disabled", "enabled", or "extrapolated".
            vertex_colors: Calculate vertex colors.
            keep_depth: Keep depth maps after building.

        Returns:
            Model statistics including face and vertex counts.
        """
        chunk = get_chunk()
        require_tie_points(chunk)

        stype = resolve_enum("surface_type", surface_type)
        src = resolve_enum("data_source", source_data)
        interp = resolve_enum("interpolation", interpolation)

        cb = make_tracking_callback("Building model")

        chunk.buildModel(
            surface_type=stype,
            face_count=Metashape.CustomFaceCount,
            face_count_custom=0,
            source_data=src,
            interpolation=interp,
            vertex_colors=vertex_colors,
            keep_depth=keep_depth,
            trimming_radius=0,
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
    def decimate_model(
        face_count: int = 200000,
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
        cb = make_tracking_callback("Decimating model")

        chunk.decimateModel(face_count=face_count, progress=cb)

        after = len(chunk.model.faces)
        return {"before": before, "after": after}

    @mcp.tool()
    def smooth_model(
        strength: float = 3.0,
        preserve_edges: bool = False,
        fix_borders: bool = True,
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

        cb = make_tracking_callback("Smoothing model")

        chunk.smoothModel(
            strength=strength,
            preserve_edges=preserve_edges,
            fix_borders=fix_borders,
            progress=cb,
        )

        return {"status": "model_smoothed", "strength": strength}

    @mcp.tool()
    def clean_model(
        criterion: str = "component_size",
        level: int = 0,
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
        cb = make_tracking_callback("Cleaning model")

        chunk.cleanModel(criterion=crit, level=level, progress=cb)

        after = len(chunk.model.faces)
        return {"before": before, "after": after, "removed": before - after}

    @mcp.tool()
    def close_holes(
        level: int = 100,
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
        cb = make_tracking_callback("Closing holes")

        chunk.model.closeHoles(level=level, progress=cb)

        after = len(chunk.model.faces)
        return {"before": before, "after": after, "added": after - before}

    @mcp.tool()
    def refine_model(
        downscale: int = 4,
        iterations: int = 10,
        smoothness: float = 0.5,
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

        cb = make_tracking_callback("Refining model")

        chunk.refineModel(
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
    def clear_model() -> dict:
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
    def get_model_stats() -> dict:
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
