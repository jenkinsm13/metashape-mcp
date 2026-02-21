"""Coordinate reference system and region tools."""

import Metashape

from metashape_mcp.utils.bridge import get_chunk


def register(mcp) -> None:
    """Register coordinate system tools."""

    @mcp.tool()
    def set_crs(
        epsg_code: int | None = None,
        wkt: str | None = None,
    ) -> dict:
        """Set the coordinate reference system for the active chunk.

        Provide either an EPSG code or a WKT string.

        Args:
            epsg_code: EPSG code (e.g., 4326 for WGS84, 32633 for UTM 33N).
            wkt: Well-Known Text (WKT) CRS definition.

        Returns:
            The applied CRS info.
        """
        chunk = get_chunk()

        if epsg_code:
            crs = Metashape.CoordinateSystem(f"EPSG::{epsg_code}")
        elif wkt:
            crs = Metashape.CoordinateSystem(wkt)
        else:
            raise ValueError("Provide either 'epsg_code' or 'wkt'.")

        chunk.crs = crs

        return {
            "crs_name": crs.name,
            "epsg": epsg_code,
        }

    @mcp.tool()
    def set_region(
        center: list[float] | None = None,
        size: list[float] | None = None,
    ) -> dict:
        """Set the processing region (reconstruction volume).

        The region defines the 3D bounding box for processing.
        Coordinates are in the chunk's internal coordinate system.

        Args:
            center: Region center [x, y, z].
            size: Region size [width, height, depth].

        Returns:
            Updated region info.
        """
        chunk = get_chunk()
        region = chunk.region

        if center and len(center) >= 3:
            region.center = Metashape.Vector(center[:3])

        if size and len(size) >= 3:
            region.size = Metashape.Vector(size[:3])

        chunk.region = region

        return {
            "center": list(chunk.region.center),
            "size": list(chunk.region.size),
        }

    @mcp.tool()
    def update_transform() -> dict:
        """Update the chunk transformation matrix.

        Recalculates the chunk-to-world transform based on reference
        data (camera positions, markers, scalebars).

        Returns:
            Transform info.
        """
        chunk = get_chunk()
        chunk.updateTransform()

        t = chunk.transform
        return {
            "status": "transform_updated",
            "has_transform": t.matrix is not None,
            "scale": t.scale if t.scale else None,
        }

    @mcp.tool()
    def transform_chunk_crs(target_epsg: int) -> dict:
        """Reproject the chunk to a new coordinate reference system.

        Args:
            target_epsg: Target EPSG code (e.g., 32633 for UTM 33N).

        Returns:
            The new CRS name.
        """
        chunk = get_chunk()
        crs = Metashape.CoordinateSystem(f"EPSG::{target_epsg}")
        chunk.crs = crs
        chunk.updateTransform()

        return {
            "status": "crs_reprojected",
            "crs_name": crs.name,
            "epsg": target_epsg,
        }

    @mcp.tool()
    def get_chunk_bounds() -> dict:
        """Return the bounding box of the chunk's data in geographic coordinates.

        Returns:
            Center, size, and CRS name of the chunk region.
        """
        chunk = get_chunk()
        region = chunk.region
        center = list(region.center)
        size = list(region.size)

        result: dict = {
            "center_internal": center,
            "size": size,
            "crs_name": chunk.crs.name if chunk.crs else None,
        }

        if chunk.crs:
            try:
                geo_center = chunk.crs.project(
                    chunk.transform.matrix.mulp(region.center)
                )
                result["center_geographic"] = list(geo_center)
            except (AttributeError, TypeError):
                result["center_geographic"] = None

        return result

    @mcp.tool()
    def reset_region() -> dict:
        """Reset the processing region to automatically fit all chunk data.

        Returns:
            The new region center and size.
        """
        chunk = get_chunk()
        chunk.resetRegion()
        region = chunk.region
        return {
            "status": "region_reset",
            "center": list(region.center),
            "size": list(region.size),
        }

    @mcp.tool()
    def set_region_rotation(
        yaw: float = 0,
        pitch: float = 0,
        roll: float = 0,
    ) -> dict:
        """Rotate the processing region by yaw/pitch/roll in degrees.

        Args:
            yaw: Rotation around vertical axis in degrees.
            pitch: Rotation around lateral axis in degrees.
            roll: Rotation around longitudinal axis in degrees.

        Returns:
            The applied rotation angles.
        """
        chunk = get_chunk()
        region = chunk.region
        R = Metashape.Utils.ypr2mat(Metashape.Vector([yaw, pitch, roll]))
        region.rot = R
        chunk.region = region
        return {"yaw": yaw, "pitch": pitch, "roll": roll}

    @mcp.tool()
    def set_reference_settings(
        camera_accuracy_xy: float | None = None,
        camera_accuracy_z: float | None = None,
        marker_accuracy_xy: float | None = None,
        marker_accuracy_z: float | None = None,
        tie_point_accuracy: float | None = None,
    ) -> dict:
        """Configure reference accuracy settings for the chunk.

        These settings control how much Metashape trusts camera GPS
        vs tie points vs GCP markers during optimization.

        Args:
            camera_accuracy_xy: Horizontal camera location accuracy in meters.
            camera_accuracy_z: Vertical camera location accuracy in meters.
            marker_accuracy_xy: Horizontal marker location accuracy in meters.
            marker_accuracy_z: Vertical marker location accuracy in meters.
            tie_point_accuracy: Tie point accuracy in pixels.

        Returns:
            Current reference accuracy settings.
        """
        chunk = get_chunk()

        if camera_accuracy_xy is not None:
            z = camera_accuracy_z or camera_accuracy_xy
            chunk.camera_location_accuracy = Metashape.Vector(
                [camera_accuracy_xy, camera_accuracy_xy, z]
            )

        if marker_accuracy_xy is not None:
            z = marker_accuracy_z or marker_accuracy_xy
            chunk.marker_location_accuracy = Metashape.Vector(
                [marker_accuracy_xy, marker_accuracy_xy, z]
            )

        if tie_point_accuracy is not None:
            chunk.tiepoint_accuracy = tie_point_accuracy

        return {
            "camera_location_accuracy": list(chunk.camera_location_accuracy),
            "marker_location_accuracy": list(chunk.marker_location_accuracy),
            "tiepoint_accuracy": chunk.tiepoint_accuracy,
        }
