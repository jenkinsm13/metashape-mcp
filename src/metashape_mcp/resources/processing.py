"""Processing status and statistics resources."""

from metashape_mcp.utils.bridge import get_chunk


def register(mcp) -> None:
    """Register processing resources."""

    @mcp.resource("metashape://chunk/{label}/tie_points")
    def chunk_tie_points(label: str) -> dict:
        """Tie point statistics for a chunk."""
        chunk = get_chunk(label=label)

        if chunk.tie_points is None:
            return {"status": "no_tie_points"}

        tp = chunk.tie_points
        points = tp.points if tp.points else []

        # Count valid (non-removed) points
        valid_points = sum(1 for p in points if p.valid)
        total_points = len(points)

        result = {
            "total_points": total_points,
            "valid_points": valid_points,
        }

        if tp.tracks:
            result["tracks"] = len(tp.tracks)
        if tp.projections:
            result["projections"] = len(tp.projections)

        return result

    @mcp.resource("metashape://chunk/{label}/point_cloud")
    def chunk_point_cloud(label: str) -> dict:
        """Point cloud statistics for a chunk."""
        chunk = get_chunk(label=label)

        if chunk.point_cloud is None:
            return {"status": "no_point_cloud"}

        pc = chunk.point_cloud
        points = pc.points if pc.points else []

        result = {
            "point_count": len(points),
            "has_colors": pc.has_colors if hasattr(pc, "has_colors") else None,
            "has_normals": pc.has_normals if hasattr(pc, "has_normals") else None,
        }

        return result

    @mcp.resource("metashape://chunk/{label}/model")
    def chunk_model(label: str) -> dict:
        """Model geometry statistics for a chunk."""
        chunk = get_chunk(label=label)

        if chunk.model is None:
            return {"status": "no_model"}

        model = chunk.model

        result = {
            "faces": len(model.faces) if model.faces else 0,
            "vertices": len(model.vertices) if model.vertices else 0,
            "has_uv": (
                model.tex_vertices is not None
                and len(model.tex_vertices) > 0
            ),
            "texture_count": len(model.textures) if model.textures else 0,
        }

        return result

    @mcp.resource("metashape://chunk/{label}/dem")
    def chunk_dem(label: str) -> dict:
        """DEM extent and resolution for a chunk."""
        chunk = get_chunk(label=label)

        if chunk.elevation is None:
            return {"status": "no_dem"}

        dem = chunk.elevation
        result = {
            "resolution": dem.resolution,
        }

        if dem.crs:
            result["crs"] = dem.crs.name

        return result

    @mcp.resource("metashape://chunk/{label}/orthomosaic")
    def chunk_orthomosaic(label: str) -> dict:
        """Orthomosaic information for a chunk."""
        chunk = get_chunk(label=label)

        if chunk.orthomosaic is None:
            return {"status": "no_orthomosaic"}

        ortho = chunk.orthomosaic
        result = {
            "resolution": ortho.resolution,
        }

        if ortho.crs:
            result["crs"] = ortho.crs.name

        return result
