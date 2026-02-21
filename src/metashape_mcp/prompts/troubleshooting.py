"""Diagnostic and troubleshooting prompt templates."""


def register(mcp) -> None:
    """Register troubleshooting prompts."""

    @mcp.prompt()
    def diagnose_alignment() -> str:
        """Diagnose alignment quality issues.

        Generates a diagnostic prompt that checks alignment status
        and suggests improvements.
        """
        return """Diagnose the current alignment quality:

1. **Check Project State**: Read metashape://project/chunks to see overall status
2. **Check Cameras**: Read metashape://chunk/{active_chunk}/cameras
   - What percentage of cameras are aligned?
   - Are there clusters of unaligned cameras?
3. **Check Tie Points**: Read metashape://chunk/{active_chunk}/tie_points
   - How many tie points exist?
   - What's the ratio of points to cameras?
4. **Check Sensors**: Read metashape://chunk/{active_chunk}/sensors
   - Are calibration parameters reasonable?

**Common Issues and Solutions:**

- **Low alignment rate (<80%)**:
  - Try: match_photos with higher keypoint_limit (60000-100000)
  - Try: Enable guided_matching=True
  - Try: Lower downscale (0 or 1 for highest accuracy)
  - Check for images with insufficient overlap

- **High reprojection error (>1 pixel)**:
  - Run: optimize_cameras with all distortion coefficients
  - Try: adaptive_fitting=True
  - Remove cameras with very high individual errors

- **Sparse tie points (<1000 per camera)**:
  - Increase keypoint_limit and tiepoint_limit
  - Check image quality with analyze_images
  - Remove blurry images (quality < 0.5)

- **Alignment drift/banding**:
  - Add ground control points (GCPs)
  - Use reference_preselection=True
  - Check camera GPS accuracy

Provide a summary of findings and recommended actions.
"""

    @mcp.prompt()
    def optimize_quality_settings(
        photo_count: str = "100",
        ram_gb: str = "32",
    ) -> str:
        """Recommend processing quality settings based on dataset size.

        Args:
            photo_count: Number of photos in the dataset.
            ram_gb: Available RAM in gigabytes.
        """
        return f"""Recommend optimal processing settings for this dataset:

**Dataset Info:**
- Photos: {photo_count}
- Available RAM: {ram_gb} GB

**Guidelines by dataset size:**

| Setting | <100 photos | 100-500 | 500-2000 | 2000+ |
|---------|-------------|---------|----------|-------|
| Match downscale | 1 (High) | 1 (High) | 2 (Medium) | 2-4 |
| Keypoint limit | 60000 | 40000 | 40000 | 40000 |
| Depth map quality | 2 (High) | 4 (Medium) | 4 (Medium) | 8 (Low) |
| Depth filter | mild | mild | moderate | moderate |
| Face count | high | high | medium | medium/custom |

**RAM Considerations:**
- <16 GB: Use downscale 4+ for depth maps, medium face count
- 16-32 GB: Use downscale 2-4, high face count up to ~500 photos
- 32-64 GB: Use downscale 1-2, high face count up to ~1000 photos
- 64+ GB: Can use ultra quality for smaller datasets

**Recommended Settings for {photo_count} photos / {ram_gb} GB RAM:**

Read the chunk info first, then recommend specific parameter values
for each processing step. Consider the trade-off between quality
and processing time.

Provide the recommended tool calls with specific parameters.
"""
