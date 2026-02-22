"""Marker and ground control point (GCP) tools."""

import os

import Metashape

from metashape_mcp.utils.bridge import auto_save, get_chunk
from metashape_mcp.utils.enums import resolve_enum
from metashape_mcp.utils.progress import make_tracking_callback


def register(mcp) -> None:
    """Register marker and GCP tools."""

    @mcp.tool()
    def detect_markers(
        target_type: str = "circular_12bit",
        tolerance: int = 50,
        filter_mask: bool = False,
    ) -> dict:
        """Auto-detect coded targets in images and create markers.

        Args:
            target_type: Target type: "circular_12bit", "circular_14bit",
                        "circular_16bit", "circular_20bit", "circular", "cross".
            tolerance: Detector tolerance (0-100).
            filter_mask: Ignore masked image regions.

        Returns:
            Number of markers detected.
        """
        chunk = get_chunk()
        if not chunk.cameras:
            raise RuntimeError("No cameras in chunk. Add photos first.")

        ttype = resolve_enum("target_type", target_type)
        cb = make_tracking_callback("Detecting markers")

        chunk.detectMarkers(
            target_type=ttype,
            tolerance=tolerance,
            filter_mask=filter_mask,
            progress=cb,
        )

        auto_save()
        return {
            "markers_detected": len(chunk.markers),
            "markers": [
                {"label": m.label, "key": m.key}
                for m in chunk.markers
            ],
        }

    @mcp.tool()
    def add_marker(
        label: str | None = None,
        position: list[float] | None = None,
    ) -> dict:
        """Add a marker manually to the active chunk.

        Args:
            label: Marker label. Auto-generated if not provided.
            position: Optional [x, y, z] reference coordinates.

        Returns:
            Info about the created marker.
        """
        chunk = get_chunk()
        marker = chunk.addMarker()

        if label:
            marker.label = label
        if position and len(position) >= 3:
            marker.reference.location = Metashape.Vector(position[:3])
            marker.reference.enabled = True

        auto_save()
        return {
            "label": marker.label,
            "key": marker.key,
            "position": list(marker.reference.location) if marker.reference.location else None,
        }

    @mcp.tool()
    def add_scalebar(
        marker1_label: str,
        marker2_label: str,
        distance: float,
    ) -> dict:
        """Add a scalebar between two markers with a known distance.

        Scalebars constrain the model scale during optimization.

        Args:
            marker1_label: Label of the first marker.
            marker2_label: Label of the second marker.
            distance: Known distance between markers in meters.

        Returns:
            Scalebar info.
        """
        chunk = get_chunk()

        m1 = m2 = None
        for m in chunk.markers:
            if m.label == marker1_label:
                m1 = m
            if m.label == marker2_label:
                m2 = m

        if m1 is None:
            raise RuntimeError(f"Marker '{marker1_label}' not found.")
        if m2 is None:
            raise RuntimeError(f"Marker '{marker2_label}' not found.")

        scalebar = chunk.addScalebar(m1, m2)
        scalebar.reference.distance = distance

        auto_save()
        return {
            "label": scalebar.label,
            "marker1": marker1_label,
            "marker2": marker2_label,
            "distance": distance,
        }

    @mcp.tool()
    def refine_markers() -> dict:
        """Refine marker positions for sub-pixel accuracy.

        Adjusts marker projections in individual images for better
        accuracy. Run after detect_markers or manual marker placement.

        Returns:
            Marker refinement results.
        """
        chunk = get_chunk()
        if not chunk.markers:
            raise RuntimeError("No markers in chunk.")

        cb = make_tracking_callback("Refining markers")
        chunk.trackMarkers(progress=cb)

        auto_save()
        return {
            "status": "markers_refined",
            "marker_count": len(chunk.markers),
        }

    @mcp.tool()
    def list_markers() -> list[dict]:
        """List all markers with their coordinates and error estimates.

        Returns:
            List of markers with labels, positions, and errors.
        """
        chunk = get_chunk()

        result = []
        for m in chunk.markers:
            info = {
                "label": m.label,
                "key": m.key,
                "enabled": m.reference.enabled,
                "type": str(m.type),
            }

            if m.reference.location:
                info["reference_position"] = list(m.reference.location)

            if m.position:
                info["estimated_position"] = list(m.position)

            if m.reference.location and m.position and chunk.transform.matrix:
                # Calculate error if both reference and estimated exist
                try:
                    est = chunk.transform.matrix.mulp(m.position)
                    ref = m.reference.location
                    if chunk.crs:
                        est = chunk.crs.project(
                            chunk.transform.matrix.mulp(m.position)
                        )
                    error = (est - ref).norm()
                    info["error_m"] = round(error, 4)
                except Exception:
                    pass

            # Count projections
            projections = sum(
                1 for cam in chunk.cameras
                if m.projections.get(cam) is not None
            )
            info["projections"] = projections

            result.append(info)

        return result

    @mcp.tool()
    def remove_marker(label: str) -> dict:
        """Remove a marker by its label.

        Args:
            label: Label of the marker to remove.

        Returns:
            Confirmation with remaining marker count.
        """
        chunk = get_chunk()

        for marker in chunk.markers:
            if marker.label == label:
                chunk.remove(marker)
                auto_save()
                return {
                    "status": "marker_removed",
                    "label": label,
                    "remaining_markers": len(chunk.markers),
                }

        raise RuntimeError(f"Marker '{label}' not found.")

    @mcp.tool()
    def set_marker_reference(
        label: str,
        x: float,
        y: float,
        z: float,
        accuracy_xy: float | None = None,
        accuracy_z: float | None = None,
        enabled: bool = True,
    ) -> dict:
        """Set or update a marker's reference coordinates and accuracy.

        Args:
            label: Label of the marker to update.
            x: X reference coordinate.
            y: Y reference coordinate.
            z: Z reference coordinate.
            accuracy_xy: Horizontal accuracy (applied to both X and Y).
            accuracy_z: Vertical accuracy. Defaults to accuracy_xy if not set.
            enabled: Whether the reference is enabled for optimization.

        Returns:
            Updated marker info.
        """
        chunk = get_chunk()

        for marker in chunk.markers:
            if marker.label == label:
                marker.reference.location = Metashape.Vector([x, y, z])
                marker.reference.enabled = enabled

                if accuracy_xy is not None:
                    az = accuracy_z if accuracy_z is not None else accuracy_xy
                    marker.reference.accuracy = Metashape.Vector(
                        [accuracy_xy, accuracy_xy, az]
                    )

                auto_save()
                return {
                    "label": marker.label,
                    "key": marker.key,
                    "reference_position": list(marker.reference.location),
                    "enabled": marker.reference.enabled,
                    "accuracy": list(marker.reference.accuracy)
                    if marker.reference.accuracy
                    else None,
                }

        raise RuntimeError(f"Marker '{label}' not found.")

    @mcp.tool()
    def export_markers(path: str, delimiter: str = ",") -> dict:
        """Export all marker positions and errors to CSV.

        Args:
            path: Output file path for the CSV export.
            delimiter: Column delimiter. Defaults to comma.

        Returns:
            Export path and file size.
        """
        chunk = get_chunk()
        if not chunk.markers:
            raise RuntimeError("No markers in chunk.")

        try:
            chunk.exportMarkers(path=path, delimiter=delimiter)
        except AttributeError:
            chunk.exportReference(
                path=path, items=Metashape.ReferenceItemsMarkers
            )

        return {
            "path": path,
            "file_size_bytes": os.path.getsize(path),
        }

    @mcp.tool()
    def remove_scalebar(label: str) -> dict:
        """Remove a scalebar by its label.

        Args:
            label: Label of the scalebar to remove.

        Returns:
            Confirmation with remaining scalebar count.
        """
        chunk = get_chunk()

        for scalebar in chunk.scalebars:
            if scalebar.label == label:
                chunk.remove(scalebar)
                auto_save()
                return {
                    "status": "scalebar_removed",
                    "label": label,
                    "remaining_scalebars": len(chunk.scalebars),
                }

        raise RuntimeError(f"Scalebar '{label}' not found.")
