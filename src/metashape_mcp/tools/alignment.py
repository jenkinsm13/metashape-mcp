"""Photo alignment tools: match photos, align cameras, optimize."""

from metashape_mcp.utils.bridge import get_chunk, require_tie_points
from metashape_mcp.utils.enums import resolve_enum
from metashape_mcp.utils.progress import make_tracking_callback


def register(mcp) -> None:
    """Register alignment tools."""

    @mcp.tool()
    def match_photos(
        downscale: int = 1,
        generic_preselection: bool = True,
        reference_preselection: bool = False,
        keypoint_limit: int = 40000,
        tiepoint_limit: int = 4000,
        filter_stationary_points: bool = True,
        guided_matching: bool = False,
        keep_keypoints: bool = True,
        reset_matches: bool = False,
    ) -> dict:
        """Perform feature matching between photos.

        This is the first step of photo alignment. It detects keypoints
        in each image and finds matching features between image pairs.

        Args:
            downscale: Accuracy (0=Highest, 1=High, 2=Medium, 4=Low, 8=Lowest).
            generic_preselection: Enable generic image pair preselection.
            reference_preselection: Enable reference-based preselection.
            keypoint_limit: Maximum keypoints per photo.
            tiepoint_limit: Maximum tie points per photo.
            filter_stationary_points: Filter stationary points across images.
            guided_matching: Enable guided image matching.
            keep_keypoints: Keep keypoints after matching. Must be True for
                incremental workflows so subsequent batches can cross-match
                new cameras against existing ones.
            reset_matches: Reset existing matches before matching.

        Returns:
            Matching results with tie point count.
        """
        chunk = get_chunk()
        if not chunk.cameras:
            raise RuntimeError("No cameras in chunk. Add photos first.")

        cb = make_tracking_callback("Matching photos")
        chunk.matchPhotos(
            downscale=downscale,
            generic_preselection=generic_preselection,
            reference_preselection=reference_preselection,
            keypoint_limit=keypoint_limit,
            tiepoint_limit=tiepoint_limit,
            filter_stationary_points=filter_stationary_points,
            guided_matching=guided_matching,
            keep_keypoints=keep_keypoints,
            reset_matches=reset_matches,
            progress=cb,
        )

        tp = chunk.tie_points
        tp_count = len(tp.points) if tp and tp.points else 0
        return {
            "cameras": len(chunk.cameras),
            "tie_points": tp_count,
        }

    @mcp.tool()
    def align_cameras(
        adaptive_fitting: bool = False,
        reset_alignment: bool = False,
        min_image: int = 2,
    ) -> dict:
        """Align cameras using matched features.

        Estimates camera positions and orientations based on feature matches.
        Run match_photos first.

        Args:
            adaptive_fitting: Enable adaptive fitting of distortion coefficients.
            reset_alignment: Reset current alignment before processing.
            min_image: Minimum number of point projections.

        Returns:
            Alignment results with aligned/total camera counts.
        """
        chunk = get_chunk()
        require_tie_points(chunk)

        cb = make_tracking_callback("Aligning cameras")
        chunk.alignCameras(
            adaptive_fitting=adaptive_fitting,
            reset_alignment=reset_alignment,
            min_image=min_image,
            progress=cb,
        )

        aligned = sum(1 for c in chunk.cameras if c.transform is not None)
        return {
            "aligned": aligned,
            "total": len(chunk.cameras),
            "alignment_rate": f"{aligned/len(chunk.cameras):.1%}" if chunk.cameras else "0%",
        }

    @mcp.tool()
    def optimize_cameras(
        fit_f: bool = True,
        fit_cx: bool = True,
        fit_cy: bool = True,
        fit_k1: bool = True,
        fit_k2: bool = True,
        fit_k3: bool = True,
        fit_k4: bool = False,
        fit_p1: bool = True,
        fit_p2: bool = True,
        fit_b1: bool = False,
        fit_b2: bool = False,
        adaptive_fitting: bool = False,
        tiepoint_covariance: bool = False,
    ) -> dict:
        """Optimize camera calibration parameters.

        Refines camera positions and lens distortion parameters to minimize
        reprojection errors. Run after align_cameras.

        Args:
            fit_f: Optimize focal length.
            fit_cx: Optimize X principal point.
            fit_cy: Optimize Y principal point.
            fit_k1-k4: Optimize radial distortion coefficients.
            fit_p1-p2: Optimize tangential distortion coefficients.
            fit_b1-b2: Optimize aspect ratio and skew.
            adaptive_fitting: Enable adaptive coefficient fitting.
            tiepoint_covariance: Estimate tie point covariance matrices.

        Returns:
            Optimization results.
        """
        chunk = get_chunk()
        require_tie_points(chunk)

        cb = make_tracking_callback("Optimizing cameras")
        chunk.optimizeCameras(
            fit_f=fit_f,
            fit_cx=fit_cx,
            fit_cy=fit_cy,
            fit_k1=fit_k1,
            fit_k2=fit_k2,
            fit_k3=fit_k3,
            fit_k4=fit_k4,
            fit_p1=fit_p1,
            fit_p2=fit_p2,
            fit_b1=fit_b1,
            fit_b2=fit_b2,
            adaptive_fitting=adaptive_fitting,
            tiepoint_covariance=tiepoint_covariance,
            progress=cb,
        )

        return {"status": "optimization_complete"}

    @mcp.tool()
    def filter_tie_points(
        criterion: str = "ReprojectionError",
        threshold: float = 0.3,
        max_select_percent: float = 50.0,
    ) -> dict:
        """Filter (remove) tie points based on quality criteria.

        USGS workflow — run BEFORE optimize_cameras, in this order:
        1. filter_tie_points(criterion="ReconstructionUncertainty", threshold=10)
           then optimize_cameras()
        2. filter_tie_points(criterion="ProjectionAccuracy", threshold=3)
           then optimize_cameras()
        3. filter_tie_points(criterion="ReprojectionError", threshold=0.3)
           then optimize_cameras()
        Repeat step 3 until <10 points are removed per iteration.

        NEVER remove more than 50% of tie points in one call. If the
        threshold would select more than max_select_percent, the threshold
        is automatically raised in 0.1 increments until under the limit.

        Args:
            criterion: "ReprojectionError", "ReconstructionUncertainty",
                       "ProjectionAccuracy", or "ImageCount".
            threshold: Points above this value are removed.
                       USGS values: ReconstructionUncertainty=10,
                       ProjectionAccuracy=3, ReprojectionError=0.3.
            max_select_percent: Safety cap — never select more than this
                       percentage of tie points (default 50%). Set to 100
                       to disable the cap.

        Returns:
            Number of points removed, remaining count, and final threshold.
        """
        import Metashape

        chunk = get_chunk()
        require_tie_points(chunk)

        criterion_map = {
            "reprojectionerror": Metashape.TiePoints.Filter.ReprojectionError,
            "reconstructionuncertainty": Metashape.TiePoints.Filter.ReconstructionUncertainty,
            "projectionaccuracy": Metashape.TiePoints.Filter.ProjectionAccuracy,
            "imagecount": Metashape.TiePoints.Filter.ImageCount,
        }
        crit = criterion_map.get(criterion.lower())
        if crit is None:
            raise ValueError(
                f"Unknown criterion: {criterion}. "
                f"Use: ReprojectionError, ReconstructionUncertainty, "
                f"ProjectionAccuracy, or ImageCount."
            )

        tp = chunk.tie_points
        before = len(tp.points) if tp.points else 0
        max_allowed = int(before * max_select_percent / 100.0)
        actual_threshold = threshold

        f = Metashape.TiePoints.Filter()
        f.init(chunk, criterion=crit)
        f.selectPoints(actual_threshold)
        selected = sum(1 for p in tp.points if p.selected)

        # Raise threshold in 0.1 increments until under the cap
        while selected > max_allowed and actual_threshold < 1000:
            actual_threshold = round(actual_threshold + 0.1, 1)
            f.selectPoints(actual_threshold)
            selected = sum(1 for p in tp.points if p.selected)

        tp.removeSelectedPoints()

        after = len(tp.points) if tp.points else 0
        result = {
            "criterion": criterion,
            "threshold_requested": threshold,
            "threshold_used": actual_threshold,
            "removed": selected,
            "remaining": after,
            "percent_removed": f"{selected / before:.1%}" if before else "0%",
        }
        if actual_threshold != threshold:
            result["note"] = (
                f"Threshold raised from {threshold} to {actual_threshold} "
                f"to stay under {max_select_percent}% removal cap."
            )
        return result

    @mcp.tool()
    def reset_camera_alignment() -> dict:
        """Clear all camera alignment data from the active chunk.

        This removes camera positions and tie points. Use with caution.

        Returns:
            Confirmation of reset.
        """
        chunk = get_chunk()
        for cam in chunk.cameras:
            cam.transform = None
        return {
            "status": "alignment_reset",
            "cameras_reset": len(chunk.cameras),
        }

    @mcp.tool()
    def get_alignment_stats() -> dict:
        """Return detailed alignment quality metrics for the active chunk.

        Returns:
            Dict with aligned/total cameras, alignment rate, enabled count,
            valid tie point count, and number of sensors.
        """
        chunk = get_chunk()
        require_tie_points(chunk)

        aligned = sum(1 for c in chunk.cameras if c.transform is not None)
        total = len(chunk.cameras)
        enabled = sum(1 for c in chunk.cameras if c.enabled)
        tp = chunk.tie_points
        valid_points = 0
        if tp and tp.points:
            valid_points = sum(1 for p in tp.points if p.valid)

        return {
            "aligned": aligned,
            "total": total,
            "alignment_rate": f"{aligned / total:.1%}" if total else "0%",
            "enabled_cameras": enabled,
            "tie_point_count_valid": valid_points,
            "sensors": len(chunk.sensors),
        }
