---
name: diagnose-alignment
description: Diagnose alignment quality issues in the current Metashape project — checks camera alignment rate, tie point density, reprojection error, and sensor calibration. Provides actionable fix recommendations.
user-invocable: true
---

# Diagnose Alignment

Check alignment health and recommend fixes for the active Metashape chunk.

## Diagnostic Steps

1. **Check project state**: `get_alignment_stats` for overall alignment summary
2. **Check cameras**: What percentage are aligned? Are there clusters of unaligned cameras?
3. **Check tie points**: How many exist? What's the ratio of points to cameras?
4. **Check sensors**: Are calibration parameters reasonable? Use `list_sensors`
5. **Check spatial distribution**: `get_camera_spatial_stats` for coverage gaps

## Common Issues and Solutions

### Low alignment rate (<80%)
- Try `match_photos` with higher `keypoint_limit` (60000–100000)
- Enable `guided_matching=True`
- Lower `downscale` (0 or 1 for highest accuracy)
- Check for images with insufficient overlap

### High reprojection error (>1 pixel)
- Run `optimize_cameras` with all distortion coefficients
- Try `adaptive_fitting=True`
- Remove cameras with very high individual errors

### Sparse tie points (<1000 per camera)
- Increase `keypoint_limit` and `tiepoint_limit`
- Check image quality with `analyze_images`
- Remove blurry images (quality < 0.5)

### Alignment drift / banding
- Add ground control points (GCPs)
- Use `reference_preselection=True`
- Check camera GPS accuracy
- See `/corridor-alignment-pipeline` for incremental approach

## Output

Provide a summary of findings with specific recommended tool calls and parameters.
