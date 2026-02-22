"""Import tools: models, point clouds, reference data, cameras, shapes."""

import os

import Metashape

from metashape_mcp.utils.bridge import auto_save, get_chunk
from metashape_mcp.utils.enums import resolve_enum
from metashape_mcp.utils.progress import make_tracking_callback


def register(mcp) -> None:
    """Register import tools."""

    @mcp.tool()
    def import_model(
        path: str,
        format: str | None = None,
        crs_epsg: int | None = None,
    ) -> dict:
        """Import a 3D model from file.

        Args:
            path: Path to the model file.
            format: Format override: "obj", "ply", "fbx", "gltf", etc.
                   Auto-detected from extension if not specified.
            crs_epsg: EPSG code for the model coordinate system.

        Returns:
            Import confirmation.
        """
        if not os.path.exists(path):
            raise FileNotFoundError(f"Model file not found: {path}")

        chunk = get_chunk()

        kwargs = {"path": path}
        if format:
            kwargs["format"] = resolve_enum("model_format", format)
        if crs_epsg:
            kwargs["crs"] = Metashape.CoordinateSystem(f"EPSG::{crs_epsg}")

        cb = make_tracking_callback("Importing model")
        kwargs["progress"] = cb

        chunk.importModel(**kwargs)

        auto_save()
        return {"status": "model_imported", "path": path}

    @mcp.tool()
    def import_point_cloud(
        path: str,
        format: str | None = None,
        crs_epsg: int | None = None,
        is_laser_scan: bool = False,
    ) -> dict:
        """Import a point cloud from file.

        Args:
            path: Path to the point cloud file.
            format: Format override: "las", "laz", "ply", "e57", etc.
                   Auto-detected from extension if not specified.
            crs_epsg: EPSG code for the coordinate system.
            is_laser_scan: Import as laser scan data.

        Returns:
            Import confirmation.
        """
        if not os.path.exists(path):
            raise FileNotFoundError(f"Point cloud file not found: {path}")

        chunk = get_chunk()

        kwargs = {"path": path, "is_laser_scan": is_laser_scan}
        if format:
            kwargs["format"] = resolve_enum("point_cloud_format", format)
        if crs_epsg:
            kwargs["crs"] = Metashape.CoordinateSystem(f"EPSG::{crs_epsg}")

        cb = make_tracking_callback("Importing point cloud")
        kwargs["progress"] = cb

        chunk.importPointCloud(**kwargs)

        auto_save()
        return {"status": "point_cloud_imported", "path": path}

    @mcp.tool()
    def import_reference(
        path: str,
        format: str = "csv",
        columns: str = "nxyz",
        delimiter: str = ",",
        crs_epsg: int | None = None,
        create_markers: bool = False,
        skip_rows: int = 0,
    ) -> dict:
        """Import reference data (GCPs, camera coordinates) from file.

        Args:
            path: Path to the reference file.
            format: "csv", "xml", or "tel".
            columns: Column order for CSV. Characters: n=label, x/y/z=coords,
                    X/Y/Z=accuracy, a/b/c=rotation. Default "nxyz".
            delimiter: Column delimiter for CSV.
            crs_epsg: EPSG code for the reference coordinate system.
            create_markers: Create markers for entries not found in chunk.
            skip_rows: Number of header rows to skip.

        Returns:
            Import confirmation.
        """
        if not os.path.exists(path):
            raise FileNotFoundError(f"Reference file not found: {path}")

        chunk = get_chunk()

        fmt = resolve_enum("reference_format", format)

        kwargs = {
            "path": path,
            "format": fmt,
            "columns": columns,
            "delimiter": delimiter,
            "create_markers": create_markers,
            "skip_rows": skip_rows,
        }
        if crs_epsg:
            kwargs["crs"] = Metashape.CoordinateSystem(f"EPSG::{crs_epsg}")

        cb = make_tracking_callback("Importing reference")
        kwargs["progress"] = cb

        chunk.importReference(**kwargs)

        auto_save()
        return {"status": "reference_imported", "path": path}

    @mcp.tool()
    def import_cameras(
        path: str,
        format: str = "xml",
        crs_epsg: int | None = None,
    ) -> dict:
        """Import camera positions and orientations from file.

        Args:
            path: Path to the camera file.
            format: "xml", "bundler", "chan", "opk", "colmap".
            crs_epsg: EPSG code for the coordinate system.

        Returns:
            Import confirmation.
        """
        if not os.path.exists(path):
            raise FileNotFoundError(f"Camera file not found: {path}")

        chunk = get_chunk()

        fmt = resolve_enum("cameras_format", format)

        kwargs = {"path": path, "format": fmt}
        if crs_epsg:
            kwargs["crs"] = Metashape.CoordinateSystem(f"EPSG::{crs_epsg}")

        cb = make_tracking_callback("Importing cameras")
        kwargs["progress"] = cb

        chunk.importCameras(**kwargs)

        auto_save()
        return {"status": "cameras_imported", "path": path}

    @mcp.tool()
    def import_shapes(
        path: str,
        format: str | None = None,
        replace: bool = False,
        crs_epsg: int | None = None,
    ) -> dict:
        """Import GIS shapes (boundaries, polygons, polylines) from file.

        Args:
            path: Path to the shapes file.
            format: "shp", "kml", "dxf", "geojson", "geopackage", "csv".
                   Auto-detected if not specified.
            replace: Replace existing shapes.
            crs_epsg: EPSG code for the coordinate system (CSV only).

        Returns:
            Import confirmation.
        """
        if not os.path.exists(path):
            raise FileNotFoundError(f"Shapes file not found: {path}")

        chunk = get_chunk()

        kwargs = {"path": path, "replace": replace}
        if format:
            kwargs["format"] = resolve_enum("shapes_format", format)
        if crs_epsg:
            kwargs["crs"] = Metashape.CoordinateSystem(f"EPSG::{crs_epsg}")

        cb = make_tracking_callback("Importing shapes")
        kwargs["progress"] = cb

        chunk.importShapes(**kwargs)

        auto_save()
        return {"status": "shapes_imported", "path": path}

    @mcp.tool()
    def create_shape(
        vertices: list[list[float]],
        shape_type: str = "polygon",
        label: str | None = None,
        group_label: str | None = None,
    ) -> dict:
        """Create a shape (boundary, polygon, polyline) in the chunk.

        Shapes are used to define areas of interest (AOI), clip processing
        regions, or mark features.

        Args:
            vertices: List of coordinate lists, e.g. [[lon, lat, alt], ...].
            shape_type: "polygon", "polyline", or "point".
            label: Optional label for the shape.
            group_label: Optional label for a new group to contain the shape.

        Returns:
            Shape summary with label, type, and vertex count.
        """
        chunk = get_chunk()
        if not chunk.shapes:
            chunk.shapes = Metashape.Shapes()
            chunk.shapes.crs = chunk.crs

        shape = chunk.shapes.addShape()
        if label:
            shape.label = label

        type_map = {
            "polygon": Metashape.Shape.Type.Polygon,
            "polyline": Metashape.Shape.Type.Polyline,
            "point": Metashape.Shape.Type.Point,
        }
        stype = type_map.get(shape_type.lower())
        if stype is None:
            raise ValueError(f"Unknown shape type: {shape_type}. Use: polygon, polyline, point.")
        shape.type = stype
        shape.vertices = [Metashape.Vector(v) for v in vertices]

        if group_label:
            group = chunk.shapes.addGroup()
            group.label = group_label
            shape.group = group

        auto_save()
        return {"label": shape.label, "type": shape_type, "vertices": len(vertices)}
