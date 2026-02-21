"""Camera management tools: enable/disable, sensor config, masks."""

import os

import Metashape

from metashape_mcp.utils.bridge import get_chunk


def register(mcp) -> None:
    """Register camera management tools."""

    @mcp.tool()
    def enable_cameras(
        labels: list[str] | None = None,
        pattern: str | None = None,
        enable: bool = True,
        invert_selection: bool = False,
    ) -> dict:
        """Enable or disable cameras for processing.

        Use this to select which cameras participate in alignment,
        depth maps, and other operations. Disabled cameras are skipped.
        Essential for incremental alignment workflows where you process
        batches of ~2000 cameras at a time.

        Args:
            labels: Specific camera labels to enable/disable.
            pattern: Substring pattern to match camera labels (e.g. "_DSC"
                     for Nikon Z9, "DJI" for drone photos).
            enable: True to enable, False to disable matched cameras.
            invert_selection: If True, enable/disable cameras NOT matching
                            the labels/pattern instead.

        Returns:
            Count of cameras changed and total enabled/disabled.
        """
        chunk = get_chunk()
        changed = 0

        for cam in chunk.cameras:
            match = False
            if labels and cam.label in labels:
                match = True
            elif pattern and pattern in cam.label:
                match = True
            elif labels is None and pattern is None:
                match = True  # All cameras

            if invert_selection:
                match = not match

            if match:
                cam.enabled = enable
                changed += 1

        enabled = sum(1 for c in chunk.cameras if c.enabled)
        return {
            "changed": changed,
            "enabled": enabled,
            "disabled": len(chunk.cameras) - enabled,
            "total": len(chunk.cameras),
        }

    @mcp.tool()
    def set_sensor(
        sensor_type: str = "frame",
        focal_length: float | None = None,
        pixel_size: float | None = None,
        label_pattern: str | None = None,
        fixed_calibration: bool = False,
        axes: str | None = None,
        rolling_shutter: str | None = None,
    ) -> dict:
        """Set camera sensor type and calibration for cameras in the chunk.

        Use this to configure fisheye lenses, set focal lengths, or fix
        sensor parameters before alignment. CRITICAL: Set the correct
        sensor type BEFORE matching/aligning — wrong type = failed alignment.

        Common setups:
        - Drone (DJI): sensor_type="frame", axes="aerial" (default)
        - Fisheye (Nikon Z9 + 11mm): sensor_type="fisheye_equidistant",
          focal_length=11, axes="terrestrial", rolling_shutter="full"
        - GoPro/action cam: sensor_type="fisheye_equidistant"

        Args:
            sensor_type: Sensor type: "frame", "fisheye_equidistant",
                         "fisheye_equisolid", "spherical", "cylindrical", "rpc".
                         Note: "fisheye" (deprecated alias) maps to equidistant.
            focal_length: Focal length in mm. Sets the initial calibration.
            pixel_size: Pixel size in mm (e.g. 0.00345 for typical sensors).
            label_pattern: Only apply to cameras whose label contains this
                          substring. If omitted, applies to ALL sensors.
            fixed_calibration: Lock calibration so it won't be adjusted
                             during alignment. Use when you have a known
                             calibration from an external source.
            axes: Camera orientation: "aerial" (Z backward, Y up — drones)
                  or "terrestrial" (Z forward, Y down — ground/vehicle).
                  If omitted, keeps current setting.
            rolling_shutter: Rolling shutter compensation mode:
                            "disabled", "regularized", or "full".
                            Use "full" for vehicle-mounted cameras.
                            If omitted, keeps current setting.

        Returns:
            Number of sensors modified and their settings.
        """
        chunk = get_chunk()

        type_map = {
            "frame": Metashape.Sensor.Type.Frame,
            "fisheye": Metashape.Sensor.Type.EquidistantFisheye,  # legacy alias
            "fisheye_equidistant": Metashape.Sensor.Type.EquidistantFisheye,
            "equidistant_fisheye": Metashape.Sensor.Type.EquidistantFisheye,
            "fisheye_equisolid": Metashape.Sensor.Type.EquisolidFisheye,
            "equisolid_fisheye": Metashape.Sensor.Type.EquisolidFisheye,
            "spherical": Metashape.Sensor.Type.Spherical,
            "cylindrical": Metashape.Sensor.Type.Cylindrical,
            "rpc": Metashape.Sensor.Type.RPC,
        }
        stype = type_map.get(sensor_type.lower())
        if stype is None:
            raise ValueError(
                f"Unknown sensor type: {sensor_type}. "
                f"Use: frame, fisheye_equidistant, fisheye_equisolid, "
                f"spherical, cylindrical, rpc."
            )

        axes_map = {
            "aerial": Metashape.Sensor.Axes.Aerial,
            "terrestrial": Metashape.Sensor.Axes.Terrestrial,
        }
        axes_val = None
        if axes is not None:
            axes_val = axes_map.get(axes.lower())
            if axes_val is None:
                raise ValueError(
                    f"Unknown axes: {axes}. Use: aerial, terrestrial."
                )

        shutter_map = {
            "disabled": Metashape.Shutter.Model.Disabled,
            "none": Metashape.Shutter.Model.Disabled,
            "regularized": Metashape.Shutter.Model.Regularized,
            "partial": Metashape.Shutter.Model.Regularized,
            "full": Metashape.Shutter.Model.Full,
        }
        shutter_val = None
        if rolling_shutter is not None:
            shutter_val = shutter_map.get(rolling_shutter.lower())
            if shutter_val is None:
                raise ValueError(
                    f"Unknown rolling_shutter: {rolling_shutter}. "
                    f"Use: disabled, regularized, full."
                )

        # Find sensors to modify
        sensors = set()
        for cam in chunk.cameras:
            if label_pattern and label_pattern not in cam.label:
                continue
            sensors.add(cam.sensor)

        if not sensors:
            raise RuntimeError(
                f"No cameras match pattern '{label_pattern}'."
            )

        for sensor in sensors:
            sensor.type = stype
            if pixel_size is not None:
                sensor.pixel_size = Metashape.Vector([pixel_size, pixel_size])
            if focal_length is not None:
                sensor.focal_length = focal_length
            if axes_val is not None:
                sensor.axes = axes_val
            if shutter_val is not None:
                sensor.rolling_shutter = shutter_val
            sensor.fixed = fixed_calibration

        return {
            "sensors_modified": len(sensors),
            "sensor_type": sensor_type,
            "focal_length_mm": focal_length,
            "axes": axes,
            "rolling_shutter": rolling_shutter,
            "fixed_calibration": fixed_calibration,
            "labels": [s.label for s in sensors],
        }

    @mcp.tool()
    def import_masks(
        path: str,
        method: str = "from_file",
        tolerance: int = 10,
        label_pattern: str | None = None,
    ) -> dict:
        """Import or generate masks for cameras.

        Masks exclude image regions from processing (e.g., sky in road
        corridor captures). EXR photos with alpha channels automatically
        define masked regions.

        Args:
            path: Path to mask folder or mask image. For "from_file", each
                  mask file should match camera label (e.g. IMG_001_mask.png).
            method: Mask generation method:
                    "from_file" - Load mask images from folder.
                    "from_alpha" - Use alpha channel of the source images.
                    "from_background" - Auto-detect background.
                    "from_model" - Generate from existing 3D model.
            tolerance: Tolerance for background detection (0-255).
            label_pattern: Only apply to cameras matching this pattern.

        Returns:
            Number of cameras with masks applied.
        """
        chunk = get_chunk()

        method_map = {
            "from_file": Metashape.MaskingMode.MaskingModeFile,
            "from_alpha": Metashape.MaskingMode.MaskingModeAlpha,
            "from_background": Metashape.MaskingMode.MaskingModeBackground,
            "from_model": Metashape.MaskingMode.MaskingModeModel,
        }
        mmode = method_map.get(method.lower())
        if mmode is None:
            raise ValueError(
                f"Unknown mask method: {method}. "
                f"Use: from_file, from_alpha, from_background, from_model."
            )

        cameras_to_mask = []
        for cam in chunk.cameras:
            if label_pattern and label_pattern not in cam.label:
                continue
            cameras_to_mask.append(cam)

        if method == "from_alpha":
            # Generate masks from source image alpha channels
            chunk.generateMasks(
                masking_mode=mmode,
                cameras=cameras_to_mask if label_pattern else None,
            )
        elif method == "from_background":
            chunk.generateMasks(
                masking_mode=mmode,
                tolerance=tolerance,
                cameras=cameras_to_mask if label_pattern else None,
            )
        elif method == "from_model":
            chunk.generateMasks(
                masking_mode=mmode,
                cameras=cameras_to_mask if label_pattern else None,
            )
        else:
            # from_file: import mask images from folder
            if not os.path.exists(path):
                raise FileNotFoundError(f"Mask path not found: {path}")
            chunk.importMasks(
                path=os.path.join(path, "{filename}_mask.png"),
            )

        masked = sum(1 for c in chunk.cameras if c.mask is not None)
        return {
            "method": method,
            "cameras_masked": masked,
            "total_cameras": len(chunk.cameras),
        }

    @mcp.tool()
    def clear_masks(label_pattern: str | None = None) -> dict:
        """Remove masks from cameras.

        Args:
            label_pattern: Only clear masks from cameras matching this
                          pattern. If omitted, clears all masks.

        Returns:
            Number of masks removed.
        """
        chunk = get_chunk()
        cleared = 0

        for cam in chunk.cameras:
            if label_pattern and label_pattern not in cam.label:
                continue
            if cam.mask is not None:
                cam.mask = None
                cleared += 1

        return {"cleared": cleared}

    @mcp.tool()
    def list_sensors() -> list[dict]:
        """List all sensors in the active chunk with calibration details.

        Returns:
            List of sensors with type, dimensions, focal length,
            calibration coefficients, and camera count.
        """
        chunk = get_chunk()
        result = []

        for sensor in chunk.sensors:
            info = {
                "label": sensor.label,
                "type": str(sensor.type).split(".")[-1],
                "axes": str(sensor.axes).split(".")[-1],
                "rolling_shutter": str(sensor.rolling_shutter).split(".")[-1],
                "width": sensor.width,
                "height": sensor.height,
                "pixel_size": list(sensor.pixel_size),
                "focal_length_mm": sensor.focal_length,
                "fixed": sensor.fixed,
                "camera_count": len([
                    c for c in chunk.cameras if c.sensor == sensor
                ]),
            }

            calib = sensor.calibration
            if calib:
                info["calibration"] = {
                    "f": calib.f,
                    "cx": calib.cx,
                    "cy": calib.cy,
                    "k1": calib.k1,
                    "k2": calib.k2,
                    "k3": calib.k3,
                    "k4": calib.k4,
                    "p1": calib.p1,
                    "p2": calib.p2,
                    "b1": calib.b1,
                    "b2": calib.b2,
                }

            result.append(info)

        return result

    @mcp.tool()
    def select_cameras(
        aligned: bool | None = None,
        enabled: bool | None = None,
        sensor_type: str | None = None,
        label_pattern: str | None = None,
        quality_min: float | None = None,
        quality_max: float | None = None,
    ) -> dict:
        """Query cameras by multiple criteria and return matching labels.

        Args:
            aligned: Filter by alignment status (True = has transform).
            enabled: Filter by enabled/disabled state.
            sensor_type: Filter by sensor type substring (case-insensitive).
            label_pattern: Filter by label substring match.
            quality_min: Minimum image quality score (inclusive).
            quality_max: Maximum image quality score (inclusive).

        Returns:
            Dict with matching camera labels (max 500) and total count.
        """
        chunk = get_chunk()
        matches = []

        for cam in chunk.cameras:
            if aligned is not None and (cam.transform is not None) != aligned:
                continue
            if enabled is not None and cam.enabled != enabled:
                continue
            if sensor_type is not None and sensor_type.lower() not in str(cam.sensor.type).lower():
                continue
            if label_pattern is not None and label_pattern not in cam.label:
                continue
            if quality_min is not None or quality_max is not None:
                try:
                    q = float(cam.meta["Image/Quality"])
                except (KeyError, TypeError):
                    continue
                if quality_min is not None and q < quality_min:
                    continue
                if quality_max is not None and q > quality_max:
                    continue
            matches.append(cam.label)

        return {"labels": matches[:500], "count": len(matches)}

    @mcp.tool()
    def get_camera_metadata(label: str) -> dict:
        """Return detailed metadata for a specific camera.

        Args:
            label: Exact camera label to look up.

        Returns:
            Dict with camera properties including alignment, sensor,
            reference, quality, and photo path.
        """
        chunk = get_chunk()

        for cam in chunk.cameras:
            if cam.label == label:
                info: dict = {
                    "label": cam.label,
                    "enabled": cam.enabled,
                    "aligned": cam.transform is not None,
                    "sensor_label": cam.sensor.label,
                    "sensor_type": str(cam.sensor.type),
                }
                if cam.reference.location is not None:
                    info["reference_location"] = list(cam.reference.location)
                if cam.transform is not None:
                    info["has_transform"] = True
                try:
                    info["quality"] = float(cam.meta["Image/Quality"])
                except (KeyError, TypeError):
                    pass
                try:
                    info["photo_path"] = cam.photo.path
                except AttributeError:
                    pass
                return info

        raise RuntimeError(f"Camera not found: {label}")

    @mcp.tool()
    def set_camera_reference(
        label: str,
        x: float,
        y: float,
        z: float,
        accuracy_xy: float | None = None,
        accuracy_z: float | None = None,
    ) -> dict:
        """Set GPS reference coordinates for a specific camera.

        Args:
            label: Exact camera label to update.
            x: Longitude or easting coordinate.
            y: Latitude or northing coordinate.
            z: Altitude or elevation.
            accuracy_xy: Horizontal accuracy in CRS units.
            accuracy_z: Vertical accuracy in CRS units (defaults to
                        accuracy_xy if not provided).

        Returns:
            Confirmation with camera label and assigned position.
        """
        chunk = get_chunk()

        for cam in chunk.cameras:
            if cam.label == label:
                cam.reference.location = Metashape.Vector([x, y, z])
                cam.reference.enabled = True
                if accuracy_xy is not None:
                    az = accuracy_z if accuracy_z is not None else accuracy_xy
                    cam.reference.accuracy = Metashape.Vector([accuracy_xy, accuracy_xy, az])
                return {
                    "label": label,
                    "position": [x, y, z],
                    "reference_enabled": True,
                }

        raise RuntimeError(f"Camera not found: {label}")
