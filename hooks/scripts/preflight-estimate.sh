#!/bin/bash
# Pre-flight time estimation for long-running Metashape operations.
# Warns the user before build_depth_maps, build_model, build_point_cloud,
# build_texture, build_dem, or build_orthomosaic starts.
#
# This hook reads tool input parameters and produces a time estimate
# based on the operation type and downscale setting.

TOOL_NAME="$CLAUDE_TOOL_NAME"
INPUT="$CLAUDE_TOOL_INPUT"

# Extract downscale parameter if present
DOWNSCALE=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('downscale','2'))" 2>/dev/null || echo "2")

case "$TOOL_NAME" in
    *build_depth_maps*)
        echo "LONG OPERATION: build_depth_maps at downscale=$DOWNSCALE"
        case "$DOWNSCALE" in
            1) echo "  Ultra quality — expect 4-12+ hours for large projects (5k+ cameras)" ;;
            2) echo "  High quality — expect 2-8 hours for large projects" ;;
            4) echo "  Medium quality — expect 30min-3 hours" ;;
            8|16) echo "  Low quality — expect 10-60 minutes" ;;
            *) echo "  Custom downscale — time varies" ;;
        esac
        echo "  This operation blocks until complete. No timeout."
        ;;
    *build_point_cloud*)
        echo "LONG OPERATION: build_point_cloud"
        echo "  Expect 30min-4 hours depending on depth map count and quality."
        echo "  This operation blocks until complete. No timeout."
        ;;
    *build_model*)
        echo "LONG OPERATION: build_model"
        SOURCE=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('source_data','depth_maps'))" 2>/dev/null || echo "depth_maps")
        echo "  Source: $SOURCE"
        echo "  From depth maps: 30min-2 hours. From point cloud: 15min-1 hour."
        echo "  This operation blocks until complete. No timeout."
        ;;
    *build_texture*)
        SIZE=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('texture_size','8192'))" 2>/dev/null || echo "8192")
        echo "LONG OPERATION: build_texture at size=$SIZE"
        echo "  Expect 15-60 minutes depending on face count and texture size."
        echo "  This operation blocks until complete. No timeout."
        ;;
    *build_dem*)
        echo "LONG OPERATION: build_dem"
        echo "  Expect 10-30 minutes depending on point count and resolution."
        echo "  This operation blocks until complete. No timeout."
        ;;
    *build_orthomosaic*)
        echo "LONG OPERATION: build_orthomosaic"
        echo "  Expect 15-60 minutes depending on camera count and resolution."
        echo "  This operation blocks until complete. No timeout."
        ;;
esac

# Always allow — this hook only warns, never blocks
exit 0
