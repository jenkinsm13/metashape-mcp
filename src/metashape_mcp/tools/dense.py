"""Dense reconstruction tools: depth maps, point cloud, filtering."""

import Metashape
from mcp.server.fastmcp import Context

from metashape_mcp.utils.bridge import (
    get_chunk,
    require_depth_maps,
    require_point_cloud,
    require_tie_points,
)
from metashape_mcp.utils.enums import resolve_enum
from metashape_mcp.utils.progress import (
    make_progress_callback,
    make_tracking_callback,
    run_in_thread,
)


def register(mcp) -> None:
    """Register dense reconstruction tools."""

    @mcp.tool()
    async def build_depth_maps(
        downscale: int = 4,
        filter_mode: str = "mild",
        max_neighbors: int = 16,
        reuse_depth: bool = False,
        ctx: Context = None,
    ) -> dict:
        """Generate depth maps for aligned cameras.

        Depth maps are the foundation for dense point cloud and mesh
        generation. Quality is controlled by downscale parameter.

        Args:
            downscale: Quality (1=Ultra, 2=High, 4=Medium, 8=Low, 16=Lowest).
            filter_mode: Depth filtering: "none", "mild", "moderate", "aggressive".
            max_neighbors: Maximum neighbor images for depth estimation.
            reuse_depth: Reuse existing depth maps if available.

        Returns:
            Depth map generation results.
        """
        chunk = get_chunk()
        require_tie_points(chunk)

        fmode = resolve_enum("filter_mode", filter_mode)
        cb = make_progress_callback(ctx, "Building depth maps") if ctx else make_tracking_callback("Building depth maps")

        await run_in_thread(
            chunk.buildDepthMaps,
            downscale=downscale,
            filter_mode=fmode,
            max_neighbors=max_neighbors,
            reuse_depth=reuse_depth,
            progress=cb,
        )

        return {
            "status": "depth_maps_built",
            "downscale": downscale,
            "filter_mode": filter_mode,
        }

    @mcp.tool()
    async def build_point_cloud(
        source_data: str = "depth_maps",
        point_colors: bool = True,
        point_confidence: bool = False,
        ctx: Context = None,
    ) -> dict:
        """Build a dense point cloud from depth maps.

        Args:
            source_data: Source: "depth_maps", "laser_scans".
            point_colors: Calculate point colors.
            point_confidence: Calculate point confidence values.

        Returns:
            Point cloud statistics.
        """
        chunk = get_chunk()
        require_depth_maps(chunk)

        src = resolve_enum("data_source", source_data)
        cb = make_progress_callback(ctx, "Building point cloud") if ctx else make_tracking_callback("Building point cloud")

        await run_in_thread(
            chunk.buildPointCloud,
            source_data=src,
            point_colors=point_colors,
            point_confidence=point_confidence,
            progress=cb,
        )

        pc = chunk.point_cloud
        point_count = len(pc.points) if pc else 0
        return {
            "status": "point_cloud_built",
            "point_count": point_count,
        }

    @mcp.tool()
    async def filter_point_cloud(
        point_spacing: float = 0,
        clip_to_region: bool = False,
        ctx: Context = None,
    ) -> dict:
        """Filter (subsample) the dense point cloud.

        Reduces point count while maintaining uniform distribution.

        Args:
            point_spacing: Desired point spacing in meters (0 = auto).
            clip_to_region: Clip points to the reconstruction region.

        Returns:
            Point count before and after filtering.
        """
        chunk = get_chunk()
        require_point_cloud(chunk)

        before = len(chunk.point_cloud.points)
        cb = make_progress_callback(ctx, "Filtering point cloud") if ctx else make_tracking_callback("Filtering point cloud")

        await run_in_thread(
            chunk.filterPointCloud,
            point_spacing=point_spacing,
            clip_to_region=clip_to_region,
            progress=cb,
        )

        after = len(chunk.point_cloud.points)
        return {
            "before": before,
            "after": after,
            "removed": before - after,
        }

    @mcp.tool()
    async def classify_ground_points(
        max_angle: float = 10.0,
        max_distance: float = 1.0,
        max_terrain_slope: float = 10.0,
        cell_size: float = 50.0,
        ctx: Context = None,
    ) -> dict:
        """Classify ground points in the dense point cloud.

        Uses progressive morphological filter to separate ground from
        non-ground points. Essential for DEM generation from aerial surveys.

        Args:
            max_angle: Maximum angle in degrees.
            max_distance: Maximum distance in meters.
            max_terrain_slope: Maximum terrain slope in degrees.
            cell_size: Cell size in meters.

        Returns:
            Classification results.
        """
        chunk = get_chunk()
        require_point_cloud(chunk)

        cb = make_progress_callback(ctx, "Classifying ground points") if ctx else make_tracking_callback("Classifying ground points")

        await run_in_thread(
            chunk.point_cloud.classifyGroundPoints,
            max_angle=max_angle,
            max_distance=max_distance,
            max_terrain_slope=max_terrain_slope,
            cell_size=cell_size,
            progress=cb,
        )

        return {"status": "ground_classification_complete"}

    @mcp.tool()
    def clear_depth_maps() -> dict:
        """Remove depth maps from the active chunk to free memory.

        Depth maps can consume significant RAM. Remove them after
        building a point cloud or mesh if no longer needed.

        Returns:
            Confirmation of removal.
        """
        chunk = get_chunk()
        if chunk.depth_maps is None:
            return {"status": "no_depth_maps_to_clear"}
        chunk.remove(chunk.depth_maps)
        return {"status": "depth_maps_cleared"}

    @mcp.tool()
    def clear_point_cloud() -> dict:
        """Remove the dense point cloud from the active chunk to free memory.

        Returns:
            Confirmation of removal.
        """
        chunk = get_chunk()
        if chunk.point_cloud is None:
            return {"status": "no_point_cloud_to_clear"}
        chunk.remove(chunk.point_cloud)
        return {"status": "point_cloud_cleared"}

    @mcp.tool()
    async def calculate_point_normals(
        point_count: int = 20,
        ctx: Context = None,
    ) -> dict:
        """Calculate normal vectors for the dense point cloud.

        Normals are needed for some meshing algorithms and point cloud
        visualization.

        Args:
            point_count: Number of neighboring points used for normal estimation.

        Returns:
            Confirmation that normals were calculated.
        """
        chunk = get_chunk()
        require_point_cloud(chunk)

        cb = make_progress_callback(ctx, "Calculating point normals") if ctx else make_tracking_callback("Calculating point normals")

        await run_in_thread(
            chunk.point_cloud.calculateNormals,
            point_count=point_count,
            progress=cb,
        )

        return {"status": "normals_calculated"}

    @mcp.tool()
    async def colorize_point_cloud(
        source_data: str = "images",
        ctx: Context = None,
    ) -> dict:
        """Colorize the dense point cloud from source imagery.

        Args:
            source_data: Data source for colorization (e.g. "images").

        Returns:
            Confirmation that the point cloud was colorized.
        """
        chunk = get_chunk()
        require_point_cloud(chunk)

        cb = make_progress_callback(ctx, "Colorizing point cloud") if ctx else make_tracking_callback("Colorizing point cloud")

        await run_in_thread(
            chunk.colorizePointCloud,
            source_data=resolve_enum("data_source", source_data),
            progress=cb,
        )

        return {"status": "point_cloud_colorized"}

    @mcp.tool()
    def filter_points_by_confidence(
        min_confidence: int = 0,
        max_confidence: int = 255,
    ) -> dict:
        """Filter dense point cloud points by confidence value.

        Sets a confidence filter so that only points within the specified
        range are used for subsequent operations.

        Args:
            min_confidence: Minimum confidence value (0-255).
            max_confidence: Maximum confidence value (0-255).

        Returns:
            Confirmation with the applied confidence range.
        """
        chunk = get_chunk()
        require_point_cloud(chunk)

        chunk.point_cloud.setConfidenceFilter(min_confidence, max_confidence)

        return {"status": "confidence_filter_set", "min": min_confidence, "max": max_confidence}

    @mcp.tool()
    def remove_points_by_class(classes: list[int]) -> dict:
        """Remove points belonging to specific classification classes.

        Standard classes: 0=Created/Never classified, 1=Unclassified,
        2=Ground, 3=Low Vegetation, 4=Medium Vegetation,
        5=High Vegetation, 6=Building, 7=Low Point/Noise,
        9=Water, 17=Bridge.

        Args:
            classes: List of classification class IDs to remove.

        Returns:
            Point counts before and after removal.
        """
        chunk = get_chunk()
        require_point_cloud(chunk)

        before = len(chunk.point_cloud.points)
        chunk.point_cloud.removePoints(classes)
        after = len(chunk.point_cloud.points)

        return {"before": before, "after": after, "removed": before - after, "classes_removed": classes}

    @mcp.tool()
    def assign_point_class(source_class: int, target_class: int) -> dict:
        """Reclassify points from one class to another.

        Args:
            source_class: Class ID to reclassify from.
            target_class: Class ID to reclassify to.

        Returns:
            Confirmation of reclassification.
        """
        chunk = get_chunk()
        require_point_cloud(chunk)

        chunk.point_cloud.assignClass(source_class=source_class, target_class=target_class)

        return {"status": "points_reclassified", "source_class": source_class, "target_class": target_class}

    @mcp.tool()
    def get_point_cloud_stats() -> dict:
        """Return dense point cloud statistics.

        Returns:
            Point count, bounds, and basic properties.
        """
        chunk = get_chunk()
        require_point_cloud(chunk)
        pc = chunk.point_cloud
        return {
            "point_count": len(pc.points),
            "has_point_cloud": True,
        }
