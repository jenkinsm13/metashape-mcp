---
name: quality-settings
description: Recommend optimal Metashape processing settings based on dataset size and available RAM. Provides specific parameter values for each processing step with quality/speed trade-offs.
user-invocable: true
---

# Optimize Quality Settings

Recommend processing parameters tuned to the user's dataset and hardware.

## Information Needed

Ask the user (or read from the project):
- **Photo count**: Number of images in the dataset
- **Available RAM**: System memory in GB
- **Priority**: Quality vs speed

## Guidelines by Dataset Size

| Setting | <100 photos | 100–500 | 500–2000 | 2000+ |
|---------|-------------|---------|----------|-------|
| Match downscale | 1 (High) | 1 (High) | 2 (Medium) | 2–4 |
| Keypoint limit | 60000 | 40000 | 40000 | 40000 |
| Depth map quality | 2 (High) | 4 (Medium) | 4 (Medium) | 8 (Low) |
| Depth filter | mild | mild | moderate | moderate |
| Face count | high | high | medium | medium/custom |

## RAM Considerations

- **<16 GB**: Use downscale 4+ for depth maps, medium face count
- **16–32 GB**: Use downscale 2–4, high face count up to ~500 photos
- **32–64 GB**: Use downscale 1–2, high face count up to ~1000 photos
- **64+ GB**: Can use ultra quality for smaller datasets

## GPU/CPU Rule

- `set_gpu_config(cpu_enable=True)` — BEFORE alignment (match_photos, align_cameras)
- `set_gpu_config(cpu_enable=False)` — BEFORE everything else (depth maps, meshing, texturing, DEM, ortho)

CPU slows GPU operations. It is ONLY beneficial for alignment.

## Output

Read the chunk info, then provide specific parameter values for each processing step as ready-to-use tool calls.
