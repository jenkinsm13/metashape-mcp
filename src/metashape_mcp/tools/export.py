"""Export tools: models, point clouds, rasters, reports, cameras, shapes."""

import os

import Metashape

from metashape_mcp.utils.bridge import (
    get_chunk,
    require_elevation,
    require_model,
    require_orthomosaic,
    require_point_cloud,
)
from metashape_mcp.utils.enums import resolve_enum
from metashape_mcp.utils.progress import (
    make_tracking_callback,
)


def register(mcp) -> None:
    """Register export tools."""

    @mcp.tool()
    def export_model(
        path: str,
        format: str = "obj",
        save_texture: bool = True,
        save_normals: bool = True,
        save_colors: bool = True,
        binary: bool = True,
    ) -> dict:
        """Export the 3D model to a file.

        Args:
            path: Output file path.
            format: "obj", "ply", "fbx", "gltf", "stl", "collada", "3ds", "dxf".
            save_texture: Include texture in export.
            save_normals: Include vertex normals.
            save_colors: Include vertex colors.
            binary: Use binary encoding (if supported by format).

        Returns:
            Export confirmation with file path and size.
        """
        chunk = get_chunk()
        require_model(chunk)

        fmt = resolve_enum("model_format", format)
        cb = make_tracking_callback("Exporting model")

        chunk.exportModel(
            path=path,
            format=fmt,
            save_texture=save_texture,
            save_normals=save_normals,
            save_colors=save_colors,
            binary=binary,
            progress=cb,
        )

        size = os.path.getsize(path) if os.path.exists(path) else 0
        return {"path": path, "size_bytes": size}

    @mcp.tool()
    def export_point_cloud(
        path: str,
        format: str = "las",
        source_data: str = "point_cloud",
        save_colors: bool = True,
        save_normals: bool = True,
        save_classification: bool = True,
    ) -> dict:
        """Export the dense point cloud to a file.

        Args:
            path: Output file path.
            format: "las", "laz", "ply", "xyz", "e57", "cesium", "pcd", "copc".
            source_data: "point_cloud" or "tie_points".
            save_colors: Include point colors.
            save_normals: Include point normals.
            save_classification: Include point classification.

        Returns:
            Export confirmation with file path and size.
        """
        chunk = get_chunk()

        fmt = resolve_enum("point_cloud_format", format)
        src = resolve_enum("data_source", source_data)
        cb = make_tracking_callback("Exporting point cloud")

        chunk.exportPointCloud(
            path=path,
            format=fmt,
            source_data=src,
            save_point_color=save_colors,
            save_point_normal=save_normals,
            save_point_classification=save_classification,
            progress=cb,
        )

        size = os.path.getsize(path) if os.path.exists(path) else 0
        return {"path": path, "size_bytes": size}

    @mcp.tool()
    def export_orthomosaic(
        path: str,
        format: str = "tif",
        save_alpha: bool = True,
    ) -> dict:
        """Export the orthomosaic to a raster file.

        Args:
            path: Output file path.
            format: "tif", "kmz", "mbtiles", "geopackage".
            save_alpha: Include alpha channel.

        Returns:
            Export confirmation with file path and size.
        """
        chunk = get_chunk()
        require_orthomosaic(chunk)

        fmt = resolve_enum("raster_format", format)
        cb = make_tracking_callback("Exporting orthomosaic")

        chunk.exportRaster(
            path=path,
            format=fmt,
            source_data=Metashape.OrthomosaicData,
            save_alpha=save_alpha,
            progress=cb,
        )

        size = os.path.getsize(path) if os.path.exists(path) else 0
        return {"path": path, "size_bytes": size}

    @mcp.tool()
    def export_dem(
        path: str,
        format: str = "tif",
        nodata_value: float = -32767,
    ) -> dict:
        """Export the DEM to a raster file.

        Args:
            path: Output file path.
            format: "tif", "kmz", "xyz".
            nodata_value: Value for no-data pixels.

        Returns:
            Export confirmation with file path and size.
        """
        chunk = get_chunk()
        require_elevation(chunk)

        fmt = resolve_enum("raster_format", format)
        cb = make_tracking_callback("Exporting DEM")

        chunk.exportRaster(
            path=path,
            format=fmt,
            source_data=Metashape.ElevationData,
            nodata_value=nodata_value,
            progress=cb,
        )

        size = os.path.getsize(path) if os.path.exists(path) else 0
        return {"path": path, "size_bytes": size}

    @mcp.tool()
    def export_report(
        path: str,
        title: str = "",
        description: str = "",
    ) -> dict:
        """Export a processing report in PDF format.

        Args:
            path: Output PDF file path.
            title: Report title.
            description: Report description.

        Returns:
            Export confirmation.
        """
        chunk = get_chunk()
        cb = make_tracking_callback("Exporting report")

        chunk.exportReport(
            path=path,
            title=title,
            description=description,
            progress=cb,
        )

        size = os.path.getsize(path) if os.path.exists(path) else 0
        return {"path": path, "size_bytes": size}

    @mcp.tool()
    def export_cameras(
        path: str,
        format: str = "xml",
    ) -> dict:
        """Export camera positions and orientations.

        Args:
            path: Output file path.
            format: "xml", "bundler", "chan", "opk", "colmap", "fbx".

        Returns:
            Export confirmation.
        """
        chunk = get_chunk()

        fmt = resolve_enum("cameras_format", format)
        cb = make_tracking_callback("Exporting cameras")

        chunk.exportCameras(
            path=path,
            format=fmt,
            progress=cb,
        )

        size = os.path.getsize(path) if os.path.exists(path) else 0
        return {"path": path, "size_bytes": size}

    @mcp.tool()
    def export_tiled_model(
        path: str,
        format: str = "cesium",
    ) -> dict:
        """Export a tiled model for web/3D streaming.

        Args:
            path: Output directory or file path.
            format: "cesium", "zip", "3mx", "slpk".

        Returns:
            Export confirmation.
        """
        chunk = get_chunk()
        if chunk.tiled_model is None:
            raise RuntimeError(
                "No tiled model found. Run 'build_tiled_model' first."
            )

        fmt = resolve_enum("tiled_model_format", format)
        cb = make_tracking_callback("Exporting tiled model")

        chunk.exportTiledModel(
            path=path,
            format=fmt,
            progress=cb,
        )

        return {"path": path}

    @mcp.tool()
    def export_shapes(
        path: str,
        format: str = "shp",
        save_polygons: bool = True,
        save_polylines: bool = True,
        save_points: bool = True,
    ) -> dict:
        """Export shapes (boundaries, polylines, points) to file.

        Args:
            path: Output file path.
            format: "shp", "kml", "dxf", "geojson", "geopackage", "csv".
            save_polygons: Export polygon shapes.
            save_polylines: Export polyline shapes.
            save_points: Export point shapes.

        Returns:
            Export confirmation.
        """
        chunk = get_chunk()

        fmt = resolve_enum("shapes_format", format)
        cb = make_tracking_callback("Exporting shapes")

        chunk.exportShapes(
            path=path,
            format=fmt,
            save_polygons=save_polygons,
            save_polylines=save_polylines,
            save_points=save_points,
            progress=cb,
        )

        size = os.path.getsize(path) if os.path.exists(path) else 0
        return {"path": path, "size_bytes": size}

    @mcp.tool()
    def export_reference(
        path: str,
        format: str = "csv",
        delimiter: str = ",",
    ) -> dict:
        """Export camera reference data (positions and errors) to file.

        Args:
            path: Output file path.
            format: "csv", "xml", "tel".
            delimiter: Column delimiter for CSV format.

        Returns:
            Export confirmation with file path and size.
        """
        chunk = get_chunk()

        fmt = resolve_enum("reference_format", format)

        chunk.exportReference(
            path=path,
            format=fmt,
            delimiter=delimiter,
        )

        size = os.path.getsize(path) if os.path.exists(path) else 0
        return {"path": path, "size_bytes": size}

    @mcp.tool()
    def export_tie_points(
        path: str,
        format: str = "las",
        save_colors: bool = True,
    ) -> dict:
        """Export the sparse tie point cloud to a file.

        Args:
            path: Output file path.
            format: "las", "laz", "ply", "xyz", "e57", "cesium", "pcd", "copc".
            save_colors: Include point colors.

        Returns:
            Export confirmation with file path and size.
        """
        chunk = get_chunk()
        if chunk.tie_points is None:
            raise RuntimeError(
                "No tie points found. Run 'align_cameras' first."
            )

        fmt = resolve_enum("point_cloud_format", format)
        src = resolve_enum("data_source", "tie_points")
        cb = make_tracking_callback("Exporting tie points")

        chunk.exportPointCloud(
            path=path,
            format=fmt,
            source_data=src,
            save_point_color=save_colors,
            progress=cb,
        )

        size = os.path.getsize(path) if os.path.exists(path) else 0
        return {"path": path, "size_bytes": size}
