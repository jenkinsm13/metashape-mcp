"""Camera and sensor detail resources."""

from metashape_mcp.utils.bridge import get_chunk


def register(mcp) -> None:
    """Register camera info resources."""

    @mcp.resource("metashape://chunk/{label}/cameras")
    def chunk_cameras(label: str) -> list[dict]:
        """Camera list with alignment status for a chunk."""
        chunk = get_chunk(label=label)

        result = []
        for cam in chunk.cameras:
            info = {
                "label": cam.label,
                "key": cam.key,
                "enabled": cam.enabled,
                "aligned": cam.transform is not None,
                "sensor": cam.sensor.label if cam.sensor else None,
            }

            # Image quality if analyzed
            try:
                info["quality"] = float(cam.meta["Image/Quality"])
            except (KeyError, TypeError):
                pass

            # Reference position
            if cam.reference.location:
                info["reference_location"] = list(cam.reference.location)
                info["reference_enabled"] = cam.reference.enabled

            # Estimated position
            if cam.transform and chunk.transform.matrix:
                try:
                    pos = chunk.transform.matrix.mulp(cam.center)
                    if chunk.crs:
                        pos = chunk.crs.project(pos)
                    info["estimated_location"] = list(pos)
                except Exception:
                    pass

            result.append(info)

        return result

    @mcp.resource("metashape://chunk/{label}/sensors")
    def chunk_sensors(label: str) -> list[dict]:
        """Sensor calibration information for a chunk."""
        chunk = get_chunk(label=label)

        result = []
        for sensor in chunk.sensors:
            info = {
                "label": sensor.label,
                "key": sensor.key,
                "type": str(sensor.type),
                "width": sensor.width,
                "height": sensor.height,
                "focal_length": sensor.focal_length,
                "pixel_width": sensor.pixel_width,
                "pixel_height": sensor.pixel_height,
            }

            # Calibration info
            cal = sensor.calibration
            if cal:
                info["calibration"] = {
                    "f": cal.f,
                    "cx": cal.cx,
                    "cy": cal.cy,
                    "k1": cal.k1,
                    "k2": cal.k2,
                    "k3": cal.k3,
                    "p1": cal.p1,
                    "p2": cal.p2,
                    "b1": cal.b1,
                    "b2": cal.b2,
                }

            # Count cameras using this sensor
            info["camera_count"] = sum(
                1 for cam in chunk.cameras if cam.sensor == sensor
            )

            result.append(info)

        return result
