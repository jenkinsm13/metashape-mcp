"""Corridor alignment diagnostics: drift detection, QA metrics, DEM comparison."""

import math

import Metashape

from metashape_mcp.utils.bridge import auto_save, get_chunk, get_document


def register(mcp) -> None:
    """Register diagnostic tools."""

    def _get_aligned_cameras(chunk, label_pattern=None):
        """Return aligned cameras, optionally filtered by label pattern."""
        cams = []
        for cam in chunk.cameras:
            if cam.transform is None:
                continue
            if label_pattern and label_pattern not in cam.label:
                continue
            cams.append(cam)
        return cams

    def _camera_estimated_position(chunk, cam):
        """Get camera position in CRS coordinates."""
        if chunk.crs and chunk.transform.matrix:
            return chunk.crs.project(chunk.transform.matrix.mulp(cam.center))
        return chunk.transform.matrix.mulp(cam.center)

    def _horizontal_distance(a, b):
        """2D distance between two vectors (XY only)."""
        return math.sqrt((a.x - b.x) ** 2 + (a.y - b.y) ** 2)

    def _sort_cameras_along_corridor(chunk, cameras):
        """Sort cameras by distance along corridor axis.

        Finds the dominant direction (longest extent of bounding box)
        and projects camera positions onto it, returning cameras sorted
        by their projection distance.
        """
        if not cameras:
            return [], []

        positions = []
        for cam in cameras:
            ref = cam.reference.location
            if ref:
                positions.append((cam, ref))
            else:
                est = _camera_estimated_position(chunk, cam)
                positions.append((cam, est))

        if len(positions) < 2:
            return [p[0] for p in positions], [0.0]

        # Find corridor axis from first to last camera by reference
        xs = [p[1].x for p in positions]
        ys = [p[1].y for p in positions]
        dx = max(xs) - min(xs)
        dy = max(ys) - min(ys)

        # Project onto dominant axis
        if dx >= dy:
            keyed = [(p[1].x, p[0], p[1]) for p in positions]
        else:
            keyed = [(p[1].y, p[0], p[1]) for p in positions]

        keyed.sort(key=lambda x: x[0])
        sorted_cams = [k[1] for k in keyed]

        # Compute cumulative distance along track
        distances = [0.0]
        for i in range(1, len(keyed)):
            prev_pos = keyed[i - 1][2]
            curr_pos = keyed[i][2]
            d = _horizontal_distance(prev_pos, curr_pos)
            distances.append(distances[-1] + d)

        return sorted_cams, distances

    # ── Phase A Tools ──────────────────────────────────────────────

    @mcp.tool()
    def get_camera_spatial_stats(
        label_pattern: str | None = None,
    ) -> dict:
        """Compute GPS deviation and drift metrics for aligned cameras.

        Key metric is error_gradient — meters of drift per 100m of
        corridor. A high gradient means alignment is diverging from GPS.
        Uniform error is normal GPS noise; increasing error is drift.

        Args:
            label_pattern: Optional filter for camera labels.

        Returns:
            Spatial quality metrics including error gradient,
            mean/max GPS deviation, and worst cameras.
        """
        chunk = get_chunk()
        cameras = _get_aligned_cameras(chunk, label_pattern)
        if not cameras:
            raise RuntimeError("No aligned cameras found.")

        # Collect cameras with both estimated and reference positions
        entries = []
        for cam in cameras:
            ref = cam.reference.location
            if ref is None:
                continue
            est = _camera_estimated_position(chunk, cam)
            err_xy = _horizontal_distance(est, ref)
            err_z = abs(est.z - ref.z)
            entries.append({
                "cam": cam,
                "est": est,
                "ref": ref,
                "err_xy": err_xy,
                "err_z": err_z,
            })

        if not entries:
            return {
                "camera_count": len(cameras),
                "cameras_with_reference": 0,
                "note": "No cameras have GPS reference. Cannot compute spatial stats.",
            }

        # Sort along corridor
        ref_cams = [e["cam"] for e in entries]
        sorted_cams, distances = _sort_cameras_along_corridor(chunk, ref_cams)

        # Build lookup by camera key
        entry_map = {e["cam"].key: e for e in entries}
        sorted_entries = [entry_map[c.key] for c in sorted_cams]

        # Aggregate stats
        err_xys = [e["err_xy"] for e in sorted_entries]
        err_zs = [e["err_z"] for e in sorted_entries]

        # Compute drift gradient (linear regression of error vs distance)
        total_distance = distances[-1] if distances else 0
        gradient = 0.0
        if total_distance > 10 and len(sorted_entries) >= 4:
            n = len(sorted_entries)
            half = n // 2
            first_half_err = sum(e["err_xy"] for e in sorted_entries[:half]) / half
            second_half_err = sum(e["err_xy"] for e in sorted_entries[half:]) / (n - half)
            first_half_dist = distances[half // 2]
            second_half_dist = distances[half + (n - half) // 2]
            dist_diff = second_half_dist - first_half_dist
            if dist_diff > 0:
                gradient = (second_half_err - first_half_err) / dist_diff * 100

        # Worst cameras
        worst = sorted(entries, key=lambda e: e["err_xy"], reverse=True)[:5]
        worst_list = [
            {"label": e["cam"].label, "error_xy": round(e["err_xy"], 3), "error_z": round(e["err_z"], 3)}
            for e in worst
        ]

        return {
            "camera_count": len(cameras),
            "cameras_with_reference": len(entries),
            "corridor_length_m": round(total_distance, 1),
            "mean_error_xy": round(sum(err_xys) / len(err_xys), 3),
            "max_error_xy": round(max(err_xys), 3),
            "mean_error_z": round(sum(err_zs) / len(err_zs), 3),
            "max_error_z": round(max(err_zs), 3),
            "error_gradient_per_100m": round(gradient, 3),
            "drift_assessment": (
                "PASS" if abs(gradient) < 0.5 else
                "WARN" if abs(gradient) < 2.0 else
                "FAIL"
            ),
            "worst_cameras": worst_list,
        }

    @mcp.tool()
    def get_reprojection_error_by_region(
        num_segments: int = 10,
        label_pattern: str | None = None,
    ) -> dict:
        """Break corridor into segments and report per-segment quality.

        Drift shows up as increasing reprojection error in later segments.

        Args:
            num_segments: Number of equal-length corridor segments.
            label_pattern: Optional filter for camera labels.

        Returns:
            Per-segment metrics including camera count, GPS deviation,
            and position along the corridor.
        """
        chunk = get_chunk()
        cameras = _get_aligned_cameras(chunk, label_pattern)
        if not cameras:
            raise RuntimeError("No aligned cameras found.")

        sorted_cams, distances = _sort_cameras_along_corridor(chunk, cameras)
        if not distances or distances[-1] == 0:
            raise RuntimeError("Cannot determine corridor axis.")

        total_dist = distances[-1]
        segment_length = total_dist / num_segments

        segments = []
        for seg_idx in range(num_segments):
            seg_start = seg_idx * segment_length
            seg_end = (seg_idx + 1) * segment_length

            seg_cams = []
            for i, cam in enumerate(sorted_cams):
                if seg_start <= distances[i] < seg_end or (seg_idx == num_segments - 1 and distances[i] == seg_end):
                    seg_cams.append(cam)

            if not seg_cams:
                segments.append({
                    "segment": seg_idx + 1,
                    "start_m": round(seg_start, 1),
                    "end_m": round(seg_end, 1),
                    "cameras": 0,
                })
                continue

            # Compute GPS errors for this segment
            err_xys = []
            err_zs = []
            for cam in seg_cams:
                ref = cam.reference.location
                if ref is None:
                    continue
                est = _camera_estimated_position(chunk, cam)
                err_xys.append(_horizontal_distance(est, ref))
                err_zs.append(abs(est.z - ref.z))

            seg_info = {
                "segment": seg_idx + 1,
                "start_m": round(seg_start, 1),
                "end_m": round(seg_end, 1),
                "cameras": len(seg_cams),
            }

            if err_xys:
                seg_info["mean_error_xy"] = round(sum(err_xys) / len(err_xys), 3)
                seg_info["max_error_xy"] = round(max(err_xys), 3)
                seg_info["mean_error_z"] = round(sum(err_zs) / len(err_zs), 3)

            segments.append(seg_info)

        return {
            "corridor_length_m": round(total_dist, 1),
            "num_segments": num_segments,
            "segment_length_m": round(segment_length, 1),
            "segments": segments,
        }

    @mcp.tool()
    def check_alignment_continuity(
        new_camera_labels: list[str],
        max_position_jump: float = 5.0,
        max_rotation_jump: float = 15.0,
    ) -> dict:
        """Check if newly aligned cameras connect smoothly to existing ones.

        Call after each align_cameras() batch to detect discontinuities
        between the new batch and previously aligned cameras.

        Args:
            new_camera_labels: Labels of cameras from the latest batch.
            max_position_jump: Flag position gaps larger than this (meters).
            max_rotation_jump: Flag rotation gaps larger than this (degrees).

        Returns:
            Continuity assessment with any flagged discontinuities.
        """
        chunk = get_chunk()
        new_set = set(new_camera_labels)

        new_cams = []
        old_cams = []
        for cam in chunk.cameras:
            if cam.transform is None:
                continue
            if cam.label in new_set:
                new_cams.append(cam)
            else:
                old_cams.append(cam)

        if not new_cams:
            raise RuntimeError("No aligned cameras found matching new_camera_labels.")
        if not old_cams:
            return {
                "continuous": True,
                "note": "First batch — no previous cameras to compare against.",
                "new_cameras": len(new_cams),
            }

        # For each new camera, find nearest old camera by reference position
        discontinuities = []
        for new_cam in new_cams:
            new_est = _camera_estimated_position(chunk, new_cam)
            new_ref = new_cam.reference.location

            # Find nearest old camera
            best_dist = float("inf")
            best_old = None
            for old_cam in old_cams:
                old_ref = old_cam.reference.location
                if new_ref and old_ref:
                    d = _horizontal_distance(new_ref, old_ref)
                else:
                    old_est = _camera_estimated_position(chunk, old_cam)
                    d = _horizontal_distance(new_est, old_est)
                if d < best_dist:
                    best_dist = d
                    best_old = old_cam

            if best_old is None:
                continue

            # Compare estimated positions
            old_est = _camera_estimated_position(chunk, best_old)
            pos_diff = _horizontal_distance(new_est, old_est)

            # Compare rotations (extract from transform matrices)
            new_rot = new_cam.transform.rotation()
            old_rot = best_old.transform.rotation()
            # Frobenius-based angle difference
            diff_mat = new_rot * old_rot.inv()
            trace = diff_mat[0, 0] + diff_mat[1, 1] + diff_mat[2, 2]
            cos_angle = max(-1.0, min(1.0, (trace - 1.0) / 2.0))
            rot_diff_deg = math.degrees(math.acos(cos_angle))

            # Only check cameras that SHOULD be close (reference distance < 20m)
            if best_dist > 20:
                continue

            if pos_diff > max_position_jump or rot_diff_deg > max_rotation_jump:
                discontinuities.append({
                    "new_camera": new_cam.label,
                    "old_camera": best_old.label,
                    "reference_distance_m": round(best_dist, 2),
                    "position_jump_m": round(pos_diff, 2),
                    "rotation_jump_deg": round(rot_diff_deg, 2),
                    "position_flag": pos_diff > max_position_jump,
                    "rotation_flag": rot_diff_deg > max_rotation_jump,
                })

        return {
            "continuous": len(discontinuities) == 0,
            "new_cameras": len(new_cams),
            "old_cameras": len(old_cams),
            "discontinuities": discontinuities[:10],
            "total_discontinuities": len(discontinuities),
        }

    # ── Phase C Tools ──────────────────────────────────────────────

    @mcp.tool()
    def compare_alignment_to_dem(
        label_pattern: str | None = None,
        camera_height_offset: float = 2.0,
    ) -> dict:
        """Compare camera heights against the DEM to detect vertical drift.

        For each aligned camera, samples the DEM at the camera's XY
        position and computes the difference. Vehicle cameras should be
        ~2m above ground; drones ~50-120m.

        Args:
            label_pattern: Optional filter for camera labels.
            camera_height_offset: Expected camera height above ground (meters).
                Use ~2.0 for vehicle-mounted, ~50-120 for drone.

        Returns:
            Per-camera and aggregate vertical deviation from DEM,
            including drift gradient along corridor.
        """
        chunk = get_chunk()
        if chunk.elevation is None:
            raise RuntimeError(
                "No DEM in active chunk. Build or import a DEM first "
                "(build_dem or import DEM as elevation)."
            )

        cameras = _get_aligned_cameras(chunk, label_pattern)
        if not cameras:
            raise RuntimeError("No aligned cameras found.")

        entries = []
        for cam in cameras:
            est = _camera_estimated_position(chunk, cam)
            try:
                dem_alt = chunk.elevation.altitude(
                    Metashape.Vector([est.x, est.y])
                )
            except Exception:
                continue

            if dem_alt is None:
                continue

            expected_z = dem_alt + camera_height_offset
            diff_z = est.z - expected_z
            entries.append({
                "cam": cam,
                "est": est,
                "dem_alt": dem_alt,
                "diff_z": diff_z,
            })

        if not entries:
            return {
                "camera_count": len(cameras),
                "cameras_with_dem": 0,
                "note": "No cameras overlap with DEM coverage.",
            }

        # Sort along corridor for gradient
        entry_cams = [e["cam"] for e in entries]
        sorted_cams, distances = _sort_cameras_along_corridor(chunk, entry_cams)
        entry_map = {e["cam"].key: e for e in entries}
        sorted_entries = [entry_map[c.key] for c in sorted_cams]

        diffs = [e["diff_z"] for e in sorted_entries]
        abs_diffs = [abs(d) for d in diffs]
        total_dist = distances[-1] if distances else 0

        # Vertical drift gradient
        gradient_z = 0.0
        if total_dist > 10 and len(sorted_entries) >= 4:
            n = len(sorted_entries)
            half = n // 2
            first_mean = sum(diffs[:half]) / half
            second_mean = sum(diffs[half:]) / (n - half)
            dist_diff = distances[half + (n - half) // 2] - distances[half // 2]
            if dist_diff > 0:
                gradient_z = (second_mean - first_mean) / dist_diff * 100

        worst = sorted(entries, key=lambda e: abs(e["diff_z"]), reverse=True)[:5]

        return {
            "camera_count": len(cameras),
            "cameras_with_dem": len(entries),
            "camera_height_offset": camera_height_offset,
            "corridor_length_m": round(total_dist, 1),
            "mean_diff_z": round(sum(diffs) / len(diffs), 3),
            "mean_abs_diff_z": round(sum(abs_diffs) / len(abs_diffs), 3),
            "max_abs_diff_z": round(max(abs_diffs), 3),
            "vertical_gradient_per_100m": round(gradient_z, 3),
            "drift_assessment": (
                "PASS" if abs(gradient_z) < 0.5 else
                "WARN" if abs(gradient_z) < 2.0 else
                "FAIL"
            ),
            "worst_cameras": [
                {
                    "label": e["cam"].label,
                    "diff_z": round(e["diff_z"], 3),
                    "dem_alt": round(e["dem_alt"], 2),
                    "est_z": round(e["est"].z, 2),
                }
                for e in worst
            ],
        }

    @mcp.tool()
    def generate_virtual_checkpoints(
        spacing_meters: float = 200.0,
        camera_height_offset: float = 2.0,
        create_markers: bool = True,
        marker_prefix: str = "VCP",
    ) -> dict:
        """Generate evenly-spaced checkpoints along corridor from the DEM.

        Creates markers at regular intervals along the camera corridor,
        using DEM elevation + height offset as the Z coordinate. These
        serve as check points (not control points) to measure alignment
        quality without biasing it.

        Markers are created with reference enabled but should NOT be used
        for optimization — only for error reporting.

        Args:
            spacing_meters: Distance between checkpoints along corridor.
            camera_height_offset: Expected camera height above ground (meters).
            create_markers: Create actual markers in the chunk.
            marker_prefix: Label prefix for created markers (e.g., VCP_001).

        Returns:
            List of checkpoint positions with DEM-derived elevations.
        """
        chunk = get_chunk()
        if chunk.elevation is None:
            raise RuntimeError("No DEM in active chunk. Build or import a DEM first.")

        cameras = _get_aligned_cameras(chunk)
        if not cameras:
            raise RuntimeError("No aligned cameras found.")

        sorted_cams, distances = _sort_cameras_along_corridor(chunk, cameras)
        total_dist = distances[-1] if distances else 0

        if total_dist < spacing_meters:
            raise RuntimeError(
                f"Corridor length ({total_dist:.0f}m) is shorter than "
                f"checkpoint spacing ({spacing_meters:.0f}m)."
            )

        # Generate checkpoint positions along corridor centerline
        checkpoints = []
        target_dist = spacing_meters
        cp_idx = 1

        for i in range(1, len(sorted_cams)):
            if distances[i] >= target_dist:
                # Interpolate position between cameras i-1 and i
                frac = (target_dist - distances[i - 1]) / (distances[i] - distances[i - 1])
                cam_a = sorted_cams[i - 1]
                cam_b = sorted_cams[i]

                ref_a = cam_a.reference.location
                ref_b = cam_b.reference.location
                if ref_a is None or ref_b is None:
                    est_a = _camera_estimated_position(chunk, cam_a)
                    est_b = _camera_estimated_position(chunk, cam_b)
                    pos = est_a + (est_b - est_a) * frac
                else:
                    pos = ref_a + (ref_b - ref_a) * frac

                # Sample DEM
                try:
                    dem_alt = chunk.elevation.altitude(
                        Metashape.Vector([pos.x, pos.y])
                    )
                except Exception:
                    target_dist += spacing_meters
                    continue

                if dem_alt is None:
                    target_dist += spacing_meters
                    continue

                cp_z = dem_alt + camera_height_offset
                label = f"{marker_prefix}_{cp_idx:03d}"

                checkpoints.append({
                    "label": label,
                    "x": round(pos.x, 6),
                    "y": round(pos.y, 6),
                    "z": round(cp_z, 3),
                    "dem_alt": round(dem_alt, 3),
                    "distance_along_m": round(target_dist, 1),
                })

                if create_markers:
                    marker = chunk.addMarker()
                    marker.label = label
                    marker.reference.location = Metashape.Vector([pos.x, pos.y, cp_z])
                    marker.reference.enabled = True

                cp_idx += 1
                target_dist += spacing_meters

        if create_markers and checkpoints:
            auto_save()

        return {
            "corridor_length_m": round(total_dist, 1),
            "spacing_meters": spacing_meters,
            "checkpoints_created": len(checkpoints),
            "camera_height_offset": camera_height_offset,
            "checkpoints": checkpoints,
        }

    @mcp.tool()
    def get_corridor_drift_report(
        num_segments: int = 10,
        camera_height_offset: float = 2.0,
        label_pattern: str | None = None,
    ) -> dict:
        """Comprehensive corridor health report combining all diagnostics.

        Runs GPS deviation analysis, per-segment breakdown, and DEM
        comparison (if available) in a single call. Returns an overall
        health assessment.

        Args:
            num_segments: Number of corridor segments for regional analysis.
            camera_height_offset: Expected camera height above ground.
            label_pattern: Optional filter for camera labels.

        Returns:
            Combined report with GPS stats, segment breakdown, DEM
            comparison, and overall PASS/WARN/FAIL assessment.
        """
        chunk = get_chunk()
        cameras = _get_aligned_cameras(chunk, label_pattern)
        if not cameras:
            raise RuntimeError("No aligned cameras found.")

        report = {
            "camera_count": len(cameras),
            "issues": [],
        }

        # GPS spatial stats
        try:
            gps_stats = get_camera_spatial_stats(label_pattern=label_pattern)
            report["gps_stats"] = gps_stats
            if gps_stats.get("drift_assessment") == "FAIL":
                report["issues"].append(
                    f"GPS drift gradient {gps_stats['error_gradient_per_100m']}m/100m exceeds threshold"
                )
            elif gps_stats.get("drift_assessment") == "WARN":
                report["issues"].append(
                    f"GPS drift gradient {gps_stats['error_gradient_per_100m']}m/100m is elevated"
                )
        except Exception as e:
            report["gps_stats"] = {"error": str(e)}

        # Per-segment breakdown
        try:
            segments = get_reprojection_error_by_region(
                num_segments=num_segments, label_pattern=label_pattern
            )
            report["segments"] = segments

            # Check for error escalation across segments
            seg_errors = [
                s["mean_error_xy"] for s in segments.get("segments", [])
                if "mean_error_xy" in s
            ]
            if len(seg_errors) >= 3:
                first_third = sum(seg_errors[:len(seg_errors)//3]) / (len(seg_errors)//3)
                last_third = sum(seg_errors[-(len(seg_errors)//3):]) / (len(seg_errors)//3)
                if last_third > first_third * 2:
                    report["issues"].append(
                        f"Error doubles along corridor: {first_third:.2f}m → {last_third:.2f}m"
                    )
        except Exception as e:
            report["segments"] = {"error": str(e)}

        # DEM comparison (only if DEM exists)
        if chunk.elevation is not None:
            try:
                dem_stats = compare_alignment_to_dem(
                    label_pattern=label_pattern,
                    camera_height_offset=camera_height_offset,
                )
                report["dem_comparison"] = dem_stats
                if dem_stats.get("drift_assessment") == "FAIL":
                    report["issues"].append(
                        f"Vertical drift gradient {dem_stats['vertical_gradient_per_100m']}m/100m exceeds threshold"
                    )
            except Exception as e:
                report["dem_comparison"] = {"error": str(e)}
        else:
            report["dem_comparison"] = {"note": "No DEM available — skipped"}

        # Overall assessment
        if any("FAIL" in str(report.get(k, {}).get("drift_assessment", "")) for k in ["gps_stats", "dem_comparison"]):
            report["overall"] = "FAIL"
        elif report["issues"]:
            report["overall"] = "WARN"
        else:
            report["overall"] = "PASS"

        if not report["issues"]:
            report["issues"] = ["No issues detected"]

        return report
