#!/bin/bash
# Post-processing QA reminder.
# After major processing steps complete, reminds to run QA checks.
# Does NOT block — just provides a suggestion.

TOOL_NAME="$CLAUDE_TOOL_NAME"

case "$TOOL_NAME" in
    *align_cameras*)
        echo "QA REMINDER: Alignment complete. Consider running photogrammetry-qa agent to check:"
        echo "  - Alignment rate (target >95%)"
        echo "  - Reprojection error (target <1.0 px)"
        echo "  - Drift gradient (target <0.5 m/100m)"
        echo "  Tools: get_alignment_stats(), get_camera_spatial_stats()"
        ;;
    *build_depth_maps*)
        echo "QA REMINDER: Depth maps complete. Before building mesh, verify:"
        echo "  - Depth map count matches aligned camera count"
        echo "  - Consider saving project before next step"
        ;;
    *build_model*)
        echo "QA REMINDER: Mesh built. Check for artifacts:"
        echo "  - get_model_stats() for face/vertex counts"
        echo "  - capture_viewport() for visual inspection"
        echo "  - Look for sky/tunnel artifacts (see sky-artifact-prevention skill)"
        echo "  - Consider clean_model() if artifacts visible"
        ;;
    *build_point_cloud*)
        echo "QA REMINDER: Point cloud built. Consider:"
        echo "  - get_point_cloud_stats() for point count and bounds"
        echo "  - classify_ground_points() if building terrain mesh"
        echo "  - filter_points_by_confidence() to remove noise"
        ;;
    *build_texture*)
        echo "QA REMINDER: Texture complete. Check for:"
        echo "  - Seam visibility (try natural blending if mosaic has bad seams)"
        echo "  - Ghosting artifacts (enable ghosting_filter if not already)"
        echo "  - Color consistency (run calibrate_colors if shifts visible)"
        ;;
esac

exit 0
