"""Survey product tools: DEM, orthomosaic, tiled model, contours, panorama."""

from metashape_mcp.utils.bridge import (
    get_chunk,
    require_elevation,
    require_model,
    require_point_cloud,
    require_tie_points,
)
from metashape_mcp.utils.enums import resolve_enum
from metashape_mcp.utils.progress import (
    make_tracking_callback,
)


def register(mcp) -> None:
    """Register survey product tools."""

    @mcp.tool()
    def build_dem(
        source_data: str = "point_cloud",
        interpolation: str = "enabled",
        resolution: float = 0,
        classes: list[int] | None = None,
    ) -> dict:
        """Build a Digital Elevation Model (DEM).

        Args:
            source_data: "point_cloud" or "tie_points".
            interpolation: "disabled", "enabled", or "extrapolated".
            resolution: Output resolution in meters (0 = auto).
            classes: Point classes to use (e.g., [2] for ground only).

        Returns:
            DEM info including resolution and extent.
        """
        chunk = get_chunk()

        src = resolve_enum("data_source", source_data)
        interp = resolve_enum("interpolation", interpolation)
        cb = make_tracking_callback("Building DEM")

        kwargs = {
            "source_data": src,
            "interpolation": interp,
            "resolution": resolution,
            "progress": cb,
        }
        if classes is not None:
            kwargs["classes"] = classes

        chunk.buildDem(**kwargs)

        dem = chunk.elevation
        result = {"status": "dem_built"}
        if dem:
            result["resolution"] = dem.resolution
        return result

    @mcp.tool()
    def build_orthomosaic(
        surface_data: str = "model",
        blending_mode: str = "mosaic",
        fill_holes: bool = True,
        ghosting_filter: bool = False,
        resolution: float = 0,
    ) -> dict:
        """Build an orthomosaic (georeferenced orthoimage).

        Requires a model or DEM for orthorectification.

        Args:
            surface_data: Ortho surface: "model", "elevation", "point_cloud".
            blending_mode: "mosaic", "average", "natural", "min", "max", "disabled".
            fill_holes: Fill holes in the orthomosaic.
            ghosting_filter: Filter ghosting from moving objects.
            resolution: Pixel size in meters (0 = auto).

        Returns:
            Orthomosaic info.
        """
        chunk = get_chunk()

        src = resolve_enum("data_source", surface_data)
        blend = resolve_enum("blending_mode", blending_mode)
        cb = make_tracking_callback("Building orthomosaic")

        chunk.buildOrthomosaic(
            surface_data=src,
            blending_mode=blend,
            fill_holes=fill_holes,
            ghosting_filter=ghosting_filter,
            resolution=resolution,
            progress=cb,
        )

        ortho = chunk.orthomosaic
        result = {"status": "orthomosaic_built"}
        if ortho:
            result["resolution"] = ortho.resolution
        return result

    @mcp.tool()
    def build_tiled_model(
        pixel_size: float = 0,
        tile_size: int = 256,
        face_count: int = 20000,
        source_data: str = "depth_maps",
    ) -> dict:
        """Build a hierarchical tiled model for web/3D visualization.

        Creates a LOD (Level of Detail) tiled model suitable for
        streaming viewers like Cesium.

        Args:
            pixel_size: Target resolution in meters (0 = auto).
            tile_size: Tile size in pixels.
            face_count: Faces per megapixel of texture.
            source_data: "depth_maps", "point_cloud", or "model".

        Returns:
            Tiled model info.
        """
        chunk = get_chunk()

        src = resolve_enum("data_source", source_data)
        cb = make_tracking_callback("Building tiled model")

        chunk.buildTiledModel(
            pixel_size=pixel_size,
            tile_size=tile_size,
            face_count=face_count,
            source_data=src,
            progress=cb,
        )

        return {"status": "tiled_model_built"}

    @mcp.tool()
    def build_contours(
        interval: float = 1.0,
        source_data: str = "elevation",
        min_value: float = -1e10,
        max_value: float = 1e10,
    ) -> dict:
        """Generate contour lines from the DEM.

        Args:
            interval: Contour interval in DEM units (meters).
            source_data: Usually "elevation".
            min_value: Minimum contour elevation.
            max_value: Maximum contour elevation.

        Returns:
            Contour generation results.
        """
        chunk = get_chunk()
        require_elevation(chunk)

        src = resolve_enum("data_source", source_data)
        cb = make_tracking_callback("Building contours")

        chunk.buildContours(
            source_data=src,
            interval=interval,
            min_value=min_value,
            max_value=max_value,
            progress=cb,
        )

        return {"status": "contours_built", "interval": interval}

    @mcp.tool()
    def build_panorama(
        blending_mode: str = "mosaic",
        ghosting_filter: bool = False,
        width: int = 0,
        height: int = 0,
    ) -> dict:
        """Generate spherical panoramas from camera stations.

        Args:
            blending_mode: "mosaic", "average", or "natural".
            ghosting_filter: Filter ghosting artifacts.
            width: Output width in pixels (0 = auto).
            height: Output height in pixels (0 = auto).

        Returns:
            Panorama generation results.
        """
        chunk = get_chunk()

        blend = resolve_enum("blending_mode", blending_mode)
        cb = make_tracking_callback("Building panorama")

        chunk.buildPanorama(
            blending_mode=blend,
            ghosting_filter=ghosting_filter,
            width=width,
            height=height,
            progress=cb,
        )

        return {"status": "panorama_built"}

    @mcp.tool()
    def clear_dem() -> dict:
        """Remove the DEM from the active chunk to free memory.

        Returns:
            Status indicating whether the DEM was cleared.
        """
        chunk = get_chunk()
        if chunk.elevation is None:
            return {"status": "no_dem"}
        chunk.remove(chunk.elevation)
        return {"status": "dem_cleared"}

    @mcp.tool()
    def clear_orthomosaic() -> dict:
        """Remove the orthomosaic from the active chunk to free memory.

        Returns:
            Status indicating whether the orthomosaic was cleared.
        """
        chunk = get_chunk()
        if chunk.orthomosaic is None:
            return {"status": "no_orthomosaic"}
        chunk.remove(chunk.orthomosaic)
        return {"status": "orthomosaic_cleared"}

    @mcp.tool()
    def clear_tiled_model() -> dict:
        """Remove the tiled model from the active chunk to free memory.

        Returns:
            Status indicating whether the tiled model was cleared.
        """
        chunk = get_chunk()
        if chunk.tiled_model is None:
            return {"status": "no_tiled_model"}
        chunk.remove(chunk.tiled_model)
        return {"status": "tiled_model_cleared"}
